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
         patch("api.agent.get_db") as mock_agent_db, \
         patch("services.orders.get_db") as mock_orders_db, \
         patch("services.wallet.get_db") as mock_wallet_service_db, \
         patch("agent.tools.get_db") as mock_tools_db, \
         patch("agent.orchestrator.get_db") as mock_orch_db:
        
        db = MagicMock()
        mock_deps_db.return_value = db
        mock_auth_db.return_value = db
        mock_stocks_db.return_value = db
        mock_wallet_db.return_value = db
        mock_trading_db.return_value = db
        mock_agent_db.return_value = db
        mock_orders_db.return_value = db
        mock_wallet_service_db.return_value = db
        mock_tools_db.return_value = db
        mock_orch_db.return_value = db

        
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


# ==========================================
# 6. AUTONOMOUS FINANCIAL AGENT (XGBoost + Gemini + Tools + Risk)
# ==========================================

def test_agent_tools_ml_signal():
    from agent.tools import get_ml_signal
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.10, 0.90]])
    mock_feat = pd.DataFrame([{"col1": 1.0}])

    with patch("agent.tools.get_or_load_xgboost_model", return_value=mock_model), \
         patch("agent.tools.extract_technical_features", return_value=mock_feat):
        res = get_ml_signal("NVDA")
        assert res["ticker"] == "NVDA"
        assert res["signal"] == "BUY"
        assert res["confidence"] == 0.9000


def test_agent_tools_portfolio_risk_limit():
    from agent.tools import place_trade_order
    # Intentar asignar 15% (debe rechazarse por superar el límite del 10%)
    res = place_trade_order("NVDA", "BUY", 0.15, email="test@example.com")
    assert res["status"] == "rejected"
    assert "Límite de riesgo excedido" in res["error"]


def test_agent_orchestrator_decision_loop(mock_db):
    from agent.orchestrator import run_financial_agent
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_client.chats.create.return_value = mock_chat

    call_tool = MagicMock()
    call_tool.name = "get_ml_signal"
    call_tool.args = {"ticker": "AAPL"}

    resp1 = MagicMock()
    resp1.function_calls = [call_tool]
    resp1.text = None

    resp2 = MagicMock()
    resp2.function_calls = []
    resp2.text = "Dictamen Final: Mantener posición (HOLD)."

    mock_chat.send_message.side_effect = [resp1, resp2]
    mock_db.agent_traces.insert_one.return_value.inserted_id = "trace_consolidated_1"

    with patch("agent.tools.get_or_load_xgboost_model") as mock_m, \
         patch("agent.tools.extract_technical_features") as mock_f:
        mock_model_obj = MagicMock()
        mock_model_obj.predict_proba.return_value = [[0.5, 0.5]]
        mock_m.return_value = mock_model_obj
        mock_f.return_value = MagicMock()

        result = run_financial_agent("AAPL", user_email="test@example.com", client=mock_client)
        assert result["ticker"] == "AAPL"
        assert "Dictamen Final" in result["final_verdict"]
        assert len(result["tool_calls"]) == 1


def test_agent_endpoints_flow(auth_headers, mock_db):
    from bson import ObjectId
    # 1. Info
    resp_info = client.get("/agent/info")
    assert resp_info.status_code == 200
    assert "get_ml_signal" in resp_info.json()["available_tools"]

    # 2. Analyze
    with patch("api.agent.run_financial_agent", return_value={"trace_id": "t1", "ticker": "TSLA", "final_verdict": "BUY"}):
        resp_an = client.post("/agent/analyze", json={"ticker": "TSLA"}, headers=auth_headers)
        assert resp_an.status_code == 200
        assert resp_an.json()["data"]["ticker"] == "TSLA"

    # 3. Approve HITL
    oid = ObjectId()
    mock_db.orders.find_one.return_value = {
        "_id": oid,
        "email": "test@example.com",
        "ticker": "TSLA",
        "action": "BUY",
        "quantity": 2,
        "estimated_price": 200.0,
        "status": "pending_approval"
    }
    with patch("api.agent.buy_stock", return_value=(True, "Compra aprobada")):
        resp_app = client.post(f"/agent/orders/{str(oid)}/approve", json={"notes": "OK"}, headers=auth_headers)
        assert resp_app.status_code == 200
        assert resp_app.json()["status"] == "success"

