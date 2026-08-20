"""Módulo de carga perezosa (Lazy Loading) y aislamiento para modelos ML (XGBoost).

Asegura que los modelos entrenados se mantengan en memoria para no re-cargar
archivos .pkl o realizar consultas a MongoDB en cada llamada del agente.
"""

import os
import joblib
from typing import Any, Dict, Optional
from config.settings import settings
from config.alman_model import cargar_modelo_de_mongo
from core.logger import logger


class ModelCache:
    """Singleton cache en memoria para modelos XGBoost locales y globales."""
    _instance: Optional["ModelCache"] = None
    _models: Dict[str, Any] = {}

    def __new__(cls) -> "ModelCache":
        if cls._instance is None:
            cls._instance = super(ModelCache, cls).__new__(cls)
            cls._instance._models = {}
        return cls._instance

    def get_model(self, key: str) -> Optional[Any]:
        """Obtiene un modelo cacheado si existe."""
        return self._models.get(key.upper())

    def set_model(self, key: str, model: Any) -> None:
        """Almacena un modelo en memoria."""
        self._models[key.upper()] = model

    def clear(self) -> None:
        """Limpia la cache."""
        self._models.clear()


model_cache = ModelCache()


def get_or_load_xgboost_model(ticker: str, model_type: str = "local_xgb") -> Optional[Any]:
    """Carga de forma perezosa (lazy) el modelo XGBoost para el ticker o tipo solicitado.
    
    1. Revisa si ya está cargado en memoria (RAM).
    2. Si no, busca en MongoDB.
    3. Si no, busca en el sistema de archivos (.pkl).
    4. Si es local y no existe, entrena bajo demanda y cachea.
    """
    cache_key = f"{model_type}:{ticker}".upper()
    cached = model_cache.get_model(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Cargando modelo ML perezosamente para {cache_key}...")
    model = None

    if model_type == "local_xgb":
        try:
            model = cargar_modelo_de_mongo(ticker)
        except Exception as e:
            logger.warning(f"No se pudo consultar modelo en MongoDB para {ticker}: {e}")
            model = None

        if model is None:
            # Buscar en filesystem
            filepath = os.path.join(settings.MODEL_DIR, f"{ticker.upper()}_xgb.pkl")
            if os.path.exists(filepath):
                try:
                    model = joblib.load(filepath)
                except Exception as e:
                    logger.warning(f"No se pudo cargar {filepath}: {e}")

        if model is None:
            # Entrenar modelo optimizado bajo demanda
            try:
                from ml.trainer import train_buy_model_optimizado
                from config.alman_model import guardar_modelo_en_mongo
                model, _ = train_buy_model_optimizado(ticker)
                try:
                    guardar_modelo_en_mongo(ticker, model)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Fallo al entrenar modelo bajo demanda para {ticker}: {e}")
                return None

    elif model_type in ("global_xgb", "GLOBAL_XGB"):
        try:
            model = cargar_modelo_de_mongo("GLOBAL_XGB")
        except Exception as e:
            logger.warning(f"No se pudo consultar modelo global en MongoDB: {e}")
            model = None

        if model is None:
            filepath = os.path.join(settings.MODEL_DIR, "global_xgb.pkl")
            if os.path.exists(filepath):
                try:
                    model = joblib.load(filepath)
                except Exception as e:
                    logger.warning(f"No se pudo cargar {filepath}: {e}")


    if model is not None:
        model_cache.set_model(cache_key, model)
        logger.info(f"Modelo {cache_key} cargado y cacheado en memoria exitosamente.")

    return model
