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
            "portfolio": {}, # {ticker: quantity}
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
    
    current_qty = portfolio.get(ticker, 0)
    if side == "buy":
        new_qty = current_qty + quantity
    else:
        new_qty = current_qty - quantity
        
    if new_qty <= 0:
        if ticker in portfolio:
            del portfolio[ticker]
    else:
        portfolio[ticker] = new_qty
        
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
    
    current_qty = portfolio.get(ticker, 0)
    if current_qty < quantity:
        return False, f"No tienes suficientes acciones de {ticker} para vender (tienes {current_qty})."
    
    # Sumar saldo
    total_gain = quantity * price
    update_balance(email, total_gain)
    # Registrar transacción y actualizar portafolio
    add_transaction(email, ticker, quantity, price, "sell")
    
    return True, f"Venta de {quantity} acciones de {ticker} exitosa."
