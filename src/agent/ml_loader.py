"""src/agent/ml_loader.py - Re-exportación del cargador perezoso de modelos."""

import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agent.ml_loader import (
    ModelCache,
    model_cache,
    get_or_load_xgboost_model
)

__all__ = [
    "ModelCache",
    "model_cache",
    "get_or_load_xgboost_model"
]
