from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import pandas as pd
from services.stocks import get_stock_info, get_price_history, get_sp500_tickers
from ml.recomendacion import smart_recommendation, basic_recommendation
from ml.global_models import tickers_from_usage
from agent.tools import get_ml_signal
from config.db import get_db
from core.logger import logger
from api.auth import get_current_user
from concurrent.futures import ThreadPoolExecutor
from .websocket import market_prices

router = APIRouter()

@router.post("/user/watchlist/{ticker}")
def add_to_watchlist(ticker: str, current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    ticker_up = ticker.upper()
    db_conn.users.update_one(
        {"email": current_user["email"]},
        {"$addToSet": {"watchlist": ticker_up}}
    )
    return {"status": "success", "message": f"{ticker_up} agregado a favoritos"}

@router.delete("/user/watchlist/{ticker}")
def remove_from_watchlist(ticker: str, current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    ticker_up = ticker.upper()
    db_conn.users.update_one(
        {"email": current_user["email"]},
        {"$pull": {"watchlist": ticker_up}}
    )
    return {"status": "success", "message": f"{ticker_up} eliminado de favoritos"}

@router.get("/user/watchlist")
def get_watchlist(current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    user = db_conn.users.find_one({"email": current_user["email"]})
    watchlist = user.get("watchlist", [])
    lista_watchlist = []
    for ticker in watchlist:
        info = get_stock_info(ticker)
        if info:
            history_data = get_price_history(ticker, period="7d")
            history_list = []
            if history_data is not None and not history_data.empty:
                if hasattr(history_data, "columns"):
                    if isinstance(history_data.columns, pd.MultiIndex):
                        history_data.columns = history_data.columns.get_level_values(0)
                    if "Close" in history_data.columns:
                        history_list = history_data["Close"].tolist()
                else:
                    history_list = history_data.tolist()
            history_list = [x for x in history_list if str(x) != 'nan']
            lista_watchlist.append({
                "ticker": ticker,
                "nombre": info.get("name", ticker),
                "precio": info.get("price"),
                "variacion": info.get("change"),
                "color_green": (info.get("change") or 0) >= 0,
                "history": history_list
            })
    return {"status": "success", "watchlist": lista_watchlist}

@router.get("/predict/{ticker}")
def predict_stock(ticker: str, period: str = "1mo"):
    ticker_up = ticker.upper()
    try:
        if period == "1d":
            interval = "15m"
        elif period == "5d":
            interval = "60m"
        elif period == "15d":
            interval = "60m"
        else:
            interval = "1d"
        
        info = get_stock_info(ticker_up)
        try:
            ml_res = smart_recommendation(ticker_up, registrar=True, model_type="global_xgb")
        except Exception as e:
            logger.error(f"IA Error en predicción para {ticker_up}: {e}")
            ml_res = None

        # Un modelo global puede no estar instalado todavía. En vez de exponer
        # el error técnico como recomendación, se entrega una regla de mercado
        # simple hasta que el modelo esté disponible.
        if not ml_res or ml_res.startswith((
            "No hay modelo global",
            "No hay suficientes datos",
            "No se pudo entrenar",
            "Error al predecir",
        )):
            logger.warning(f"Usando recomendación básica para {ticker_up}: modelo ML no disponible.")
            ml_res = basic_recommendation(info.get("change") if info else None)

        history_df = get_price_history(ticker_up, period=period, interval=interval, full=True)
        ohlc_list = []
        history_list = []
        if history_df is not None and not history_df.empty:
            if hasattr(history_df.columns, "levels"):
                history_df.columns = history_df.columns.get_level_values(0)
            history_df.columns = [str(c).lower() for c in history_df.columns]
            for index, row in history_df.iterrows():
                try:
                    o, h, l, c, v = float(row.get("open", 0)), float(row.get("high", 0)), float(row.get("low", 0)), float(row.get("close", 0)), float(row.get("volume", 0))
                    if str(o) == 'nan' or str(c) == 'nan': continue
                    ohlc_list.append({"open": o, "high": h, "low": l, "close": c, "volume": v, "date": index.isoformat() if hasattr(index, "isoformat") else str(index)})
                    history_list.append(c)
                except: pass

        precio = info.get("price") if info else 0.0
        return {"ticker": ticker_up, "precio": precio, "recomendacion": ml_res, "history": history_list, "ohlc": ohlc_list}
    except Exception as e:
        logger.error(f"Error general en predict_stock para {ticker}: {e}")
        return {"ticker": ticker_up, "precio": 0.0, "recomendacion": "Servidor en mantenimiento", "history": []}

@router.get("/popular")
def get_popular_stocks():
    top_tickers = tickers_from_usage(limit=5)
    default_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]
    seen = set()
    combined = []
    for t in top_tickers + default_list:
        if t not in seen:
            combined.append(t)
            seen.add(t)
        if len(combined) >= 5: break
    
    lista_populares = []
    for ticker in combined:
        info = get_stock_info(ticker)
        if info:
            history_data = get_price_history(ticker, period="7d")
            history_list = []
            if history_data is not None and not history_data.empty:
                if hasattr(history_data, "columns"):
                    if isinstance(history_data.columns, pd.MultiIndex):
                        history_data.columns = history_data.columns.get_level_values(0)
                    if "Close" in history_data.columns:
                        history_list = history_data["Close"].tolist()
                else:
                    history_list = history_data.tolist()
            history_list = [x for x in history_list if str(x) != 'nan']
            lista_populares.append({
                "ticker": ticker,
                "nombre": info.get("name", ticker),
                "precio": info.get("price"),
                "variacion": info.get("change"),
                "color_green": (info.get("change") or 0) >= 0,
                "history": history_list
            })
    return lista_populares


@router.get("/opportunities")
def get_market_opportunities(limit: int = Query(3, ge=1, le=5)):
    """Devuelve señales ML breves para una pequeña selección de acciones líquidas.

    Es una lista de exploración; no envía órdenes ni constituye una recomendación
    personalizada. Limitarla evita cargar modelos y datos para todo el mercado.
    """
    candidates = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN"][:limit]

    def build_opportunity(ticker: str):
        info = get_stock_info(ticker) or {}
        signal = get_ml_signal(ticker)
        history_data = get_price_history(ticker, period="7d")
        history = []
        if history_data is not None:
            try:
                history = [float(value) for value in history_data.tolist() if pd.notna(value)]
            except (AttributeError, TypeError, ValueError):
                history = []
        confidence = float(signal.get("confidence", 0.5))
        action = signal.get("signal", "HOLD")
        change = float(info.get("change") or 0.0)
        reason = (
            f"Señal {action} del modelo con {confidence * 100:.0f}% de confianza; "
            f"variación diaria {change:+.2f}%."
        )
        return {
            "ticker": ticker,
            "name": info.get("name", ticker),
            "price": info.get("price", 0.0),
            "change": change,
            "signal": action,
            "confidence": confidence,
            "reason": reason,
            "history": history,
        }

    with ThreadPoolExecutor(max_workers=limit) as executor:
        opportunities = list(executor.map(build_opportunity, candidates))
    return {
        "items": opportunities,
        "disclaimer": "Señales informativas; verificá el análisis antes de operar.",
    }

@router.get("/market")
def get_market_list(search: Optional[str] = None, page: int = 1, page_size: int = 50):
    all_tickers = get_sp500_tickers()
    if search:
        search = search.upper()
        filtered_tickers = [t for t in all_tickers if search in t]
    else:
        filtered_tickers = all_tickers
    total_items = len(filtered_tickers)
    total_pages = (total_items + page_size - 1) // page_size
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    start_idx = (page - 1) * page_size
    target_tickers = filtered_tickers[start_idx:start_idx + page_size]
    
    def fetch_ticker_data(ticker):
        if ticker in market_prices:
            cached = market_prices[ticker]
            return {"ticker": ticker, "nombre": cached.get("name", ticker), "precio": cached.get("price"), "variacion": cached.get("change"), "color_green": (cached.get("change") or 0) >= 0, "volumen": cached.get("volume"), "market_cap": 0}
        info = get_stock_info(ticker)
        if info:
            return {"ticker": ticker, "nombre": info.get("name", ticker), "precio": info.get("price"), "variacion": info.get("change"), "color_green": (info.get("change") or 0) >= 0, "volumen": info.get("volume"), "market_cap": 0}
        return {"ticker": ticker, "nombre": ticker, "precio": 0.0, "variacion": 0.0, "color_green": True, "volumen": 0, "market_cap": 0}

    with ThreadPoolExecutor(max_workers=20) as executor:
        lista_market = list(executor.map(fetch_ticker_data, target_tickers))
    return {"items": lista_market, "total_items": total_items, "total_pages": total_pages, "current_page": page, "page_size": page_size}

class DecisionRequest(BaseModel):
    ticker: str
    decision: str

@router.post("/decision")
def save_decision(req: DecisionRequest):
    db = get_db()
    result = db.acciones_usuario.update_one(
        {"ticker": req.ticker, "decision_usuario": None},
        {"$set": {"decision_usuario": req.decision}}
    )
    if result.modified_count == 0:
        return {"status": "info", "message": "No se encontró predicción pendiente o ya fue actualizada."}
    return {"status": "success", "message": "Decisión registrada correctamente."}

@router.get("/feedback")
def save_user_decision(ticker: str, decision: str):
    db = get_db()
    db.acciones_usuario.update_one(
        {"ticker": ticker, "decision_usuario": None},
        {"$set": {"decision_usuario": decision}},
        sort=[("fecha", -1)]
    )
    return {"status": "success", "message": "Decisión guardada correctamente"}
