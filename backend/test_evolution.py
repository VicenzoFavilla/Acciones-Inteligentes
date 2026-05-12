from config.db import get_db
from services.orders import create_order, check_and_execute_orders
from services.wallet import get_wallet, transfer_between_subwallets
import os

def test_backend():
    print("Iniciando prueba de backend...")
    db = get_db()
    
    # 1. Verificar índices
    print("\n1. Verificando índices...")
    for col in ["transactions", "orders", "history"]:
        indexes = db[col].index_information()
        print(f"  - {col}: {list(indexes.keys())}")
    
    email = "test@example.com"
    
    # 2. Verificar sub-billeteras
    print("\n2. Verificando sub-billeteras...")
    wallet = get_wallet(email)
    if "sub_wallets" in wallet:
        print(f"  - Sub-billeteras encontradas: {list(wallet['sub_wallets'].keys())}")
        print(f"  - Balance Spot: {wallet['sub_wallets']['spot']['balance']}")
    else:
        print("  - ERROR: Sub-billeteras no creadas")
        
    # 3. Probar transferencia
    print("\n3. Probando transferencia Spot -> Earn...")
    success, msg = transfer_between_subwallets(email, "spot", "earn", 1000.0)
    print(f"  - Resultado: {'Éxito' if success else 'Fallo'} - {msg}")
    
    # 4. Probar creación de orden Stop-Loss
    print("\n4. Creando orden Stop-Loss...")
    order_id = create_order(email, "TSLA", 5, 150.0, "sell", "stop_loss")
    print(f"  - Orden creada: {order_id}")
    
    # 5. Ejecutar matcher con precio simulado
    print("\n5. Probando Order Matcher...")
    market_prices = {"TSLA": {"price": 140.0}} # Debería activar el Stop-Loss (Sell if <= 150)
    check_and_execute_orders(market_prices)
    
    order = db.orders.find_one({"_id": order_id})
    if order: # create_order returns a string, but find_one needs ObjectId or string depending on how it's stored.
        # En MongoDB atlas y local, _id suele ser ObjectId. 
        # Pero create_order usó inserted_id que devolvió.
        pass
    
    # Buscar por email y ticker para estar seguros
    order = db.orders.find_one({"email": email, "ticker": "TSLA", "order_type": "stop_loss"})
    if order and order.get("status") == "executed":
        print("  - Orden ejecutada correctamente por el matcher.")
    else:
        print(f"  - Estado de la orden: {order.get('status') if order else 'No encontrada'}")

if __name__ == "__main__":
    test_backend()
