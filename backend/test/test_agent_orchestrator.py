"""Pruebas del Orquestador Agéntico, bucle de decisión y reglas operativas."""

import pytest
from unittest.mock import MagicMock, patch
from google.genai import types

from agent.orchestrator import run_financial_agent, SYSTEM_INSTRUCTION, AVAILABLE_TOOLS


def test_system_instruction_rules():
    """Verifica que las 5 reglas operativas de la especificación técnica estén en el prompt del sistema."""
    assert "Agente Financiero Senior" in SYSTEM_INSTRUCTION
    assert "get_ml_signal" in SYSTEM_INSTRUCTION
    assert "get_market_news" in SYSTEM_INSTRUCTION
    assert "get_portfolio_status" in SYSTEM_INSTRUCTION
    assert "10%" in SYSTEM_INSTRUCTION
    assert "Justifica claramente" in SYSTEM_INSTRUCTION


def test_orchestrator_loop_with_tool_calls():
    """Simula el flujo completo del loop agéntico con Gemini respondiendo function_calls."""
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_client.chats.create.return_value = mock_chat

    # 1. Primera respuesta de Gemini: pide llamar a get_ml_signal
    call_ml = MagicMock()
    call_ml.name = "get_ml_signal"
    call_ml.args = {"ticker": "NVDA"}

    response_1 = MagicMock()
    response_1.function_calls = [call_ml]
    response_1.text = None

    # 2. Segunda respuesta de Gemini: pide llamar a get_market_news
    call_news = MagicMock()
    call_news.name = "get_market_news"
    call_news.args = {"ticker": "NVDA", "limit": 3}

    response_2 = MagicMock()
    response_2.function_calls = [call_news]
    response_2.text = None

    # 3. Tercera respuesta: veredicto final
    response_3 = MagicMock()
    response_3.function_calls = []
    response_3.text = "Dictamen Final: Se recomienda COMPRAR NVDA debido a fuerte señal cuantitativa (85%) y catalizadores positivos."

    # Configurar secuencia de retornos de send_message
    mock_chat.send_message.side_effect = [response_1, response_2, response_3]

    mock_db = MagicMock()
    mock_db.agent_traces.insert_one.return_value.inserted_id = "trace_abc123"

    with patch("agent.orchestrator.get_db", return_value=mock_db), \
         patch("agent.tools.get_or_load_xgboost_model") as mock_load, \
         patch("agent.tools.extract_technical_features") as mock_feat:
        
        mock_m = MagicMock()
        mock_m.predict_proba.return_value = [[0.15, 0.85]]
        mock_load.return_value = mock_m
        mock_feat.return_value = MagicMock()

        result = run_financial_agent("NVDA", user_email="analyst@firm.com", client=mock_client)

        assert result["ticker"] == "NVDA"
        assert "Dictamen Final" in result["final_verdict"]
        assert len(result["tool_calls"]) == 2
        assert result["tool_calls"][0]["tool"] == "get_ml_signal"
        assert result["tool_calls"][1]["tool"] == "get_market_news"
        assert "trace_id" in result
