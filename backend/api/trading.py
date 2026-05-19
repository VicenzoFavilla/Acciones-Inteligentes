from fastapi import APIRouter, Depends
from services.stocks import get_stock_info
from services.wallet import buy_stock, sell_stock
from services.orders import create_order
from config.db import get_db
from api.auth import get_current_user

router = APIRouter()

@router.post("/trade/buy")
def trade_buy(ticker: str, quantity: int, current_user: dict = Depends(get_current_user)):
    if quantity <= 0: return {"status": "error", "message": "La cantidad debe ser mayor a 0"}
    ticker_up = ticker.upper()
    info = get_stock_info(ticker_up)
    if not info or not info.get("price"):
        return {"status": "error", "message": f"No se pudo obtener el precio para {ticker_up}"}
    price = info["price"]
    success, message = buy_stock(current_user["email"], ticker_up, quantity, price)
    if success: return {"status": "success", "message": message, "price_paid": price}
    return {"status": "error", "message": message}

@router.post("/trade/sell")
def trade_sell(ticker: str, quantity: int, current_user: dict = Depends(get_current_user)):
    if quantity <= 0: return {"status": "error", "message": "La cantidad debe ser mayor a 0"}
    ticker_up = ticker.upper()
    info = get_stock_info(ticker_up)
    if not info or not info.get("price"):
        return {"status": "error", "message": f"No se pudo obtener el precio para {ticker_up}"}
    price = info["price"]
    success, message = sell_stock(current_user["email"], ticker_up, quantity, price)
    if success: return {"status": "success", "message": message, "price_sold": price}
    return {"status": "error", "message": message}

@router.post("/trade/order")
def place_order(ticker: str, quantity: int, target_price: float, side: str, order_type: str = "limit", current_user: dict = Depends(get_current_user)):
    if quantity <= 0 or target_price <= 0: return {"status": "error", "message": "Cantidad y precio deben ser mayores a 0"}
    if side not in ["buy", "sell"]: return {"status": "error", "message": "Side debe ser 'buy' o 'sell'"}
    if order_type not in ["limit", "stop_loss", "take_profit"]: return {"status": "error", "message": "Tipo de orden no válido"}
    order_id = create_order(current_user["email"], ticker.upper(), quantity, target_price, side, order_type)
    return {"status": "success", "message": f"Orden {order_type} de {side} para {ticker} creada", "order_id": order_id}

@router.get("/user/orders")
def get_user_orders(current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    orders = list(db_conn.orders.find({"email": current_user["email"]}).sort("timestamp", -1))
    for o in orders:
        if "_id" in o: o["_id"] = str(o["_id"])
    return {"status": "success", "orders": orders}
