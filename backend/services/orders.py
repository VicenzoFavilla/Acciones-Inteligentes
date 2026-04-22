from config.db import get_db
from datetime import datetime
from services.wallet import buy_stock, sell_stock

def create_order(email: str, ticker: str, quantity: int, target_price: float, side: str, order_type: str = "limit"):
    db = get_db()
    order = {
        "email": email,
        "ticker": ticker,
        "quantity": quantity,
        "target_price": target_price,
        "side": side, # 'buy' or 'sell'
        "order_type": order_type, # 'limit', 'stop_loss', 'take_profit'
        "status": "pending",
        "timestamp": datetime.utcnow()
    }
    result = db.orders.insert_one(order)
    return str(result.inserted_id)

def check_and_execute_orders(market_prices: dict):
    """
    Simulación de ejecución de órdenes basada en precios actuales del mercado.
    Maneja Limit, Stop-Loss y Take-Profit.
    """
    db = get_db()
    pending_orders = db.orders.find({"status": "pending"})
    
    for order in pending_orders:
        ticker = order["ticker"]
        if ticker in market_prices:
            current_price = market_prices[ticker]["price"]
            order_type = order.get("order_type", "limit")
            target_price = order["target_price"]
            side = order["side"]
            
            should_execute = False
            
            if order_type == "limit":
                if side == "buy" and current_price <= target_price:
                    should_execute = True
                elif side == "sell" and current_price >= target_price:
                    should_execute = True
            
            elif order_type == "stop_loss":
                # Venta automática si el precio cae por debajo del límite
                if side == "sell" and current_price <= target_price:
                    should_execute = True
                # Compra automática (short cover) si el precio sube por encima del límite
                elif side == "buy" and current_price >= target_price:
                    should_execute = True
                    
            elif order_type == "take_profit":
                # Venta automática si el precio sube al objetivo
                if side == "sell" and current_price >= target_price:
                    should_execute = True
                # Compra automática (short cover) si el precio baja al objetivo
                elif side == "buy" and current_price <= target_price:
                    should_execute = True
                
            if should_execute:
                if side == "buy":
                    success, msg = buy_stock(order["email"], ticker, order["quantity"], current_price)
                else:
                    success, msg = sell_stock(order["email"], ticker, order["quantity"], current_price)
                
                if success:
                    db.orders.update_one(
                        {"_id": order["_id"]}, 
                        {"$set": {"status": "executed", "executed_at": datetime.utcnow(), "execution_price": current_price}}
                    )
                else:
                    # Si falla por saldo/acciones, marcamos como cancelada o error
                    db.orders.update_one(
                        {"_id": order["_id"]}, 
                        {"$set": {"status": "failed", "error": msg, "failed_at": datetime.utcnow()}}
                    )
