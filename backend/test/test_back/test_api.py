import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os
import warnings
import pandas as pd
import hashlib

# Filtrar DeprecationWarning de httpx (causado por versiones antiguas de FastAPI/Starlette con httpx nuevo)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="httpx")

# Aseguramos que el directorio raíz esté en sys.path para permitir imports de backend
# Asumiendo que test_api.py está en backend/test/test_back/
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import app

client = TestClient(app)

# --- Fixtures ---

@pytest.fixture
def mock_db():
    """Mock para la base de datos MongoDB."""
    with patch("main.get_db") as mock:
        db = MagicMock()
        mock.return_value = db
        yield db

@pytest.fixture
def mock_stock_services():
    """Mock para los servicios de datos y ML."""
    with patch("main.get_stock_info") as mock_info, \
         patch("main.get_price_history") as mock_hist, \
         patch("main.smart_recommendation") as mock_smart, \
         patch("main.basic_recommendation") as mock_basic, \
         patch("main.tickers_from_usage") as mock_tickers:
        
        yield {
            "info": mock_info,
            "hist": mock_hist,
            "smart": mock_smart,
            "basic": mock_basic,
            "tickers": mock_tickers
        }

# --- Tests de API ---

def test_read_root():
    """Test del endpoint raíz."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API de Acciones Inteligentes funcionando correctamente"}

def test_get_user_found(mock_db):
    """Test para obtener usuario existente."""
    mock_db.users.find_one.return_value = {"email": "test@example.com", "name": "Test User"}
    
    response = client.get("/user/test@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["user"]["email"] == "test@example.com"

def test_get_user_not_found(mock_db):
    """Test para usuario no encontrado."""
    mock_db.users.find_one.return_value = None
    
    response = client.get("/user/unknown@example.com")
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Usuario no encontrado"

def test_recommendation_endpoint(mock_stock_services):
    """Test del endpoint POST /recomendacion."""
    mock_stock_services["info"].return_value = {
        "name": "Apple Inc.",
        "price": 150.0,
        "change": 1.5,
        "volume": 1000000
    }
    mock_stock_services["basic"].return_value = "Mantener"

    response = client.post("/recomendacion?ticker=AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["recomendacion"] == "Mantener"
    assert data["nombre"] == "Apple Inc."

def test_recommendation_endpoint_no_info(mock_stock_services):
    """Test /recomendacion cuando no se encuentra info."""
    mock_stock_services["info"].return_value = None

    response = client.post("/recomendacion?ticker=INVALID")
    assert response.status_code == 200
    assert response.json() == {"error": "No se pudo obtener información para el ticker"}

def test_predict_endpoint_success(mock_stock_services):
    """Test GET /predict/{ticker} exitoso."""
    mock_stock_services["smart"].return_value = "Compra Fuerte"
    mock_stock_services["info"].return_value = {"price": 150.0}
    # Simulamos historial como una Serie de pandas (caso 2 en main.py)
    mock_stock_services["hist"].return_value = pd.Series([100.0, 110.0, 120.0], name="Close")
    
    response = client.get("/predict/AAPL")
    assert response.status_code == 200
    data = response.json()
    
    assert data["ticker"] == "AAPL"
    assert data["recomendacion"] == "Compra Fuerte"
    assert data["precio"] == 150.0
    assert data["history"] == [100.0, 110.0, 120.0]
    
    # Verificar que smart_recommendation se llamó con los parámetros correctos según main.py
    mock_stock_services["smart"].assert_called_with("AAPL", registrar=True, model_type="global_xgb")

def test_predict_endpoint_exception(mock_stock_services):
    """Test GET /predict/{ticker} manejando excepciones."""
    # Hacemos que get_stock_info lance excepción para simular fallo general
    mock_stock_services["info"].side_effect = Exception("API Error")
    
    response = client.get("/predict/FAIL")
    assert response.status_code == 200
    data = response.json()
    # Verifica el comportamiento de fallback definido en main.py línea 108
    assert data["recomendacion"] == "Servidor en mantenimiento"
    assert data["precio"] == 0.0

def test_get_popular_stocks(mock_stock_services):
    """Test GET /popular."""
    mock_stock_services["tickers"].return_value = ["AAPL", "GOOGL"]
    
    # Configuramos side_effect para devolver info distinta para cada ticker
    def get_info_side_effect(ticker):
        if ticker == "AAPL":
            return {"name": "Apple", "price": 150, "change": 1.0}
        elif ticker == "GOOGL":
            return {"name": "Google", "price": 2800, "change": -0.5}
        return None
    
    mock_stock_services["info"].side_effect = get_info_side_effect
    
    # Historial simple
    mock_stock_services["hist"].return_value = pd.Series([100, 101, 102], name="Close")

    response = client.get("/popular")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    assert data[0]["ticker"] == "AAPL"
    assert data[1]["ticker"] == "GOOGL"
    assert data[0]["color_green"] is True  # change 1.0 >= 0
    assert data[1]["color_green"] is False # change -0.5 < 0

def test_save_user_decision_feedback(mock_db):
    """Test GET /feedback."""
    mock_db.acciones_usuario.update_one.return_value = MagicMock()
    
    response = client.get("/feedback?ticker=AAPL&decision=comprar")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verificar llamada a DB
    mock_db.acciones_usuario.update_one.assert_called_once()

# --- Auth Tests ---

def test_register_success(mock_db):
    """Test registro de usuario nuevo."""
    mock_db.users.find_one.return_value = None # No existe
    
    payload = {"email": "newuser@test.com", "password": "password123"}
    response = client.post("/register", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_db.users.insert_one.assert_called_once()

def test_register_existing_user(mock_db):
    """Test registro de usuario existente falla."""
    mock_db.users.find_one.return_value = {"email": "exists@test.com"}
    
    payload = {"email": "exists@test.com", "password": "password123"}
    response = client.post("/register", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "El usuario ya existe"

def test_login_success(mock_db):
    """Test login exitoso."""
    # Hash password "secret" -> sha256
    hashed_pw = hashlib.sha256(b"secret").hexdigest()
    
    mock_db.users.find_one.return_value = {
        "email": "user@test.com", 
        "password": hashed_pw
    }

    payload = {"email": "user@test.com", "password": "secret"}
    response = client.post("/login", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["email"] == "user@test.com"

def test_login_failure(mock_db):
    """Test login fallido (password incorrecto)."""
    hashed_pw = hashlib.sha256(b"secret").hexdigest()
    mock_db.users.find_one.return_value = {
        "email": "user@test.com", 
        "password": hashed_pw
    }

    payload = {"email": "user@test.com", "password": "wrongpassword"}
    response = client.post("/login", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "error"

def test_save_decision_post(mock_db):
    """Test POST /decision."""
    mock_db.acciones_usuario.update_one.return_value.modified_count = 1
    
    payload = {"ticker": "MSFT", "decision": "no comprar"}
    response = client.post("/decision", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_save_decision_post_not_found(mock_db):
    """Test POST /decision cuando no se encuentra registro previo."""
    mock_db.acciones_usuario.update_one.return_value.modified_count = 0
    
    payload = {"ticker": "MSFT", "decision": "no comprar"}
    response = client.post("/decision", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "info"
