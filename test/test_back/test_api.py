import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure the root directory is in sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import app

client = TestClient(app)

# Mock response for get_stock_info to avoid hitting Yahoo Finance API
mock_stock_info = {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "price": 150.0,
    "change": 1.5,
    "volume": 1000000
}

@patch("main.get_stock_info")
def test_recommendation_endpoint(mock_get_info):
    mock_get_info.return_value = mock_stock_info
    
    response = client.post("/recomendacion?ticker=AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert "recomendacion" in data
    assert data["nombre"] == "Apple Inc."

@patch("main.get_stock_info")
def test_recommendation_endpoint_not_found(mock_get_info):
    mock_get_info.return_value = None
    
    response = client.post("/recomendacion?ticker=INVALID")
    assert response.status_code == 200
    assert response.json() == {"error": "No se pudo obtener información para el ticker"}

@patch("main.get_stock_info")
@patch("main.smart_recommendation")
def test_predict_endpoint(mock_smart_rec, mock_get_info):
    mock_get_info.return_value = mock_stock_info
    mock_smart_rec.return_value = "Compra ficiticia"

    response = client.get("/predict/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["recomendacion"] == "Compra ficiticia"
    assert data["precio"] == 150.0

@patch("main.get_stock_info")
@patch("main.smart_recommendation")
def test_predict_endpoint_custom_params(mock_smart_rec, mock_get_info):
    mock_get_info.return_value = mock_stock_info
    mock_smart_rec.return_value = "Venta ficiticia"

    response = client.get("/predict/AAPL?model=global_xgb&threshold=0.8")
    assert response.status_code == 200
    data = response.json()
    
    # Verify mock was called with correct params
    mock_smart_rec.assert_called_with(ticker="AAPL", model_type="global_xgb", prob_threshold=0.8)
    assert data["recomendacion"] == "Venta ficiticia"
