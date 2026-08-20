"""Orquestador y Grafo de Decisión del Agente Financiero Autónomo.

Implementa el bucle de control agéntico con Google GenAI SDK (Gemini 2.5 Flash),
despacho de herramientas (Function Calling), registro de trazas (Auditoría)
y cumplimiento estricto de las reglas de gestión de riesgo.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from google import genai
from google.genai import types

from config.settings import settings
from config.db import get_db
from core.logger import logger
from agent.tools import (
    get_ml_signal,
    get_market_news,
    get_portfolio_status,
    place_trade_order
)

# Diccionario de funciones disponibles para el agente
AVAILABLE_TOOLS = {
    "get_ml_signal": get_ml_signal,
    "get_market_news": get_market_news,
    "get_portfolio_status": get_portfolio_status,
    "place_trade_order": place_trade_order
}

SYSTEM_INSTRUCTION = """Eres el Agente Financiero Senior de 'Acciones Inteligentes'.
Tu objetivo es analizar activos, validar señales cuantitativas con contexto de
noticias y gestión de riesgo, y recomendar/ejecutar decisiones de inversión.

Reglas de Operación:
1. Siempre consulta la señal cuantitativa mediante 'get_ml_signal'.
2. Si la señal es BUY o SELL, consulta noticias con 'get_market_news' para
verificar si hay riesgos no capturados.
3. Antes de ejecutar o recomendar una orden, revisa el portafolio con
'get_portfolio_status'.
4. NUNCA asignes más del 10% del valor total del portafolio a una sola operación.
5. Justifica claramente cada decisión con datos cuantitativos y cualitativos.
"""


def _save_agent_trace(trace_data: Dict[str, Any]) -> str:
    """Almacena el historial de llamadas a herramientas y razonamiento en MongoDB."""
    try:
        db = get_db()
        res = db.agent_traces.insert_one(trace_data)
        return str(res.inserted_id)
    except Exception as e:
        logger.warning(f"No se pudo guardar la traza del agente en MongoDB: {e}")
        import uuid
        return f"TRACE-{uuid.uuid4().hex[:8].upper()}"


def run_financial_agent(
    ticker_query: str,
    user_email: str = "default_user@acciones.com",
    client: Optional[genai.Client] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Ejecuta el ciclo de razonamiento y toma de decisiones del Agente Financiero.

    Args:
        ticker_query: Símbolo bursátil a analizar (ej. NVDA, AAPL, MSFT).
        user_email: Identificador de la cuenta del usuario.
        client: Cliente opcional de genai.Client (útil para inyección o tests).
        model: Modelo de Gemini a utilizar (por defecto gemini-2.5-flash).

    Returns:
        Dict con el veredicto final, llamadas a herramientas realizadas y metadatos de auditoría.
    """
    ticker_clean = ticker_query.strip().upper()
    start_time = time.time()
    
    # 1. Configuración del cliente GenAI
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if client is None:
        if api_key:
            client = genai.Client(api_key=api_key)
        else:
            client = genai.Client()

    chosen_model = model or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    logger.info(f"🚀 Iniciando Agente Financiero para {ticker_clean} (Modelo: {chosen_model})...")

    # 2. Creación de la sesión de chat con herramientas nativas
    chat = client.chats.create(
        model=chosen_model,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[get_ml_signal, get_market_news, get_portfolio_status, place_trade_order],
            temperature=0.1
        )
    )

    # 3. Mensaje inicial al agente
    user_prompt = f"Analiza la oportunidad de inversión en el ticker: {ticker_clean}"
    response = chat.send_message(user_prompt)

    tool_call_history: List[Dict[str, Any]] = []
    iterations = 0
    max_iterations = 10  # Salvaguarda contra bucles infinitos

    # 4. Bucle de ejecución de herramientas (Agent Loop)
    while response.function_calls and iterations < max_iterations:
        iterations += 1
        for call in response.function_calls:
            func_name = call.name
            func_args = dict(call.args) if call.args else {}

            print(f"🤖 [Agente invocando Tool]: {func_name} con argumentos: {func_args}")
            logger.info(f"🤖 [Agente invocando Tool]: {func_name} con argumentos: {func_args}")

            # Inyectar user_email si la tool lo soporta y no fue provisto
            if func_name in ("get_portfolio_status", "place_trade_order") and "email" not in func_args:
                func_args["email"] = user_email

            # Ejecución local de la herramienta
            if func_name in AVAILABLE_TOOLS:
                try:
                    tool_output = AVAILABLE_TOOLS[func_name](**func_args)
                except Exception as e:
                    logger.error(f"Error ejecutando tool {func_name}: {e}")
                    tool_output = {"error": f"Error ejecutando {func_name}: {str(e)}"}
            else:
                tool_output = {"error": f"Herramienta '{func_name}' no disponible."}

            tool_call_history.append({
                "iteration": iterations,
                "tool": func_name,
                "arguments": func_args,
                "output": tool_output,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # Devolución del resultado al agente
            response = chat.send_message(
                types.Part.from_function_response(
                    name=func_name,
                    response={"result": tool_output}
                )
            )

    elapsed_time = round(time.time() - start_time, 2)
    final_verdict = response.text if hasattr(response, "text") and response.text else "Análisis completado sin dictamen textual."

    print(f"\n💡 [Dictamen Final del Agente]:\n{final_verdict}\n")
    logger.info(f"💡 [Dictamen Final del Agente para {ticker_clean}]: {final_verdict[:200]}...")

    # 5. Registro y auditoría de la traza
    trace_record = {
        "ticker": ticker_clean,
        "email": user_email,
        "model": chosen_model,
        "user_prompt": user_prompt,
        "final_verdict": final_verdict,
        "tool_calls": tool_call_history,
        "iterations": iterations,
        "execution_time_seconds": elapsed_time,
        "created_at": datetime.now(timezone.utc)
    }
    trace_id = _save_agent_trace(trace_record)

    return {
        "trace_id": trace_id,
        "ticker": ticker_clean,
        "final_verdict": final_verdict,
        "tool_calls": tool_call_history,
        "execution_time_seconds": elapsed_time,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
