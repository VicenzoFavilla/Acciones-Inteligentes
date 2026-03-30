"""
Script de testing automatizado — VERSION CON OUTPUT LIMPIO
"""
import requests
import sys

BASE_URL = "http://127.0.0.1:8001"
TEST_EMAIL = "test_auto@acciones.com"
TEST_PASSWORD = "TestPass123!"
TOKEN = None

results = {"pass": 0, "fail": 0, "warn": 0}
failed_tests = []

def check(name, condition, detail=""):
    if condition:
        results["pass"] += 1
        print(f"  PASS: {name}")
    else:
        results["fail"] += 1
        msg = f"  FAIL: {name}"
        if detail:
            msg += f" [{detail}]"
        print(msg)
        failed_tests.append(name)

def warn(name, detail=""):
    results["warn"] += 1
    print(f"  WARN: {name}" + (f" [{detail}]" if detail else ""))

def section(title):
    print(f"\n--- {title} ---")

section("1. Health Check")
try:
    r = requests.get(f"{BASE_URL}/", timeout=5)
    check("Servidor responde en /", r.status_code == 200)
    check("Respuesta contiene mensaje", "message" in r.json())
except Exception as e:
    check("Servidor responde en /", False, str(e))
    print("ERROR CRITICO: Servidor no disponible. Abortando.")
    sys.exit(1)

section("2. Auth - Registro y Login")

try:
    r = requests.post(f"{BASE_URL}/register", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    data = r.json()
    if data.get("status") == "success":
        check("Registro de nuevo usuario", True)
    else:
        warn("Registro", data.get('message', ''))
except Exception as e:
    check("Registro de nuevo usuario", False, str(e))

try:
    r = requests.post(f"{BASE_URL}/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    data = r.json()
    check("Login exitoso", data.get("status") == "success")
    check("Login retorna token", "access_token" in data)
    TOKEN = data.get("access_token")
except Exception as e:
    check("Login exitoso", False, str(e))

try:
    r = requests.post(f"{BASE_URL}/login", json={"email": TEST_EMAIL, "password": "MAL!"})
    data = r.json()
    check("Login con pass incorrecta - error", data.get("status") == "error")
except Exception as e:
    check("Login con pass incorrecta - error", False, str(e))

if TOKEN:
    try:
        r = requests.get(f"{BASE_URL}/me", headers={"Authorization": f"Bearer {TOKEN}"})
        data = r.json()
        check("GET /me con token", r.status_code == 200 and "email" in data)
        check("GET /me no expone password", "password" not in data)
    except Exception as e:
        check("GET /me con token", False, str(e))
    
    try:
        r = requests.get(f"{BASE_URL}/me")
        check("GET /me sin token - 401", r.status_code == 401)
    except Exception as e:
        check("GET /me sin token - 401", False, str(e))

section("3. Datos de Mercado")

try:
    r = requests.get(f"{BASE_URL}/market", timeout=30)
    data = r.json()
    check("GET /market responde", r.status_code == 200 and isinstance(data, list))
    check("GET /market retorna datos", len(data) > 0)
    if data:
        first = data[0]
        check("Accion tiene ticker y precio", "ticker" in first and "precio" in first)
        check("variacion es numerica", isinstance(first.get("variacion"), (int, float)))
        check("NO hay cripto (BTC/ETH)", not any(t.get("ticker") in ["BTC-USD", "ETH-USD"] for t in data))
except Exception as e:
    check("GET /market responde", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/popular", timeout=30)
    data = r.json()
    check("GET /popular responde", r.status_code == 200 and isinstance(data, list))
    if data:
        check("Popular tiene campo history", "history" in data[0])
except Exception as e:
    check("GET /popular responde", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/predict/AAPL", timeout=30)
    data = r.json()
    check("GET /predict/AAPL responde", r.status_code == 200)
    check("Tiene precio y recomendacion", "precio" in data and "recomendacion" in data)
    check("Tiene OHLC para graficos", "ohlc" in data and isinstance(data["ohlc"], list))
except Exception as e:
    check("GET /predict/AAPL responde", False, str(e))

section("4. Billetera y Portfolio")

if TOKEN:
    H = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        r = requests.get(f"{BASE_URL}/wallet/info", headers=H, timeout=15)
        data = r.json()
        check("GET /wallet/info responde", data.get("status") == "success")
        wallet = data.get("wallet", {})
        check("Wallet tiene balance", "balance" in wallet)
        check("Wallet tiene total_equity", "total_equity" in wallet)
        check("Wallet tiene portfolio_details", "portfolio_details" in wallet)
        check("total_equity >= balance", wallet.get("total_equity", 0) >= wallet.get("balance", 0))
    except Exception as e:
        check("GET /wallet/info responde", False, str(e))
    
    try:
        r = requests.post(f"{BASE_URL}/wallet/deposit?amount=1000", headers=H)
        data = r.json()
        check("POST /wallet/deposit monto valido", data.get("status") == "success")
    except Exception as e:
        check("POST /wallet/deposit monto valido", False, str(e))
    
    try:
        r = requests.post(f"{BASE_URL}/wallet/deposit?amount=-50", headers=H)
        data = r.json()
        check("POST /wallet/deposit monto negativo - error", data.get("status") == "error")
    except Exception as e:
        check("POST /wallet/deposit monto negativo - error", False, str(e))

section("5. Trading")

if TOKEN:
    H = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        r = requests.post(f"{BASE_URL}/trade/buy?ticker=AAPL&quantity=1", headers=H, timeout=15)
        data = r.json()
        check("Compra 1 AAPL exitosa", data.get("status") == "success", data.get("message", ""))
        check("Respuesta tiene price_paid", "price_paid" in data)
    except Exception as e:
        check("Compra 1 AAPL exitosa", False, str(e))
    
    try:
        r = requests.post(f"{BASE_URL}/trade/buy?ticker=AAPL&quantity=0", headers=H)
        data = r.json()
        check("Compra con qty=0 - error", data.get("status") == "error")
    except Exception as e:
        check("Compra con qty=0 - error", False, str(e))
    
    try:
        r = requests.post(f"{BASE_URL}/trade/buy?ticker=AAPL&quantity=999999", headers=H, timeout=15)
        data = r.json()
        check("Compra con saldo insuficiente - error", data.get("status") == "error")
        check("Mensaje menciona saldo", "saldo" in data.get("message", "").lower() or "insuficiente" in data.get("message", "").lower())
    except Exception as e:
        check("Compra con saldo insuficiente - error", False, str(e))
    
    try:
        r = requests.post(f"{BASE_URL}/trade/sell?ticker=AAPL&quantity=1", headers=H, timeout=15)
        data = r.json()
        check("Venta 1 AAPL exitosa", data.get("status") == "success", data.get("message", ""))
    except Exception as e:
        check("Venta 1 AAPL exitosa", False, str(e))
    
    try:
        r = requests.post(f"{BASE_URL}/trade/sell?ticker=TSLA&quantity=9999", headers=H, timeout=15)
        data = r.json()
        check("Venta sin existencias - error", data.get("status") == "error")
    except Exception as e:
        check("Venta sin existencias - error", False, str(e))

section("6. Watchlist")

if TOKEN:
    H = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        r = requests.post(f"{BASE_URL}/user/watchlist/NVDA", headers=H)
        check("Agregar NVDA a watchlist", r.json().get("status") == "success")
    except Exception as e:
        check("Agregar NVDA a watchlist", False, str(e))
    
    try:
        r = requests.get(f"{BASE_URL}/user/watchlist", headers=H, timeout=20)
        data = r.json()
        check("GET /user/watchlist responde", data.get("status") == "success")
        check("NVDA en watchlist", any(w.get("ticker") == "NVDA" for w in data.get("watchlist", [])))
    except Exception as e:
        check("GET /user/watchlist responde", False, str(e))
    
    try:
        r = requests.delete(f"{BASE_URL}/user/watchlist/NVDA", headers=H)
        check("Eliminar NVDA de watchlist", r.json().get("status") == "success")
    except Exception as e:
        check("Eliminar NVDA de watchlist", False, str(e))

section("7. Historial")

if TOKEN:
    H = {"Authorization": f"Bearer {TOKEN}"}
    try:
        r = requests.get(f"{BASE_URL}/wallet/history", headers=H)
        data = r.json()
        check("GET /wallet/history responde", data.get("status") == "success")
        check("Historial es una lista", isinstance(data.get("transactions", []), list))
        txns = data.get("transactions", [])
        if txns:
            check("Transaccion tiene ticker, price, type", all(k in txns[0] for k in ["ticker", "price", "side"]))
    except Exception as e:
        check("GET /wallet/history responde", False, str(e))

# === RESUMEN FINAL ===
total = results["pass"] + results["fail"] + results["warn"]
score = (results["pass"] / max(total, 1)) * 100
print(f"\n{'='*50}")
print(f"RESUMEN FINAL: {total} tests")
print(f"  PASS: {results['pass']}")
print(f"  FAIL: {results['fail']}")  
print(f"  WARN: {results['warn']}")
print(f"  Score: {score:.1f}%")
if failed_tests:
    print(f"\nTests fallidos:")
    for t in failed_tests:
        print(f"  - {t}")
print(f"{'='*50}")

sys.exit(0 if results["fail"] == 0 else 1)
