"""Tests unitarios para la Fase 2: DataLoader Extensible y Feature Engineering Avanzado."""

import pytest
import numpy as np
import pandas as pd

from ml.data import DataLoader, MemoryDataLoader, YFinanceDataLoader, get_data_loader
from ml.features import add_technical_indicators, add_basic_features, make_supervised, get_X_y, FEATURE_COLUMNS
from ml.trainer import train_and_backtest_pipeline


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


def test_data_loader_factory_and_memory_loader(sample_ohlcv_df):
    """Verifica que el factory y MemoryDataLoader funcionen con validación de columnas."""
    mem_loader = MemoryDataLoader({"TEST": sample_ohlcv_df})
    df = mem_loader.fetch_data("TEST")

    assert not df.empty
    assert len(df) == 100
    assert all(col in df.columns for col in DataLoader.REQUIRED_COLUMNS)

    # Test error en ticker inexistente
    with pytest.raises(ValueError, match="no encontrado"):
        mem_loader.fetch_data("NON_EXISTENT")

    # Test factory
    loader_from_factory = get_data_loader("memory", data_map={"TEST": sample_ohlcv_df})
    assert isinstance(loader_from_factory, MemoryDataLoader)

    yf_loader = get_data_loader("yfinance")
    assert isinstance(yf_loader, YFinanceDataLoader)


def test_advanced_technical_indicators(sample_ohlcv_df):
    """Verifica el cálculo de Bollinger, ATR, VWAP, Volatilidad Histórica y osciladores."""
    df_feat = add_technical_indicators(sample_ohlcv_df)

    # Bollinger Bands
    assert "BB_High_Dist" in df_feat.columns
    assert "BB_Low_Dist" in df_feat.columns
    assert "BB_Width" in df_feat.columns
    assert "BB_Pct" in df_feat.columns

    # ATR
    assert "ATR" in df_feat.columns
    assert "ATR_Pct" in df_feat.columns
    assert (df_feat["ATR"].iloc[14:] > 0).all()

    # VWAP
    assert "VWAP" in df_feat.columns
    assert "VWAP_Dist" in df_feat.columns

    # Volatilidad Histórica
    assert "Volatility" in df_feat.columns
    assert "Volatility_20d" in df_feat.columns
    assert "Hist_Vol_Ann" in df_feat.columns
    assert (df_feat["Hist_Vol_Ann"].dropna() >= 0).all()

    # Momentum y Tendencia
    assert "RSI" in df_feat.columns
    assert "MACD" in df_feat.columns
    assert "EMA5" in df_feat.columns
    assert "EMA20" in df_feat.columns
    assert "EMA50" in df_feat.columns


def test_pipeline_with_custom_dataloader(sample_ohlcv_df):
    """Prueba que train_and_backtest_pipeline funcione con inyección de dependencias de DataLoader."""
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
