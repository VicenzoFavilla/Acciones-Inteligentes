"""Funciones utilitarias para ingeniería de variables y dataset supervisado."""

import pandas as pd


FEATURE_COLUMNS = [
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
    """Agrega indicadores técnicos avanzados e indispensables a un OHLCV DataFrame."""
    df = df.copy()
    
    # Retorno diario y volatilidad de corto plazo (5 periodos)
    df["Return"] = df["Close"].pct_change()
    df["Volatility"] = df["Close"].rolling(5).std()
    
    # EMAs (Medias Móviles Exponenciales)
    df["EMA5"] = df["Close"].ewm(span=5, adjust=False).mean()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    
    # RSI (Relative Strength Index - 14 periodos)
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0.0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100.0 - (100.0 / (1.0 + rs))
    
    # MACD (12, 26, 9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    macd_signal = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - macd_signal
    
    # Bandas de Bollinger (20 periodos, 2 stddevs)
    bb_mid = df["Close"].rolling(window=20).mean()
    bb_std = df["Close"].rolling(window=20).std()
    bb_upper = bb_mid + 2.0 * bb_std
    bb_lower = bb_mid - 2.0 * bb_std
    
    df["BB_High_Dist"] = (bb_upper - df["Close"]) / (df["Close"] + 1e-9)
    df["BB_Low_Dist"] = (df["Close"] - bb_lower) / (df["Close"] + 1e-9)
    df["BB_Width"] = (bb_upper - bb_lower) / (bb_mid + 1e-9)
    
    # ROC (Rate of Change / Momentum - 10 periodos)
    df["ROC"] = df["Close"].pct_change(periods=10)
    
    # ATR Normalizado (Average True Range - 14 periodos en relación al precio)
    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - df["Close"].shift()).abs()
    tr3 = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/14, adjust=False).mean()
    df["ATR_Pct"] = atr / (df["Close"] + 1e-9)
    
    # Estocástico (Stochastic Oscillator - 14 periodos)
    low_14 = df["Low"].rolling(14).min()
    high_14 = df["High"].rolling(14).max()
    df["Stoch_K"] = 100.0 * (df["Close"] - low_14) / (high_14 - low_14 + 1e-9)
    df["Stoch_D"] = df["Stoch_K"].rolling(3).mean()
    
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
