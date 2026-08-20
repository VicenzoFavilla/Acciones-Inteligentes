"""src/agent/orchestrator.py - Re-exportación del orquestador del agente."""

import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agent.orchestrator import (
    run_financial_agent,
    SYSTEM_INSTRUCTION,
    AVAILABLE_TOOLS
)

__all__ = [
    "run_financial_agent",
    "SYSTEM_INSTRUCTION",
    "AVAILABLE_TOOLS"
]
