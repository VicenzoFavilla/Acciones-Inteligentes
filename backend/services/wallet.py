from config.db import get_db
from datetime import datetime

def get_wallet(email: str):
    db = get_db()
    wallet = db.wallets.find_one({"email": email})
    if not wallet:
        # Crear billetera inicial con 10,000 USD virtuales para pruebas
        wallet = {
            "email": email,
            "balance": 10000.0,
            "portfolio": {}, # {ticker: {"quantity": int, "average_price": float}}
            "last_update": datetime.utcnow()
        }
        db.wallets.insert_one(wallet)
    return wallet

def update_balance(email: str, amount: float):
    db = get_db()
    result = db.wallets.update_one(
        {"email": email},
        {
            "$inc": {"balance": amount},
            "$set": {"last_update": datetime.utcnow()}
        }
    )
    return result.modified_count > 0

def add_transaction(email: str, ticker: str, quantity: int, price: float, side: str):
    """
    side: 'buy' o 'sell'
    """
    db = get_db()
    transaction = {
        "email": email,
        "ticker": ticker,
        "quantity": quantity,
        "price": price,
        "side": side,
        "total": quantity * price,
        "timestamp": datetime.utcnow()
    }
    db.transactions.insert_one(transaction)
    
    # Actualizar portafolio
    wallet = get_wallet(email)
    portfolio = wallet.get("portfolio", {})
    
    # Manejar estructura antigua o nueva
    asset_info = portfolio.get(ticker, {"quantity": 0, "average_price": 0.0})
    if isinstance(asset_info, int): # Migración simple para datos viejos
        asset_info = {"quantity": asset_info, "average_price": price}

    current_qty = asset_info["quantity"]
    current_avg = asset_info["average_price"]

    if side == "buy":
        new_qty = current_qty + quantity
        # Cálculo del precio promedio ponderado
        new_avg = ((current_qty * current_avg) + (quantity * price)) / new_qty
        portfolio[ticker] = {"quantity": new_qty, "average_price": new_avg}
    else:
        new_qty = current_qty - quantity
        if new_qty <= 0:
            if ticker in portfolio:
                del portfolio[ticker]
        else:
            portfolio[ticker] = {"quantity": new_qty, "average_price": current_avg}
        
    db.wallets.update_one(
        {"email": email},
        {"$set": {"portfolio": portfolio, "last_update": datetime.utcnow()}}
    )

def buy_stock(email: str, ticker: str, quantity: int, price: float):
    wallet = get_wallet(email)
    total_cost = quantity * price
    
    if wallet["balance"] < total_cost:
        return False, "Saldo insuficiente para completar la compra."
    
    # Restar saldo
    update_balance(email, -total_cost)
    # Registrar transacción y actualizar portafolio
    add_transaction(email, ticker, quantity, price, "buy")
    
    return True, f"Compra de {quantity} acciones de {ticker} exitosa."

def sell_stock(email: str, ticker: str, quantity: int, price: float):
    wallet = get_wallet(email)
    portfolio = wallet.get("portfolio", {})
    
    asset_info = portfolio.get(ticker, {"quantity": 0})
    if isinstance(asset_info, int): # Migración simple
        asset_info = {"quantity": asset_info}

    current_qty = asset_info["quantity"]
    if current_qty < quantity:
        return False, f"No tienes suficientes acciones de {ticker} para vender (tienes {current_qty})."
    
    # Sumar saldo
    total_gain = quantity * price
    update_balance(email, total_gain)
    # Registrar transacción y actualizar portafolio
    add_transaction(email, ticker, quantity, price, "sell")
    
    return True, f"Venta de {quantity} acciones de {ticker} exitosa."
