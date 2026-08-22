"""Pruebas unitarias de las 4 herramientas (Tools) del Agente Financiero Autónomo."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from agent.tools import (
    get_ml_signal,
    get_market_news,
    get_portfolio_status,
    place_trade_order,
    extract_technical_features
)
from agent.ml_loader import model_cache, get_or_load_xgboost_model


def test_tool_get_ml_signal_buy():
    """Prueba get_ml_signal cuando la probabilidad es > 0.65 -> BUY."""
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.20, 0.80]])
    mock_features = pd.DataFrame([{"feat1": 1.0}])

    with patch("agent.tools.get_or_load_xgboost_model", return_value=mock_model), \
         patch("agent.tools.extract_technical_features", return_value=mock_features):
        result = get_ml_signal("NVDA")
        assert result["ticker"] == "NVDA"
        assert result["signal"] == "BUY"
        assert result["confidence"] == 0.8000


def test_tool_get_ml_signal_sell():
    """Prueba get_ml_signal cuando la probabilidad es < 0.35 -> SELL."""
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.80, 0.20]])
    mock_features = pd.DataFrame([{"feat1": 1.0}])

    with patch("agent.tools.get_or_load_xgboost_model", return_value=mock_model), \
         patch("agent.tools.extract_technical_features", return_value=mock_features):
        result = get_ml_signal("AAPL")
        assert result["ticker"] == "AAPL"
        assert result["signal"] == "SELL"
        assert result["confidence"] == 0.2000


def test_tool_get_ml_signal_hold():
    """Prueba get_ml_signal cuando 0.35 <= prob <= 0.65 -> HOLD."""
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.45, 0.55]])
    mock_features = pd.DataFrame([{"feat1": 1.0}])

    with patch("agent.tools.get_or_load_xgboost_model", return_value=mock_model), \
         patch("agent.tools.extract_technical_features", return_value=mock_features):
        result = get_ml_signal("MSFT")
        assert result["ticker"] == "MSFT"
        assert result["signal"] == "HOLD"
        assert result["confidence"] == 0.5500


def test_tool_get_ml_signal_fallback():
    """Prueba fallback ante datos técnicos insuficientes."""
    with patch("agent.tools.extract_technical_features", return_value=None):
        result = get_ml_signal("UNKNOWN")
        assert result["signal"] == "HOLD"
        assert result["confidence"] == 0.5000


def test_tool_get_market_news_filters_by_ticker_and_translates_to_spanish():
    """No expone noticias sectoriales y traduce las vinculadas al ticker."""
    mock_raw_news = [
        {
            "title": "NVDA Earnings Surge",
            "summary": "Nvidia reported record revenues across data center AI chips.",
            "publisher": "Reuters",
            "relatedTickers": ["NVDA"],
            "providerPublishTime": 1700000000
        },
        {
            "title": "Tech Rally Continues",
            "summary": "Nasdaq hits new all time high driven by semiconductors.",
            "publisher": "Bloomberg",
            "providerPublishTime": 1700003600
        }
    ]

    mock_ticker = MagicMock()
    mock_ticker.news = mock_raw_news

    translated_news = [{"title": "Las ganancias de NVDA se disparan", "summary": "Nvidia informó ingresos récord."}]
    with patch("yfinance.Ticker", return_value=mock_ticker), \
         patch("agent.tools._translate_news_to_spanish", side_effect=lambda news: [
             {**news[0], **translated_news[0], "language": "es"}
         ]):
        news = get_market_news("NVDA", limit=2)
        assert len(news) == 1
        for item in news:
            assert "title" in item
            assert "summary" in item
            assert "source" in item
            assert "time_published" in item
            assert len(item["title"]) > 0
            assert item["language"] == "es"
        assert news[0]["title"] == "Las ganancias de NVDA se disparan"


def test_tool_get_portfolio_status():
    """Prueba cálculo de balance, valor total de cartera y desglose de posiciones."""
    mock_wallet = {
        "email": "user@test.com",
        "balance": 5000.0,
        "sub_wallets": {
            "spot": {
                "balance": 5000.0,
                "portfolio": {
                    "AAPL": {"quantity": 10, "average_price": 150.0}
                }
            }
        }
    }

    with patch("agent.tools.get_wallet", return_value=mock_wallet), \
         patch("agent.tools.get_stock_info", return_value={"price": 180.0}):
        status = get_portfolio_status("user@test.com")
        assert status["cash_balance"] == 5000.0
        # 10 * 180 = 1800 de acciones + 5000 cash = 6800
        assert status["total_portfolio_value"] == 6800.0
        assert len(status["positions"]) == 1
        pos = status["positions"][0]
        assert pos["ticker"] == "AAPL"
        assert pos["quantity"] == 10
        assert pos["market_value"] == 1800.0
        assert pos["pnl"] == 300.0  # 1800 - 1500
        assert pos["pnl_pct"] == 20.0


def test_tool_place_trade_order_valid():
    """Prueba orden de compra válida cumpliendo regla de riesgo (<10%)."""
    mock_status = {
        "cash_balance": 10000.0,
        "total_portfolio_value": 10000.0,
        "positions": []
    }
    mock_db = MagicMock()
    mock_db.orders.insert_one.return_value.inserted_id = "mock_order_123"

    with patch("agent.tools.get_portfolio_status", return_value=mock_status), \
         patch("agent.tools.get_stock_info", return_value={"price": 200.0}), \
         patch("agent.tools.get_db", return_value=mock_db):
        
        # Asignar 5% ($500 -> 2 acciones de $200)
        res = place_trade_order("AAPL", "BUY", 0.05, email="user@test.com")
        assert res["ticker"] == "AAPL"
        assert res["action"] == "BUY"
        assert res["status"] == "pending_approval"
        assert res["quantity"] >= 2
        assert "transaction_id" in res


def test_tool_place_trade_order_risk_limit_exceeded():
    """Prueba rechazo cuando se intenta asignar más del 10% del capital."""
    res = place_trade_order("NVDA", "BUY", 0.15, email="user@test.com")
    assert res["status"] == "rejected"
    assert "Límite de riesgo excedido" in res["error"]


def test_tool_place_trade_order_invalid_action():
    """Prueba rechazo ante acción inválida."""
    res = place_trade_order("NVDA", "INVALID_ACTION", 0.05, email="user@test.com")
    assert res["status"] == "rejected"
    assert "no válida" in res["error"]


def test_lazy_loading_cache():
    """Prueba que el ModelCache almacene y reutilice instancias de modelos."""
    model_cache.clear()
    fake_model = MagicMock()
    model_cache.set_model("TEST_KEY", fake_model)
    
    retrieved = model_cache.get_model("test_key")
    assert retrieved is fake_model
    model_cache.clear()
    assert model_cache.get_model("test_key") is None
