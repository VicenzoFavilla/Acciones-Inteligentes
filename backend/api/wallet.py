from fastapi import APIRouter, Depends
from config.db import get_db
from services.wallet import get_wallet, update_balance
from services.stocks import get_stock_info
from api.auth import get_current_user

router = APIRouter()

@router.get("/wallet/info")
def wallet_info(current_user: dict = Depends(get_current_user)):
    wallet = get_wallet(current_user["email"])
    portfolio = wallet.get("portfolio", {})
    total_market_value = 0.0
    daily_pnl = 0.0
    previous_portfolio_value = 0.0
    detailed_portfolio = []

    for ticker, info in portfolio.items():
        qty = info.get("quantity", 0)
        avg_price = info.get("average_price", 0.0)
        current_data = get_stock_info(ticker)
        current_price = current_data.get("price", avg_price) if current_data else avg_price
        cost_basis = qty * avg_price
        market_value = qty * current_price
        daily_change_pct = current_data.get("change", 0.0) if current_data else 0.0
        previous_price = current_price / (1 + (daily_change_pct / 100)) if daily_change_pct > -100 else current_price
        pnl_abs = market_value - cost_basis
        pnl_pct = (pnl_abs / cost_basis * 100) if cost_basis > 0 else 0.0
        total_market_value += market_value
        previous_portfolio_value += qty * previous_price
        daily_pnl += market_value - (qty * previous_price)
        detailed_portfolio.append({
            "ticker": ticker, "quantity": qty, "average_price": avg_price,
            "current_price": current_price, "pnl_abs": pnl_abs, "pnl_pct": pnl_pct,
            "market_value": market_value, "daily_change_pct": daily_change_pct
        })

    wallet["portfolio_details"] = detailed_portfolio
    wallet["total_equity"] = wallet["balance"] + total_market_value
    previous_equity = wallet["balance"] + previous_portfolio_value
    wallet["daily_pnl"] = daily_pnl
    wallet["daily_pnl_pct"] = (daily_pnl / previous_equity * 100) if previous_equity else 0.0
    if "_id" in wallet: del wallet["_id"]
    return {"status": "success", "wallet": wallet}

@router.post("/wallet/deposit")
def deposit_funds(amount: float, current_user: dict = Depends(get_current_user)):
    if amount <= 0: return {"status": "error", "message": "El monto debe ser positivo"}
    if update_balance(current_user["email"], amount):
        return {"status": "success", "message": f"Se han depositado ${amount} correctamente."}
    return {"status": "error", "message": "No se pudo actualizar el saldo."}

@router.get("/wallet/history")
def transaction_history(current_user: dict = Depends(get_current_user)):
    db = get_db()
    transactions = list(db.transactions.find({"email": current_user["email"]}).sort("timestamp", -1))
    for t in transactions:
        if "_id" in t: t["_id"] = str(t["_id"])
    return {"status": "success", "transactions": transactions}

@router.post("/wallet/transfer")
def transfer_funds_endpoint(from_wallet: str, to_wallet: str, amount: float, current_user: dict = Depends(get_current_user)):
    from services.wallet import transfer_between_subwallets
    success, message = transfer_between_subwallets(current_user["email"], from_wallet, to_wallet, amount)
    if success: return {"status": "success", "message": message}
    return {"status": "error", "message": message}
