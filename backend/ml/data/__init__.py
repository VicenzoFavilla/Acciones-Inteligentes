"""Módulo de Ingesta y Carga de Datos de Mercado."""

from ml.data.base import DataLoader
from ml.data.yfinance_loader import YFinanceDataLoader
from ml.data.memory_loader import MemoryDataLoader


def get_data_loader(source: str = "yfinance", **kwargs) -> DataLoader:
    """Factory para instanciar el DataLoader adecuado."""
    src = source.lower().strip()
    if src in ("yfinance", "yf"):
        return YFinanceDataLoader(**kwargs)
    elif src in ("memory", "mock"):
        return MemoryDataLoader(**kwargs)
    else:
        raise ValueError(f"Fuente de datos no soportada: '{source}'. Opciones: 'yfinance', 'memory'.")


__all__ = [
    "DataLoader",
    "YFinanceDataLoader",
    "MemoryDataLoader",
    "get_data_loader",
]
