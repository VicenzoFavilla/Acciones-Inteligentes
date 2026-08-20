"""Paquete src.agent para compatibilidad con la estructura especificada en el PDF."""

import sys
import os

# Asegurar que backend esté en el sys.path para resolución de módulos
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agent.tools import (
    get_ml_signal,
    get_market_news,
    get_portfolio_status,
    place_trade_order,
    AVAILABLE_TOOLS
)
from agent.orchestrator import run_financial_agent, SYSTEM_INSTRUCTION
from agent.ml_loader import get_or_load_xgboost_model, model_cache

__all__ = [
    "get_ml_signal",
    "get_market_news",
    "get_portfolio_status",
    "place_trade_order",
    "AVAILABLE_TOOLS",
    "run_financial_agent",
    "SYSTEM_INSTRUCTION",
    "get_or_load_xgboost_model",
    "model_cache",
]
