"""Tests unitarios para la Fase 1: TimeSeriesSplit, Backtesting Engine y Métricas Financieras."""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from ml.backtesting.metrics import calculate_financial_metrics
from ml.backtesting.engine import BacktestSimulator, BacktestConfig
from ml.validation.walk_forward import TimeSeriesValidator
from ml.trainer import train_and_backtest_pipeline


def test_calculate_financial_metrics():
    """Verifica que las métricas de Sharpe, Sortino, Drawdown y Win Rate se calculen adecuadamente."""
    # Simular una equity curve creciente con una corrección
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    equity_values = np.linspace(10000, 12000, 100)
    # Introducir un drawdown temporal
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
    """Valida que el simulador registre compras, ventas y aplique comisiones."""
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    prices = [100, 102, 105, 103, 101, 104, 108, 107, 106, 110]
    # Señales: Comprar en 1, mantener hasta vender en 4, volver a comprar en 5
    signals = [0, 1, 1, 1, 0, 1, 1, 1, 0, 0]

    df = pd.DataFrame({"Close": prices}, index=dates)
    config = BacktestConfig(
        initial_capital=10_000.0,
        commission_pct=0.001,
        slippage_pct=0.0005,
    )
    simulator = BacktestSimulator(config)
    results = simulator.run(df, signals, price_col="Close")

    assert "metrics" in results
    assert "benchmark_metrics" in results
    assert "equity_curve" in results
    assert len(results["equity_curve"]) == 10
    assert len(results["trades"]) >= 1


def test_timeseries_validator():
    """Prueba que TimeSeriesValidator no genere data leakage y respete el orden temporal."""
    X = pd.DataFrame(np.random.randn(100, 4), columns=["f1", "f2", "f3", "f4"])
    y = pd.Series(np.random.randint(0, 2, size=100))

    validator = TimeSeriesValidator(n_splits=3)
    splits = list(validator.split(X, y))

    assert len(splits) == 3
    for train_idx, val_idx in splits:
        # El índice máximo de train debe ser menor al índice mínimo de validación
        assert max(train_idx) < min(val_idx)


@patch("yfinance.Ticker")
def test_train_and_backtest_pipeline_mocked(mock_ticker):
    """Verifica la ejecución de punta a punta del pipeline de entrenamiento y backtest."""
    dates = pd.date_range("2023-01-01", periods=150, freq="B")
    data = {
        "Open": np.linspace(100, 150, 150) + np.random.randn(150),
        "High": np.linspace(102, 152, 150) + np.random.randn(150),
        "Low": np.linspace(98, 148, 150) + np.random.randn(150),
        "Close": np.linspace(100, 150, 150) + np.random.randn(150),
        "Volume": np.random.randint(10000, 50000, size=150),
    }
    mock_df = pd.DataFrame(data, index=dates)
    
    mock_stock = MagicMock()
    mock_stock.history.return_value = mock_df
    mock_ticker.return_value = mock_stock

    model, report = train_and_backtest_pipeline(ticker="AAPL", period="1y", n_splits=3)

    assert model is not None
    assert hasattr(model, "optimal_threshold")
    assert "ml_validation_metrics" in report
    assert "financial_metrics" in report
    assert "sharpe_ratio" in report["financial_metrics"]
    assert "max_drawdown_pct" in report["financial_metrics"]
