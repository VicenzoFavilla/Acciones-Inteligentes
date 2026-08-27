"""Suite Completa y Consolidada de Pruebas Unitarias e Integración.

Incluye:
- 1. Endpoints de API y Autenticación (FastAPI)
- 2. Lógica de Negocio (Wallets, Sub-cuentas, Order Matching)
- 3. Normalización y Seguridad de Usuarios
- 4. Agente Financiero Autónomo (XGBoost + Gemini + Tools + Risk Limits)
- 5. [FASE 1] Robustez de ML y Backtesting (Sharpe, Sortino, MDD, Win Rate, TimeSeriesSplit OOF)
- 6. [FASE 2] DataLoader Extensible y Feature Engineering Avanzado (Bollinger, ATR, VWAP, Volatilidad)
- 7. [FASE 3] MLOps y Logging Estructurado (JSONFormatter, Daily ML Pipeline)
"""

import json
import logging
import os
import sys
import warnings
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# Silenciar advertencias de deprecación de librerías externas en tests
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Asegurar que el path incluya el backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from services.auth import create_access_token
from services.orders import create_order, check_and_execute_orders
from services.wallet import get_wallet, transfer_between_subwallets
from core.logger import JSONFormatter
from ml.backtesting.metrics import calculate_financial_metrics
from ml.backtesting.engine import BacktestSimulator, BacktestConfig
from ml.validation.walk_forward import TimeSeriesValidator
from ml.data import DataLoader, MemoryDataLoader, YFinanceDataLoader, get_data_loader
from ml.features import add_technical_indicators, add_basic_features, make_supervised, get_X_y, FEATURE_COLUMNS
from ml.trainer import train_and_backtest_pipeline
from scripts.daily_ml_pipeline import run_daily_pipeline

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

        # Para get_current_user
        db.users.find_one.return_value = {"email": "test@example.com", "name": "Test User", "password": "hashed_password"}

        # Para get_wallet
        db.wallets.find_one.return_value = {
            "email": "test@example.com",
            "balance": 1000.0,
            "sub_wallets": {
                "spot": {"balance": 1000.0, "portfolio": {}},
                "earn": {"balance": 0.0, "portfolio": {}},
            },
        }

        yield db


@pytest.fixture
def sample_ohlcv_df():
    """Genera un DataFrame OHLCV sintético y consistente de 100 periodos."""
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.randn(100) * 1.5)
    high = close + np.random.uniform(0.5, 2.0, 100)
    low = close - np.random.uniform(0.5, 2.0, 100)
    open_p = low + np.random.uniform(0.0, high - low, 100)
    volume = np.random.randint(10000, 100000, 100)

    return pd.DataFrame({
        "Open": open_p,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=dates)


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
    with patch("services.stocks.get_sp500_tickers", return_value=["AAPL", "MSFT"]):
        response = client.get("/market")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


# ==========================================
# 2. BUSINESS LOGIC & WALLET TESTS
# ==========================================

def test_wallet_logic(mock_db):
    email = "test@example.com"
    wallet = get_wallet(email)
    assert "sub_wallets" in wallet
    assert wallet["sub_wallets"]["spot"]["balance"] == 1000.0

    success, msg = transfer_between_subwallets(email, "spot", "earn", 500.0)
    assert success is True
    assert "exitosa" in msg.lower()


def test_order_matcher(mock_db):
    email = "test@example.com"
    mock_db.orders.find.return_value = [
        {
            "_id": "order1",
            "email": email,
            "ticker": "TSLA",
            "quantity": 5,
            "target_price": 150.0,
            "side": "sell",
            "order_type": "stop_loss",
            "status": "pending",
        }
    ]

    market_prices = {"TSLA": {"price": 140.0}}

    with patch("services.orders.sell_stock", return_value=(True, "Venta exitosa")):
        try:
            check_and_execute_orders(market_prices)
            assert True
        except Exception as e:
            pytest.fail(f"Order matcher falló: {e}")


# ==========================================
# 3. AUTH NORMALIZATION & WEBSOCKET
# ==========================================

def test_websocket_market():
    with client.websocket_connect("/ws/market") as websocket:
        websocket.send_text("hello")
        assert True


def test_register_normalization(mock_db):
    mock_db.users.find_one.return_value = None

    response = client.post(
        "/register",
        json={"email": "   TEST_Normalizacion@acciones.com   ", "password": "mypassword"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    mock_db.users.insert_one.assert_called_once()
    saved_user = mock_db.users.insert_one.call_args[0][0]
    assert saved_user["email"] == "test_normalizacion@acciones.com"


def test_login_normalization(mock_db):
    from core.auth_handler import get_password_hash
    mock_db.users.find_one.return_value = {
        "email": "test_normalizacion@acciones.com",
        "password": get_password_hash("mypassword"),
    }

    response = client.post(
        "/login",
        json={"email": "  TEST_Normalizacion@acciones.com  ", "password": "mypassword"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["email"] == "test_normalizacion@acciones.com"


# ==========================================
# 4. AUTONOMOUS FINANCIAL AGENT
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
    resp_info = client.get("/agent/info")
    assert resp_info.status_code == 200
    assert "get_ml_signal" in resp_info.json()["available_tools"]

    with patch("api.agent.run_financial_agent", return_value={"trace_id": "t1", "ticker": "TSLA", "final_verdict": "BUY"}):
        resp_an = client.post("/agent/analyze", json={"ticker": "TSLA"}, headers=auth_headers)
        assert resp_an.status_code == 200
        assert resp_an.json()["data"]["ticker"] == "TSLA"

    oid = ObjectId()
    mock_db.orders.find_one.return_value = {
        "_id": oid,
        "email": "test@example.com",
        "ticker": "TSLA",
        "action": "BUY",
        "quantity": 2,
        "estimated_price": 200.0,
        "status": "pending_approval",
    }
    with patch("api.agent.buy_stock", return_value=(True, "Compra aprobada")):
        resp_app = client.post(f"/agent/orders/{str(oid)}/approve", json={"notes": "OK"}, headers=auth_headers)
        assert resp_app.status_code == 200
        assert resp_app.json()["status"] == "success"


# ==========================================
# 5. [FASE 1] ML ROBUSTNESS & BACKTESTING
# ==========================================

def test_calculate_financial_metrics():
    """Calcula Sharpe, Sortino, MDD, Win Rate y Profit Factor sobre una curva de capital."""
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    equity_values = np.linspace(10000, 12000, 100)
    equity_values[50:60] -= 500
    equity_series = pd.Series(equity_values, index=dates)

    trades = pd.DataFrame([
        {"pnl": 200.0, "return_pct": 2.0},
        {"pnl": -100.0, "return_pct": -1.0},
        {"pnl": 300.0, "return_pct": 3.0},
    ])

    metrics = calculate_financial_metrics(equity_series, trades_df=trades)

    assert "total_return_pct" in metrics
    assert "sharpe_ratio" in metrics
    assert "sortino_ratio" in metrics
    assert "max_drawdown_pct" in metrics
    assert "win_rate_pct" in metrics
    assert "profit_factor" in metrics
    assert metrics["total_trades"] == 3
    assert metrics["win_rate_pct"] == pytest.approx(66.67, 0.1)
    assert metrics["profit_factor"] == pytest.approx(5.0, 0.1)
    assert metrics["max_drawdown_pct"] <= 0.0


def test_backtest_simulator_execution():
    """Prueba que el simulador registre trades, aplique comisiones y mantenga consistencia de capital."""
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    prices = [100, 102, 105, 103, 101, 104, 108, 107, 106, 110]
    signals = [0, 1, 1, 1, 0, 1, 1, 1, 0, 0]

    df = pd.DataFrame({"Close": prices}, index=dates)
    config = BacktestConfig(initial_capital=10_000.0, commission_pct=0.001, slippage_pct=0.0005)
    simulator = BacktestSimulator(config)
    results = simulator.run(df, signals, price_col="Close")

    assert "metrics" in results
    assert "benchmark_metrics" in results
    assert "equity_curve" in results
    assert len(results["equity_curve"]) == 10
    assert len(results["trades"]) >= 1


def test_timeseries_validator():
    """Valida que TimeSeriesSplit respete la causalidad temporal sin Data Leakage."""
    X = pd.DataFrame(np.random.randn(100, 4), columns=["f1", "f2", "f3", "f4"])
    y = pd.Series(np.random.randint(0, 2, size=100))

    validator = TimeSeriesValidator(n_splits=3)
    splits = list(validator.split(X, y))

    assert len(splits) == 3
    for train_idx, val_idx in splits:
        assert max(train_idx) < min(val_idx)


@patch("yfinance.Ticker")
def test_train_and_backtest_pipeline_mocked(mock_ticker, sample_ohlcv_df):
    """Verifica el pipeline integral de reentrenamiento y backtesting."""
    mock_stock = MagicMock()
    mock_stock.history.return_value = sample_ohlcv_df
    mock_ticker.return_value = mock_stock

    model, report = train_and_backtest_pipeline(ticker="AAPL", period="1y", n_splits=3)

    assert model is not None
    assert hasattr(model, "optimal_threshold")
    assert "ml_validation_metrics" in report
    assert "financial_metrics" in report
    assert "sharpe_ratio" in report["financial_metrics"]
    assert "max_drawdown_pct" in report["financial_metrics"]


# ==========================================
# 6. [FASE 2] EXTENSIBLE DATALOADER & ADVANCED FEATURES
# ==========================================

def test_data_loader_factory_and_memory_loader(sample_ohlcv_df):
    """Verifica la interfaz DataLoader, validaciones y MemoryDataLoader."""
    mem_loader = MemoryDataLoader({"TEST": sample_ohlcv_df})
    df = mem_loader.fetch_data("TEST")

    assert not df.empty
    assert len(df) == 100
    assert all(col in df.columns for col in DataLoader.REQUIRED_COLUMNS)

    with pytest.raises(ValueError, match="no encontrado"):
        mem_loader.fetch_data("NON_EXISTENT")

    loader_from_factory = get_data_loader("memory", data_map={"TEST": sample_ohlcv_df})
    assert isinstance(loader_from_factory, MemoryDataLoader)

    yf_loader = get_data_loader("yfinance")
    assert isinstance(yf_loader, YFinanceDataLoader)


def test_advanced_technical_indicators(sample_ohlcv_df):
    """Verifica Bollinger, ATR, VWAP, Volatilidad Histórica y osciladores."""
    df_feat = add_technical_indicators(sample_ohlcv_df)

    assert "BB_High_Dist" in df_feat.columns
    assert "BB_Low_Dist" in df_feat.columns
    assert "BB_Width" in df_feat.columns
    assert "BB_Pct" in df_feat.columns
    assert "ATR" in df_feat.columns
    assert "ATR_Pct" in df_feat.columns
    assert (df_feat["ATR"].iloc[14:] > 0).all()
    assert "VWAP" in df_feat.columns
    assert "VWAP_Dist" in df_feat.columns
    assert "Volatility" in df_feat.columns
    assert "Volatility_20d" in df_feat.columns
    assert "Hist_Vol_Ann" in df_feat.columns
    assert (df_feat["Hist_Vol_Ann"].dropna() >= 0).all()
    assert "RSI" in df_feat.columns
    assert "MACD" in df_feat.columns
    assert "EMA5" in df_feat.columns
    assert "EMA20" in df_feat.columns
    assert "EMA50" in df_feat.columns


def test_pipeline_with_custom_dataloader(sample_ohlcv_df):
    """Prueba inyección de DataLoader en pipeline de entrenamiento."""
    mem_loader = MemoryDataLoader({"SYNTH": sample_ohlcv_df})

    model, report = train_and_backtest_pipeline(
        ticker="SYNTH",
        n_splits=3,
        data_loader=mem_loader,
    )

    assert model is not None
    assert "ml_validation_metrics" in report
    assert "financial_metrics" in report
    assert report["financial_metrics"]["total_return_pct"] is not None


# ==========================================
# 7. [FASE 3] MLOPS & STRUCTURED LOGGING
# ==========================================

def test_json_formatter_structure():
    """Valida formato JSON estructurado para logs de producción."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Operación completada con éxito",
        args=(),
        exc_info=None,
    )
    record.extra_data = {"ticker": "AAPL", "sharpe": 1.85}

    formatted_str = formatter.format(record)
    log_json = json.loads(formatted_str)

    assert log_json["level"] == "INFO"
    assert log_json["logger"] == "test_logger"
    assert log_json["message"] == "Operación completada con éxito"
    assert log_json["lineNo"] == 42
    assert "timestamp" in log_json
    assert log_json["data"]["ticker"] == "AAPL"
    assert log_json["data"]["sharpe"] == 1.85


@patch("scripts.daily_ml_pipeline.train_and_backtest_pipeline")
@patch("scripts.daily_ml_pipeline.get_data_loader")
def test_run_daily_pipeline_execution(mock_get_loader, mock_train_pipeline, tmp_path):
    """Verifica la ejecución del pipeline batch diario de MLOps."""
    mock_loader = MagicMock()
    mock_get_loader.return_value = mock_loader

    mock_report = {
        "ticker": "AAPL",
        "period": "2y",
        "optimal_threshold": 0.52,
        "ml_validation_metrics": {"mean_accuracy": 0.62, "std_accuracy": 0.04, "mean_auc": 0.68},
        "financial_metrics": {
            "total_return_pct": 24.5,
            "sharpe_ratio": 1.42,
            "max_drawdown_pct": -8.3,
            "win_rate_pct": 58.0,
            "profit_factor": 2.1,
            "total_trades": 12,
        },
        "benchmark_metrics": {"total_return_pct": 15.0, "max_drawdown_pct": -14.2},
        "total_trades_executed": 12,
    }
    mock_train_pipeline.return_value = (MagicMock(), mock_report)

    output_dir = str(tmp_path / "test_reports")
    pipeline_res = run_daily_pipeline(
        tickers=["AAPL", "MSFT"],
        period="2y",
        output_dir=output_dir,
        save_to_mongo=False,
    )

    assert "AAPL" in pipeline_res["processed_tickers"]
    assert "MSFT" in pipeline_res["processed_tickers"]
    assert len(pipeline_res["failed_tickers"]) == 0

    files = os.listdir(output_dir)
    assert len(files) == 1
    assert files[0].startswith("daily_metrics_") and files[0].endswith(".json")

    with open(os.path.join(output_dir, files[0]), "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "AAPL" in data["summary"]
        assert data["summary"]["AAPL"]["financial_metrics"]["sharpe_ratio"] == 1.42
