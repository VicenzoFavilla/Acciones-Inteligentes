"""Paquete del Agente Financiero Autónomo de Acciones Inteligentes."""

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
