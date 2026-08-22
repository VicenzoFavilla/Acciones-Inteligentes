"""Pruebas de endpoints REST del Agente Financiero y Human-in-the-Loop."""

import pytest
import pandas as pd
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from bson import ObjectId

from main import app
from services.auth import create_access_token
from api.stocks import get_market_list, get_market_opportunities, predict_stock
from ml.recomendacion import basic_recommendation

client = TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_access_token(data={"sub": "trader@acciones.com"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_db():
    with patch("api.deps.get_db") as mock_deps_db, \
         patch("api.agent.get_db") as mock_agent_db:
        db = MagicMock()
        mock_deps_db.return_value = db
        mock_agent_db.return_value = db
        db.users.find_one.return_value = {"email": "trader@acciones.com", "name": "Trader AI"}
        yield db


def test_agent_info():
    """Prueba GET /agent/info sin requerir autenticación."""
    response = client.get("/agent/info")
    assert response.status_code == 200
    data = response.json()
    assert "available_tools" in data
    assert "get_ml_signal" in data["available_tools"]
    assert "place_trade_order" in data["available_tools"]
    assert data["risk_limits"]["max_capital_per_operation_pct"] == 10.0


def test_agent_news_endpoint():
    """El endpoint expone noticias verificables obtenidas por la herramienta del agente."""
    with patch("api.agent.get_market_news", return_value=[{"title": "Titular en español", "source": "Reuters", "language": "es"}]) as news_mock:
        response = client.get("/agent/news/NVDA")

    assert response.status_code == 200
    assert response.json()["ticker"] == "NVDA"
    assert response.json()["count"] == 1
    assert response.json()["news"][0]["language"] == "es"
    news_mock.assert_called_once_with("NVDA", limit=5)


def test_prediction_uses_basic_recommendation_when_global_model_is_missing():
    """La UI no debe recibir el error de carga del modelo como una recomendación."""
    with patch("api.stocks.get_stock_info", return_value={"price": 100.0, "change": -3.0}), \
         patch("api.stocks.smart_recommendation", return_value="No hay modelo global XGB disponible."), \
         patch("api.stocks.get_price_history", return_value=None):
        result = predict_stock("NVDA")

    assert result["recomendacion"] == basic_recommendation(-3.0)


def test_market_endpoint_returns_only_the_requested_page():
    """El mercado devuelve 50 símbolos por página, no todo el universo."""
    tickers = [f"T{i:03}" for i in range(123)]
    with patch("api.stocks.get_sp500_tickers", return_value=tickers), \
         patch("api.stocks.get_stock_info", side_effect=lambda ticker: {
             "name": ticker,
             "price": 10.0,
             "change": 1.0,
             "volume": 100,
         }):
        result = get_market_list(page=2, page_size=50)

    assert result["total_items"] == 123
    assert result["total_pages"] == 3
    assert result["current_page"] == 2
    assert len(result["items"]) == 50
    assert result["items"][0]["ticker"] == "T050"


def test_market_opportunities_include_model_signal_and_disclaimer():
    """Las oportunidades son informativas y exponen señal y confianza ML."""
    with patch("api.stocks.get_stock_info", return_value={
        "name": "Nvidia", "price": 100.0, "change": 1.5,
    }), patch("api.stocks.get_ml_signal", return_value={
        "signal": "BUY", "confidence": 0.82,
    }), patch("api.stocks.get_price_history", return_value=pd.Series([98.0, 100.0])):
        result = get_market_opportunities(limit=2)

    assert len(result["items"]) == 2
    assert result["items"][0]["signal"] == "BUY"
    assert result["items"][0]["confidence"] == 0.82
    assert result["items"][0]["history"] == [98.0, 100.0]
    assert "informativas" in result["disclaimer"]


def test_agent_analyze_endpoint(auth_headers, mock_db):
    """Prueba POST /agent/analyze autenticado con ejecución del agente mockeada."""
    mock_agent_output = {
        "trace_id": "trace_test_001",
        "ticker": "AAPL",
        "final_verdict": "Veredicto: Mantener posición (HOLD).",
        "tool_calls": [],
        "execution_time_seconds": 1.2
    }

    with patch("api.agent.run_financial_agent", return_value=mock_agent_output):
        response = client.post(
            "/agent/analyze",
            json={"ticker": "AAPL"},
            headers=auth_headers
        )
        assert response.status_code == 200
        res = response.json()
        assert res["status"] == "success"
        assert res["data"]["ticker"] == "AAPL"
        assert "trace_id" in res["data"]


def test_agent_approve_order_hitl(auth_headers, mock_db):
    """Prueba POST /agent/orders/{order_id}/approve (Human-In-The-Loop)."""
    fake_id = ObjectId()
    mock_order = {
        "_id": fake_id,
        "email": "trader@acciones.com",
        "ticker": "NVDA",
        "action": "BUY",
        "quantity": 5,
        "estimated_price": 120.0,
        "status": "pending_approval"
    }
    mock_db.orders.find_one.return_value = mock_order

    with patch("api.agent.buy_stock", return_value=(True, "Compra ejecutada correctamente")):
        response = client.post(
            f"/agent/orders/{str(fake_id)}/approve",
            json={"notes": "Aprobado por el analista."},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "ejecutada" in response.json()["message"]


def test_agent_reject_order_hitl(auth_headers, mock_db):
    """Prueba POST /agent/orders/{order_id}/reject."""
    fake_id = ObjectId()
    mock_order = {
        "_id": fake_id,
        "email": "trader@acciones.com",
        "ticker": "NVDA",
        "action": "BUY",
        "quantity": 5,
        "status": "pending_approval"
    }
    mock_db.orders.find_one.return_value = mock_order

    response = client.post(
        f"/agent/orders/{str(fake_id)}/reject",
        json={"notes": "Riesgo excesivo en el sector."},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "rechazada" in response.json()["message"].lower()
