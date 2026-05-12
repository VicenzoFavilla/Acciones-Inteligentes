from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class PredictionRequest(BaseModel):
    ticker: str = Field(..., description="Símbolo de la acción (ej. AAPL)", min_length=1, max_length=10)
    model_type: Optional[str] = Field(default="local_xgb", description="Tipo de modelo a utilizar", pattern="^(local_xgb|global_xgb|global_mlp)$")
    prob_threshold: Optional[float] = Field(default=0.5, ge=0.0, le=1.0, description="Umbral de probabilidad para recomendación de compra")

class PredictionResponse(BaseModel):
    ticker: str
    precio: float
    recomendacion: str
    history: List[float] = []
    ohlc: List[Dict[str, Any]] = []

class MarketDataResponse(BaseModel):
    ticker: str
    nombre: str
    precio: float
    variacion: float
    color_green: bool
    volumen: Optional[int] = None
    market_cap: Optional[int] = None
