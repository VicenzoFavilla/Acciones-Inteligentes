"""Implementación concreta de DataLoader usando yfinance."""

from typing import Optional
import yfinance as yf
import pandas as pd

from ml.data.base import DataLoader


class YFinanceDataLoader(DataLoader):
    """Cargador de datos de mercado utilizando la API de Yahoo Finance."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def fetch_data(
        self,
        ticker: str,
        period: str = "2y",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Descarga datos históricos de Yahoo Finance y normaliza la salida."""
        stock = yf.Ticker(ticker)

        if start and end:
            df = stock.history(start=start, end=end, interval=interval, timeout=self.timeout)
        else:
            df = stock.history(period=period, interval=interval, timeout=self.timeout)

        # Si MultiIndex en columnas (común en versiones recientes de yfinance), aplanar
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = self.validate_dataframe(df, ticker)
        return df
