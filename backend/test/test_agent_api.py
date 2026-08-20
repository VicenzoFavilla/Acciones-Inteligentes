"""Pruebas de endpoints REST del Agente Financiero y Human-in-the-Loop."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from bson import ObjectId

from main import app
from services.auth import create_access_token

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
