"""Cálculo de Indicadores Técnicos Avanzados con 'ta' y optimizaciones vectorizadas."""

import numpy as np
import pandas as pd
import ta


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega indicadores técnicos robustos: Bollinger, ATR, VWAP, Volatilidad Histórica, RSI, MACD, etc.
    
    Args:
        df: DataFrame OHLCV limpio y ordenado por fecha.

    Returns:
        DataFrame enriquecido con variables técnicas normalizadas y estacionarias.
    """
    df = df.copy()

    # 1. Retornos y Momento
    df["Return"] = df["Close"].pct_change()
    df["Log_Return"] = np.log(df["Close"] / df["Close"].shift(1))
    df["ROC"] = ta.momentum.roc(df["Close"], window=10)

    # 2. Volatilidad Histórica
    # Volatilidad móvil de corto y mediano plazo (desviación de retornos)
    df["Volatility"] = df["Return"].rolling(window=5).std()
    df["Volatility_20d"] = df["Return"].rolling(window=20).std()
    # Volatilidad histórica anualizada (252 días de trading)
    df["Hist_Vol_Ann"] = df["Return"].rolling(window=20).std() * np.sqrt(252)

    # 3. Bandas de Bollinger (20 periodos, 2 desviaciones)
    bb_indicator = ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2)
    bb_upper = bb_indicator.bollinger_hband()
    bb_lower = bb_indicator.bollinger_lband()
    bb_mid = bb_indicator.bollinger_mavg()

    df["BB_High_Dist"] = (bb_upper - df["Close"]) / (df["Close"] + 1e-9)
    df["BB_Low_Dist"] = (df["Close"] - bb_lower) / (df["Close"] + 1e-9)
    df["BB_Width"] = (bb_upper - bb_lower) / (bb_mid + 1e-9)
    df["BB_Pct"] = bb_indicator.bollinger_pband()

    # 4. Average True Range (ATR - 14 periodos) y ATR Normalizado
    atr_series = ta.volatility.average_true_range(high=df["High"], low=df["Low"], close=df["Close"], window=14)
    df["ATR"] = atr_series
    df["ATR_Pct"] = atr_series / (df["Close"] + 1e-9)

    # 5. Volume Weighted Average Price (VWAP) y Distancia Relativa
    # Para datos diarios agrupamos o calculamos VWAP rolling/acumulado
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    vol_cum = df["Volume"].rolling(window=20).sum() + 1e-9
    pv_cum = (typical_price * df["Volume"]).rolling(window=20).sum()
    df["VWAP"] = pv_cum / vol_cum
    df["VWAP_Dist"] = (df["Close"] - df["VWAP"]) / (df["VWAP"] + 1e-9)

    # 6. Osciladores de Momentum: RSI y Estocástico
    df["RSI"] = ta.momentum.rsi(close=df["Close"], window=14)
    
    stoch = ta.momentum.StochasticOscillator(high=df["High"], low=df["Low"], close=df["Close"], window=14, smooth_window=3)
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()

    # 7. Tendencia: MACD y Medias Móviles Exponenciales (EMA)
    macd = ta.trend.MACD(close=df["Close"], window_slow=26, window_fast=12, window_sign=9)
    df["MACD"] = macd.macd()
    df["MACD_Hist"] = macd.macd_diff()

    df["EMA5"] = ta.trend.ema_indicator(close=df["Close"], window=5)
    df["EMA20"] = ta.trend.ema_indicator(close=df["Close"], window=20)
    df["EMA50"] = ta.trend.ema_indicator(close=df["Close"], window=50)

    # Distancia relativa de EMAs al precio de cierre
    df["EMA5_Dist"] = (df["Close"] - df["EMA5"]) / (df["EMA5"] + 1e-9)
    df["EMA20_Dist"] = (df["Close"] - df["EMA20"]) / (df["EMA20"] + 1e-9)

    return df
