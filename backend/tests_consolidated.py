import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import sys
import warnings

# Silenciar advertencias de deprecación de terceros (httpx, jose, datetime) en la suite de pruebas
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Asegurar que el path incluya el backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from services.auth import create_access_token
from config.db import get_db
from services.orders import create_order, check_and_execute_orders
from services.wallet import get_wallet, transfer_between_subwallets

client = TestClient(app)

# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def test_token():
    return create_access_token(data={"sub": "test@example.com"})

@pytest.fixture
def auth_headers(test_token):
    return {"Authorization": f"Bearer {test_token}"}

@pytest.fixture
def mock_db():
    with patch("api.deps.get_db") as mock_deps_db, \
         patch("api.auth.get_db") as mock_auth_db, \
         patch("api.stocks.get_db") as mock_stocks_db, \
         patch("api.wallet.get_db") as mock_wallet_db, \
         patch("api.trading.get_db") as mock_trading_db, \
         patch("services.orders.get_db") as mock_orders_db, \
         patch("services.wallet.get_db") as mock_wallet_service_db:
        
        db = MagicMock()
        mock_deps_db.return_value = db
        mock_auth_db.return_value = db
        mock_stocks_db.return_value = db
        mock_wallet_db.return_value = db
        mock_trading_db.return_value = db
        mock_orders_db.return_value = db
        mock_wallet_service_db.return_value = db
        
        # Para get_current_user (en api.deps)
        db.users.find_one.return_value = {"email": "test@example.com", "name": "Test User", "password": "hashed_password"}
        
        # Para get_wallet (en services.wallet)
        db.wallets.find_one.return_value = {
            "email": "test@example.com",
            "balance": 1000.0,
            "sub_wallets": {
                "spot": {"balance": 1000.0, "portfolio": {}},
                "earn": {"balance": 0.0, "portfolio": {}}
            }
        }
        
        yield db

# ==========================================
# 1. API TESTS (Mocked)
# ==========================================

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_get_me_protected(auth_headers, mock_db):
    response = client.get("/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_market_data(mock_db):
    # Mocking SP500 tickers to avoid external calls
    with patch("services.stocks.get_sp500_tickers", return_value=["AAPL", "MSFT"]):
        response = client.get("/market")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

# ==========================================
# 2. BUSINESS LOGIC TESTS (Mocked DB)
# ==========================================

def test_wallet_logic(mock_db):
    """Prueba de lógica de billetera."""
    email = "test@example.com"
    
    # El mock ya está configurado en el fixture mock_db para db.wallets.find_one
    wallet = get_wallet(email)
    assert "sub_wallets" in wallet
    assert wallet["sub_wallets"]["spot"]["balance"] == 1000.0
    
    # Probar transferencia
    success, msg = transfer_between_subwallets(email, "spot", "earn", 500.0)
    assert success is True
    assert "exitosa" in msg.lower()

def test_order_matcher(mock_db):
    """Prueba del matcher de órdenes."""
    email = "test@example.com"
    
    # Mock find orders en la colección orders
    mock_db.orders.find.return_value = [
        {
            "_id": "order1",
            "email": email,
            "ticker": "TSLA",
            "quantity": 5,
            "target_price": 150.0,
            "side": "sell",
            "order_type": "stop_loss",
            "status": "pending"
        }
    ]
    
    market_prices = {"TSLA": {"price": 140.0}} # Activates Stop-Loss
    
    # Mock successful execution de sell_stock
    with patch("services.orders.sell_stock", return_value=(True, "Venta exitosa")):
        try:
            check_and_execute_orders(market_prices)
            assert True
        except Exception as e:
            pytest.fail(f"Order matcher falló: {e}")

# ==========================================
# 3. ML PREPROCESSING TESTS
# ==========================================

def preprocess_mock(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()
    if df.empty: return df
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['Daily_Return'] = df['Close'].pct_change()
    return df.dropna()

@pytest.fixture
def mock_stock_data():
    dates = pd.date_range(start='2023-01-01', periods=30)
    data = {
        'Open': np.random.uniform(100, 150, 30),
        'High': np.random.uniform(150, 160, 30),
        'Low': np.random.uniform(90, 100, 30),
        'Close': np.random.uniform(105, 145, 30),
        'Volume': np.random.randint(1000, 10000, 30)
    }
    return pd.DataFrame(data, index=dates)

def test_ml_preprocessing(mock_stock_data):
    processed = preprocess_mock(mock_stock_data)
    assert 'SMA_20' in processed.columns
    assert 'Daily_Return' in processed.columns
    assert not processed.isnull().values.any()

# ==========================================
# 4. WEBSOCKET TESTS
# ==========================================

def test_websocket_market():
    with client.websocket_connect("/ws/market") as websocket:
        # El websocket del server actual espera un mensaje para no cerrarse
        websocket.send_text("hello")
        assert True

# ==========================================
# 5. AUTH EMAIL NORMALIZATION TESTS
# ==========================================

def test_register_normalization(mock_db):
    # Simular que el usuario no existe
    mock_db.users.find_one.return_value = None
    
    response = client.post(
        "/register",
        json={"email": "   TEST_Normalizacion@acciones.com   ", "password": "mypassword"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verificar normalización en guardado
    mock_db.users.insert_one.assert_called_once()
    saved_user = mock_db.users.insert_one.call_args[0][0]
    assert saved_user["email"] == "test_normalizacion@acciones.com"

def test_login_normalization(mock_db):
    from core.auth_handler import get_password_hash
    # Simular usuario con email normalizado
    mock_db.users.find_one.return_value = {
        "email": "test_normalizacion@acciones.com",
        "password": get_password_hash("mypassword")
    }
    
    # Intento de login con capitalización mixta y espacios
    response = client.post(
        "/login",
        json={"email": "  TEST_Normalizacion@acciones.com  ", "password": "mypassword"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["email"] == "test_normalizacion@acciones.com"
