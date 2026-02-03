"""Servicios de datos bursátiles vía yfinance.

Este módulo evita acoplar la UI: sólo retorna datos y persiste en DB.
"""

import yfinance as yf
from datetime import datetime
from config.db import get_db


def get_stock_info(ticker: str):
    """Obtiene nombre, precio actual, variación diaria y volumen de un ticker.

    Intenta primero `fast_info` (rápido) y hace respaldo con `history()`.
    También persiste un snapshot en MongoDB (colección `history`).
    """
    stock = yf.Ticker(ticker)

    name = ticker.upper()
    current_price = None
    previous_close = None
    volume = None

    # Intento rápido con fast_info
    try:
        fi = stock.fast_info
        if isinstance(fi, dict):
            current_price = fi.get("last_price") or fi.get("regular_market_price")
            previous_close = fi.get("regular_market_previous_close") or fi.get("previous_close")
            volume = fi.get("last_volume") or fi.get("regular_market_volume") or fi.get("volume")
    except Exception:
        pass

    # Respaldo con history()
    if current_price is None or previous_close is None or volume is None:
        try:
            hist = stock.history(period="5d", interval="1d")
            if not hist.empty:
                last_row = hist.iloc[-1]
                if current_price is None:
                    current_price = float(last_row["Close"])
                if volume is None and "Volume" in last_row:
                    volume = int(last_row["Volume"])
                if previous_close is None:
                    if len(hist) >= 2:
                        previous_close = float(hist["Close"].iloc[-2])
                    else:
                        previous_close = float(last_row["Close"])  # mejor que nada
        except Exception:
            pass

    # Nombre (opcional)
    try:
        info = stock.get_info()
        if isinstance(info, dict):
            name = info.get("shortName", name)
    except Exception:
        pass

    if current_price is None or previous_close is None:
        return None

    change = round((current_price - previous_close) / previous_close * 100, 2) if previous_close else None

    # Persistencia en MongoDB (sin prints/UI)
    try:
        db = get_db()
        db.history.insert_one({
            "ticker": ticker,
            "name": name,
            "price": current_price,
            "change": change,
            "volume": volume,
            "timestamp": datetime.now()
        })
    except Exception:
        # Si DB no está disponible, no romper el flujo de la CLI
        pass

    return {
        "ticker": ticker,
        "name": name,
        "price": current_price,
        "change": change,
        "volume": volume,
    }


def get_price_history(ticker: str, period: str = "30d"):
    """Devuelve la serie de cierres diarios para graficar desde la CLI."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period, interval="1d")
    if hist is None or hist.empty:
        return None
    return hist["Close"]
