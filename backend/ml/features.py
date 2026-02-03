"""Funciones utilitarias para ingeniería de variables y dataset supervisado."""

import pandas as pd


FEATURE_COLUMNS = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Return",
    "MA5",
    "MA10",
    "Volatility",
]


def add_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega retornos, medias móviles y volatilidad a un OHLCV DataFrame."""
    df = df.copy()
    df["Return"] = df["Close"].pct_change()
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA10"] = df["Close"].rolling(10).mean()
    df["Volatility"] = df["Close"].rolling(5).std()
    return df


def make_supervised(df: pd.DataFrame, up_pct: float = 0.01) -> pd.DataFrame:
    """Crea la columna objetivo: sube más de up_pct al día siguiente (binario)."""
    df = df.copy()
    df["Target"] = (df["Close"].shift(-1) > df["Close"] * (1.0 + up_pct)).astype(int)
    df = df.dropna()
    return df


def get_X_y(df: pd.DataFrame):
    """Separa features y etiqueta usando FEATURE_COLUMNS y 'Target'."""
    X = df[FEATURE_COLUMNS]
    y = df["Target"]
    return X, y
