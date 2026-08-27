"""Implementación de DataLoader en memoria / DataFrame para pruebas y simulación."""

from typing import Dict, Optional
import pandas as pd

from ml.data.base import DataLoader


class MemoryDataLoader(DataLoader):
    """Cargador de datos desde DataFrames prealmacenados en memoria o diccionarios."""

    def __init__(self, data_map: Optional[Dict[str, pd.DataFrame]] = None):
        self.data_map: Dict[str, pd.DataFrame] = data_map or {}

    def set_data(self, ticker: str, df: pd.DataFrame) -> None:
        self.data_map[ticker.upper()] = df

    def fetch_data(
        self,
        ticker: str,
        period: str = "2y",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        ticker_key = ticker.upper()
        if ticker_key not in self.data_map:
            raise ValueError(f"Ticker '{ticker}' no encontrado en MemoryDataLoader.")

        df = self.data_map[ticker_key].copy()
        df = self.validate_dataframe(df, ticker)
        return df
