import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import app
from services.auth import create_access_token

client = TestClient(app)

@pytest.fixture
def test_token():
    return create_access_token(data={"sub": "test@user.com"})

@pytest.fixture
def auth_headers(test_token):
    return {"Authorization": f"Bearer {test_token}"}

@pytest.fixture
def mock_db():
    with patch("api.deps.get_db") as mock_deps, \
         patch("api.auth.get_db") as mock_auth, \
         patch("api.stocks.get_db") as mock_stocks, \
         patch("api.trading.get_db") as mock_trading:
        db = MagicMock()
        mock_deps.return_value = db
        mock_auth.return_value = db
        mock_stocks.return_value = db
        mock_trading.return_value = db
        # Para get_current_user
        db.users.find_one.return_value = {"email": "test@user.com"}
        yield db


def test_add_watchlist(mock_db, auth_headers):
    response = client.post("/user/watchlist/AAPL", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_db.users.update_one.assert_called_with(
        {"email": "test@user.com"},
        {"$addToSet": {"watchlist": "AAPL"}}
    )

def test_remove_watchlist(mock_db, auth_headers):
    response = client.delete("/user/watchlist/AAPL", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_db.users.update_one.assert_called_with(
        {"email": "test@user.com"},
        {"$pull": {"watchlist": "AAPL"}}
    )

@patch("api.trading.get_stock_info")
@patch("api.trading.sell_stock")
def test_sell_stock_endpoint(mock_sell_stock, mock_get_stock_info, mock_db, auth_headers):
    mock_get_stock_info.return_value = {"price": 150.0}
    mock_sell_stock.return_value = (True, "Venta exitosa")
    
    response = client.post("/trade/sell?ticker=AAPL&quantity=2", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Venta exitosa", "price_sold": 150.0}
    assert mock_sell_stock.called

@patch("api.trading.get_stock_info")
@patch("api.trading.sell_stock")
def test_sell_stock_endpoint_insufficient(mock_sell_stock, mock_get_stock_info, mock_db, auth_headers):
    mock_get_stock_info.return_value = {"price": 150.0}
    mock_sell_stock.return_value = (False, "No posees suficientes acciones")
    
    response = client.post("/trade/sell?ticker=AAPL&quantity=10", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "error", "message": "No posees suficientes acciones"}


def test_websocket_market():
    # Probar la conexión al websocket
    with client.websocket_connect("/ws/market") as websocket:
        websocket.send_text("ping")
        assert True
