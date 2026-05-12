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
            "sub_wallets": {
                "spot": {"balance": 10000.0, "portfolio": {}},
                "earn": {"balance": 0.0, "portfolio": {}}
            },
            "portfolio": {}, # {ticker: {"quantity": int, "average_price": float}}
            "last_update": datetime.utcnow()
        }
        db.wallets.insert_one(wallet)
    elif "sub_wallets" not in wallet:
        # Migración: mover balance actual a Spot
        balance = wallet.get("balance", 0.0)
        portfolio = wallet.get("portfolio", {})
        sub_wallets = {
            "spot": {"balance": balance, "portfolio": portfolio},
            "earn": {"balance": 0.0, "portfolio": {}}
        }
        db.wallets.update_one(
            {"email": email},
            {"$set": {"sub_wallets": sub_wallets}}
        )
        wallet["sub_wallets"] = sub_wallets
    return wallet

def transfer_between_subwallets(email: str, from_wallet: str, to_wallet: str, amount: float):
    if amount <= 0:
        return False, "El monto debe ser positivo"
    
    db = get_db()
    wallet = get_wallet(email)
    
    if from_wallet not in wallet["sub_wallets"] or to_wallet not in wallet["sub_wallets"]:
        return False, "Sub-billetera no válida"
        
    if wallet["sub_wallets"][from_wallet]["balance"] < amount:
        return False, f"Saldo insuficiente en {from_wallet}"
        
    db.wallets.update_one(
        {"email": email},
        {
            "$inc": {
                f"sub_wallets.{from_wallet}.balance": -amount,
                f"sub_wallets.{to_wallet}.balance": amount
            },
            "$set": {"last_update": datetime.utcnow()}
        }
    )
    return True, f"Transferencia de ${amount} desde {from_wallet} a {to_wallet} exitosa"

def update_balance(email: str, amount: float, wallet_type: str = "spot"):
    db = get_db()
    result = db.wallets.update_one(
        {"email": email},
        {
            "$inc": {f"sub_wallets.{wallet_type}.balance": amount},
            "$set": {"last_update": datetime.utcnow()}
        }
    )
    # También actualizamos el balance global por compatibilidad
    db.wallets.update_one(
        {"email": email},
        {"$inc": {"balance": amount}}
    )
    return result.modified_count > 0

def add_transaction(email: str, ticker: str, quantity: int, price: float, side: str, wallet_type: str = "spot"):
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
        "wallet_type": wallet_type,
        "timestamp": datetime.utcnow()
    }
    db.transactions.insert_one(transaction)
    
    # Actualizar portafolio de la sub-billetera
    wallet = get_wallet(email)
    sub_wallet = wallet["sub_wallets"].get(wallet_type, {"portfolio": {}})
    portfolio = sub_wallet.get("portfolio", {})
    
    asset_info = portfolio.get(ticker, {"quantity": 0, "average_price": 0.0})
    current_qty = asset_info["quantity"]
    current_avg = asset_info["average_price"]

    if side == "buy":
        new_qty = current_qty + quantity
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
        {
            "$set": {
                f"sub_wallets.{wallet_type}.portfolio": portfolio,
                "portfolio": portfolio, # Sincronizar con el global por ahora
                "last_update": datetime.utcnow()
            }
        }
    )

def buy_stock(email: str, ticker: str, quantity: int, price: float, wallet_type: str = "spot"):
    wallet = get_wallet(email)
    total_cost = quantity * price
    
    sub_wallet_balance = wallet["sub_wallets"].get(wallet_type, {}).get("balance", 0.0)
    
    if sub_wallet_balance < total_cost:
        return False, f"Saldo insuficiente en {wallet_type} para completar la compra."
    
    # Restar saldo
    update_balance(email, -total_cost, wallet_type)
    # Registrar transacción y actualizar portafolio
    add_transaction(email, ticker, quantity, price, "buy", wallet_type)
    
    return True, f"Compra de {quantity} acciones de {ticker} exitosa en {wallet_type}."

def sell_stock(email: str, ticker: str, quantity: int, price: float, wallet_type: str = "spot"):
    wallet = get_wallet(email)
    sub_wallet = wallet["sub_wallets"].get(wallet_type, {})
    portfolio = sub_wallet.get("portfolio", {})
    
    asset_info = portfolio.get(ticker, {"quantity": 0})
    current_qty = asset_info["quantity"]
    if current_qty < quantity:
        return False, f"No tienes suficientes acciones de {ticker} en {wallet_type} para vender (tienes {current_qty})."
    
    # Sumar saldo
    total_gain = quantity * price
    update_balance(email, total_gain, wallet_type)
    # Registrar transacción y actualizar portafolio
    add_transaction(email, ticker, quantity, price, "sell", wallet_type)
    
    return True, f"Venta de {quantity} acciones de {ticker} exitosa en {wallet_type}."
