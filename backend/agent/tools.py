"""Herramientas (Tools) nativas de Python para el Agente Financiero Autónomo.

Implementación de las 4 herramientas especificadas en la Documentación Técnica:
1. get_ml_signal(ticker: str) -> dict
2. get_market_news(ticker: str, limit: int = 5) -> list[dict]
3. get_portfolio_status(email: str = "default_user@acciones.com") -> dict
4. place_trade_order(ticker: str, action: str, percentage_capital: float, email: str = "default_user@acciones.com") -> dict
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import yfinance as yf
import pandas as pd
import numpy as np
from google import genai
from google.genai import types

from config.db import get_db
from config.settings import settings
from core.logger import logger
from ml.features import add_basic_features, make_supervised, FEATURE_COLUMNS
from agent.ml_loader import get_or_load_xgboost_model
from services.wallet import get_wallet
from services.stocks import get_stock_info


# ==============================================================================
# TOOL 1: get_ml_signal
# ==============================================================================

def extract_technical_features(ticker: str) -> Optional[pd.DataFrame]:
    """Obtiene datos de mercado recientes y extrae el vector de features técnicas."""
    stock = yf.Ticker(ticker)
    data = stock.history(period="1y")
    if data.empty or len(data) < 20:
        return None

    df = add_basic_features(data.copy())
    df = make_supervised(df, up_pct=0.01)
    df.dropna(inplace=True)
    if df.empty:
        return None

    last_row = df.iloc[-1]
    features_df = pd.DataFrame([last_row[FEATURE_COLUMNS]])
    return features_df


def get_ml_signal(ticker: str) -> dict:
    """Consulta el modelo XGBoost para obtener la señal cuantitativa del ticker.

    Calcula los últimos indicadores técnicos (RSI, MACD, Medias Móviles, etc.)
    y ejecuta inferencia con el modelo XGBoost precargado.

    Args:
        ticker: Símbolo bursátil del activo (ej. NVDA, AAPL, MSFT).

    Returns:
        dict: {'ticker': str, 'signal': 'BUY'|'SELL'|'HOLD', 'confidence': float}
    """
    ticker_clean = ticker.upper().strip()
    logger.info(f"⚡ [Tool get_ml_signal] Invocada para ticker: {ticker_clean}")

    # 1. Obtención del modelo con Lazy Loading
    model = get_or_load_xgboost_model(ticker_clean, model_type="local_xgb")
    if model is None:
        model = get_or_load_xgboost_model(ticker_clean, model_type="global_xgb")

    # 2. Extracción de features técnicas
    features = extract_technical_features(ticker_clean)
    if features is None or model is None:
        logger.warning(f"No se pudieron obtener features o modelo para {ticker_clean}. Retornando señal neutral.")
        return {
            "ticker": ticker_clean,
            "signal": "HOLD",
            "confidence": 0.5000,
            "status": "warning_insufficient_data"
        }

    # 3. Inferencia probabilística con XGBoost
    try:
        if hasattr(model, "predict_proba"):
            probability = float(model.predict_proba(features)[0][1])
        else:
            pred = model.predict(features)[0]
            probability = 0.70 if pred == 1 else 0.30
    except Exception as e:
        logger.error(f"Error durante predict_proba en get_ml_signal: {e}")
        probability = 0.50

    # 4. Mapeo de señal según especificación técnica
    # signal = "BUY" if probability > 0.65 else ("SELL" if probability < 0.35 else "HOLD")
    if probability > 0.65:
        signal = "BUY"
    elif probability < 0.35:
        signal = "SELL"
    else:
        signal = "HOLD"

    result = {
        "ticker": ticker_clean,
        "signal": signal,
        "confidence": round(float(probability), 4)
    }
    logger.info(f"📊 [Tool get_ml_signal] Resultado: {result}")
    return result


# ==============================================================================
# TOOL 2: get_market_news
# ==============================================================================

def _is_news_for_ticker(item: Dict[str, Any], content: Dict[str, Any], ticker: str) -> bool:
    """Acepta sólo noticias que Yahoo vincula al ticker o que lo nombran.

    Yahoo puede mezclar titulares sectoriales en ``Ticker.news``.  No se
    infiere la relación por palabras como "IA" o "semiconductores": si la
    fuente no declara el ticker, el titular debe mencionarlo explícitamente.
    """
    related_tickers = []
    for payload in (item, content):
        values = payload.get("relatedTickers") or payload.get("related_tickers") or []
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            related_tickers.extend(str(value).upper() for value in values)

    if ticker in related_tickers:
        return True

    title = str(content.get("title") or content.get("headline") or "")
    summary = str(
        content.get("summary") or content.get("description") or content.get("snippet") or ""
    )
    return ticker in f"{title} {summary}".upper()


def _translate_news_to_spanish(news: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Traduce título y resumen en una sola petición a Gemini.

    Si el servicio de traducción no está configurado o falla, se devuelve una
    lista vacía para no mostrar contenido en otro idioma como si estuviera
    traducido. La fuente, fecha y enlace se preservan sin cambios.
    """
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("No se muestran noticias: GEMINI_API_KEY no está configurada para traducirlas.")
        return []

    payload = [{"title": item["title"], "summary": item["summary"]} for item in news]
    prompt = (
        "Traduce al español neutro cada título y resumen financiero del JSON. "
        "No agregues ni elimines elementos, conserva tickers, cifras y nombres propios. "
        "Responde únicamente un JSON válido con la misma lista de objetos y las claves title y summary.\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )
        translated = json.loads(response.text)
        if not isinstance(translated, list) or len(translated) != len(news):
            raise ValueError("La traducción no conserva la cantidad de noticias")

        result = []
        for original, translated_item in zip(news, translated):
            title = translated_item.get("title") if isinstance(translated_item, dict) else None
            summary = translated_item.get("summary") if isinstance(translated_item, dict) else None
            if not isinstance(title, str) or not isinstance(summary, str):
                raise ValueError("La traducción no contiene título y resumen válidos")
            result.append({**original, "title": title, "summary": summary, "language": "es"})
        return result
    except Exception as exc:
        logger.error(f"No se pudieron traducir las noticias al español: {exc}")
        return []

def get_market_news(ticker: str, limit: int = 5) -> list:
    """Recupera los titulares y resúmenes de noticias recientes relacionadas al activo.

    Permite al agente evaluar el sentimiento del mercado y detectar riesgos no capturados.

    Args:
        ticker: Símbolo bursátil del activo (ej. NVDA, AAPL).
        limit: Número máximo de noticias a recuperar (por defecto 5).

    Returns:
        list: Lista de diccionarios con title, summary, source y time_published.
    """
    ticker_clean = ticker.upper().strip()
    try:
        limit = max(1, min(int(limit), 20))
    except (TypeError, ValueError):
        limit = 5
    logger.info(f"📰 [Tool get_market_news] Obteniendo noticias para {ticker_clean} (limit={limit})...")
    processed_news: List[Dict[str, Any]] = []

    try:
        stock = yf.Ticker(ticker_clean)
        raw_news = getattr(stock, "news", []) or []

        now = datetime.now(timezone.utc)

        for item in raw_news:
            if not isinstance(item, dict):
                continue
            # Yahoo finance puede estructurar noticias en 'content' o dict directo
            content = item.get("content") if isinstance(item.get("content"), dict) else item
            if not _is_news_for_ticker(item, content, ticker_clean):
                continue
            
            title = content.get("title") or content.get("headline") or "Sin título disponible"
            summary = content.get("summary") or content.get("description") or content.get("snippet") or title
            
            provider = content.get("provider")
            if isinstance(provider, dict):
                source = provider.get("displayName") or provider.get("name") or "Yahoo Finance"
            else:
                source = content.get("publisher") or content.get("source") or "Yahoo Finance"

            # Parseo de fecha
            pub_date = content.get("pubDate") or content.get("displayPublishTime")
            if pub_date:
                time_published = str(pub_date)
            else:
                time_sec = content.get("providerPublishTime") or content.get("datetime")
                if time_sec:
                    try:
                        time_published = datetime.fromtimestamp(int(time_sec), timezone.utc).isoformat()
                    except Exception:
                        time_published = str(time_sec)
                else:
                    time_published = now.isoformat()

            link_data = content.get("canonicalUrl") or content.get("clickThroughUrl") or content.get("link")
            if isinstance(link_data, dict):
                link = link_data.get("url")
            else:
                link = link_data

            processed_news.append({
                "title": title,
                "summary": summary,
                "source": source,
                "time_published": time_published,
                "url": link,
            })
            if len(processed_news) == limit:
                break

    except Exception as e:
        logger.error(f"Error al obtener noticias para {ticker_clean}: {e}")

    # No inventar noticias: una fuente inaccesible no equivale a un mercado sin eventos.
    # El agente puede expresar explícitamente que no dispuso de contexto noticioso.
    if not processed_news:
        logger.warning(f"No se encontraron noticias verificables para {ticker_clean}.")

    translated_news = _translate_news_to_spanish(processed_news)
    logger.info(f"🗞️ [Tool get_market_news] {len(translated_news)} noticias de {ticker_clean} recuperadas y traducidas.")
    return translated_news


# ==============================================================================
# TOOL 3: get_portfolio_status
# ==============================================================================

def get_portfolio_status(email: str = "default_user@acciones.com") -> dict:
    """Recupera el balance actual de la cuenta, efectivo disponible y posiciones abiertas.

    Proporciona al agente visibilidad en tiempo real sobre la cartera del usuario
    para prevenir sobreexposición al riesgo.

    Args:
        email: Identificador del usuario o cuenta.

    Returns:
        dict: {'cash_balance': float, 'total_portfolio_value': float, 'positions': list}
    """
    logger.info(f"💼 [Tool get_portfolio_status] Consultando estado de cartera para {email}...")
    try:
        wallet = get_wallet(email)
    except Exception as e:
        logger.warning(f"No se pudo conectar a la base de datos para billetera: {e}. Usando mock seguro.")
        wallet = {
            "balance": 10000.0,
            "sub_wallets": {"spot": {"balance": 10000.0, "portfolio": {}}},
            "portfolio": {}
        }

    sub_spot = wallet.get("sub_wallets", {}).get("spot", {})
    cash_balance = float(sub_spot.get("balance", wallet.get("balance", 10000.0)))
    raw_positions = sub_spot.get("portfolio", wallet.get("portfolio", {}))

    positions_list: List[Dict[str, Any]] = []
    total_positions_value = 0.0

    for ticker, data in raw_positions.items():
        qty = int(data.get("quantity", 0))
        if qty <= 0:
            continue
        avg_price = float(data.get("average_price", 0.0))
        
        # Precio actual estimado
        current_price = avg_price
        try:
            info = get_stock_info(ticker)
            if info and info.get("price"):
                current_price = float(info["price"])
        except Exception:
            pass

        market_value = round(qty * current_price, 2)
        total_positions_value += market_value
        pnl = round(market_value - (qty * avg_price), 2)
        pnl_pct = round((pnl / (qty * avg_price) * 100.0) if avg_price > 0 else 0.0, 2)

        positions_list.append({
            "ticker": ticker.upper(),
            "quantity": qty,
            "average_price": avg_price,
            "current_price": current_price,
            "market_value": market_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct
        })

    total_portfolio_value = round(cash_balance + total_positions_value, 2)

    result = {
        "cash_balance": round(cash_balance, 2),
        "total_portfolio_value": total_portfolio_value,
        "positions": positions_list
    }
    logger.info(f"📊 [Tool get_portfolio_status] Balance: ${cash_balance}, Total: ${total_portfolio_value}, Posiciones: {len(positions_list)}")
    return result


# ==============================================================================
# TOOL 4: place_trade_order
# ==============================================================================

def place_trade_order(
    ticker: str,
    action: str,
    percentage_capital: float,
    email: str = "default_user@acciones.com"
) -> dict:
    """Simula o ejecuta la orden financiera ajustada a las reglas de riesgo aprobadas.

    Aplica Human-In-The-Loop registrando la orden en estado de borrador/pendiente
    para validación o ejecución.

    Args:
        ticker: Símbolo del activo (ej. NVDA, AAPL).
        action: Acción a ejecutar ('BUY' o 'SELL').
        percentage_capital: Porcentaje del portafolio a asignar (ej. 0.05 para 5%, max 0.10 para 10%).
        email: Correo del usuario solicitante.

    Returns:
        dict: Confirmación con ID de transacción, detalles y estado.
    """
    ticker_clean = ticker.upper().strip()
    action_clean = action.upper().strip()
    logger.info(f"🎯 [Tool place_trade_order] Solicitud de orden: {action_clean} {ticker_clean} con {percentage_capital*100:.1f}% de capital")

    # 1. Validar acción
    if action_clean not in ("BUY", "SELL"):
        return {
            "status": "rejected",
            "error": f"Acción '{action}' no válida. Debe ser 'BUY' o 'SELL'."
        }

    # 2. Control dinámico de riesgo (Regla: Máximo 10% del total de la cartera por operación)
    if percentage_capital <= 0:
        return {
            "status": "rejected",
            "error": "El porcentaje de capital debe ser mayor a 0."
        }
    if percentage_capital > 0.1001:  # Margen de precisión de punto flotante
        return {
            "status": "rejected",
            "error": f"Límite de riesgo excedido: La orden solicita {percentage_capital*100:.1f}%, superando el máximo permitido del 10% del portafolio."
        }

    # 3. Consultar estado del portafolio
    portfolio_status = get_portfolio_status(email)
    total_val = portfolio_status["total_portfolio_value"]
    cash = portfolio_status["cash_balance"]

    target_amount = total_val * percentage_capital

    # 4. Obtener precio actual de mercado
    current_price = 100.0  # Fallback seguro
    try:
        info = get_stock_info(ticker_clean)
        if info and info.get("price"):
            current_price = float(info["price"])
    except Exception as e:
        logger.warning(f"No se pudo consultar precio en vivo para {ticker_clean}: {e}")

    # 5. Calcular cantidad de acciones
    quantity = int(target_amount // current_price)
    if quantity < 1:
        quantity = 1  # Mínimo 1 acción en simulaciones si el capital lo permite

    total_order_cost = round(quantity * current_price, 2)

    # 6. Validación de balance en compras
    if action_clean == "BUY" and total_order_cost > cash:
        return {
            "status": "rejected",
            "error": f"Saldo en efectivo insuficiente (${cash}) para comprar {quantity} acciones (${total_order_cost})."
        }

    # 7. Registrar orden en MongoDB con soporte Human-In-The-Loop
    order_doc = {
        "email": email,
        "ticker": ticker_clean,
        "action": action_clean,
        "quantity": quantity,
        "estimated_price": current_price,
        "total_amount": total_order_cost,
        "percentage_capital": percentage_capital,
        "status": "pending_approval",  # Human-In-The-Loop
        "mode": "paper_trading",
        "created_at": datetime.now(timezone.utc),
        "source": "AI_Agent"
    }

    try:
        db = get_db()
        res = db.orders.insert_one(order_doc)
        transaction_id = str(res.inserted_id)
    except Exception as e:
        logger.warning(f"No se pudo persistir orden en Mongo: {e}. Generando ID simulado.")
        import uuid
        transaction_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"

    confirmation = {
        "transaction_id": transaction_id,
        "ticker": ticker_clean,
        "action": action_clean,
        "quantity": quantity,
        "price_per_share": current_price,
        "total_estimated": total_order_cost,
        "percentage_assigned": round(percentage_capital * 100.0, 2),
        "status": "pending_approval",
        "message": f"Orden de {action_clean} para {quantity} acciones de {ticker_clean} creada con éxito (Pendiente de aprobación en la UI)."
    }
    logger.info(f"✅ [Tool place_trade_order] Orden registrada: {confirmation}")
    return confirmation


AVAILABLE_TOOLS = {
    "get_ml_signal": get_ml_signal,
    "get_market_news": get_market_news,
    "get_portfolio_status": get_portfolio_status,
    "place_trade_order": place_trade_order
}
