"""src/agent/tools.py - Re-exportación de las herramientas del agente."""

import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agent.tools import (
    extract_technical_features,
    get_ml_signal,
    get_market_news,
    get_portfolio_status,
    place_trade_order
)

__all__ = [
    "extract_technical_features",
    "get_ml_signal",
    "get_market_news",
    "get_portfolio_status",
    "place_trade_order"
]
