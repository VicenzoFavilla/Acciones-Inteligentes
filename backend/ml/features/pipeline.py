"""Pipeline de Features y Generación de Dataset Supervisado."""

from typing import Tuple, List
import pandas as pd

from ml.features.technical import add_technical_indicators

FEATURE_COLUMNS: List[str] = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Return",
    "Volatility",
    "Volatility_20d",
    "Hist_Vol_Ann",
    "RSI",
    "MACD",
    "MACD_Hist",
    "BB_High_Dist",
    "BB_Low_Dist",
    "BB_Width",
    "BB_Pct",
    "ROC",
    "ATR_Pct",
    "VWAP_Dist",
    "Stoch_K",
    "Stoch_D",
    "EMA5",
    "EMA20",
    "EMA50",
    "EMA5_Dist",
    "EMA20_Dist",
]

# Conjunto base tradicional para retrocompatibilidad estricta si se requiere
LEGACY_FEATURE_COLUMNS: List[str] = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Return",
    "Volatility",
    "RSI",
    "MACD",
    "MACD_Hist",
    "BB_High_Dist",
    "BB_Low_Dist",
    "BB_Width",
    "ROC",
    "ATR_Pct",
    "Stoch_K",
    "Stoch_D",
    "EMA5",
    "EMA20",
]


def add_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    """Función de compatibilidad que calcula la totalidad de los indicadores técnicos."""
    return add_technical_indicators(df)


def make_supervised(df: pd.DataFrame, up_pct: float = 0.01) -> pd.DataFrame:
    """Crea la columna objetivo: sube más de up_pct en el siguiente periodo (1) o no (0)."""
    df = df.copy()
    df["Target"] = (df["Close"].shift(-1) > df["Close"] * (1.0 + up_pct)).astype(int)
    df = df.dropna()
    return df


def get_X_y(df: pd.DataFrame, columns: List[str] | None = None) -> Tuple[pd.DataFrame, pd.Series]:
    """Separa variables independientes X y variable dependiente y."""
    cols = columns or [c for c in FEATURE_COLUMNS if c in df.columns]
    X = df[cols]
    y = df["Target"]
    return X, y
