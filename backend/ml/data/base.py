"""Interfaz abstracta para la ingesta y carga de datos financieros (DataLoader)."""

from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd


class DataLoader(ABC):
    """Clase base abstracta para proveedores de datos de mercado."""

    REQUIRED_COLUMNS: List[str] = ["Open", "High", "Low", "Close", "Volume"]

    @abstractmethod
    def fetch_data(
        self,
        ticker: str,
        period: str = "2y",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Descarga o carga los datos históricos en formato OHLCV.

        Args:
            ticker: Símbolo o identificador del activo (e.g. 'AAPL', 'MSFT').
            period: Rango temporal ('1mo', '3mo', '6mo', '1y', '2y', '5y', 'max').
            interval: Frecuencia de las velas ('1d', '1h', etc.).
            start: Fecha inicial en formato YYYY-MM-DD (opcional).
            end: Fecha final en formato YYYY-MM-DD (opcional).

        Returns:
            pd.DataFrame indexado por fecha con columnas OHLCV obligatorias.
        """
        pass

    def validate_dataframe(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Valida que el DataFrame contenga las columnas mínimas y tipo de datos adecuado."""
        if df is None or df.empty:
            raise ValueError(f"No se obtuvieron datos para el ticker '{ticker}'.")

        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"El dataset para '{ticker}' carece de las columnas obligatorias: {missing}")

        # Asegurar orden cronológico y eliminar duplicados de índice
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]
        
        # Coerción numérica
        for col in self.REQUIRED_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=self.REQUIRED_COLUMNS)
        if df.empty:
            raise ValueError(f"Todos los registros para '{ticker}' contenían valores nulos en columnas requeridas.")

        return df
