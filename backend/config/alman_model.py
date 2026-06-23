"""Persistencia de modelos en MongoDB como binarios."""

from config.db import get_db
from bson.binary import Binary
import joblib
import io
from datetime import datetime


# Versión de features actual — incrementar si se cambia FEATURE_COLUMNS
FEATURE_VERSION = "v2"


def guardar_modelo_en_mongo(ticker, modelo):
    """Guarda un modelo serializado (joblib) en MongoDB bajo la clave ticker."""
    from ml.features import FEATURE_COLUMNS  # import tardío para evitar ciclos

    buffer = io.BytesIO()
    joblib.dump(modelo, buffer)
    buffer.seek(0)

    db = get_db()
    db.modelos_binarios.replace_one(
        {"ticker": ticker},
        {
            "ticker": ticker,
            "modelo": Binary(buffer.read()),
            "ultima_actualizacion": datetime.now(),
            # Guardamos la firma de features para detectar modelos obsoletos
            "feature_version": FEATURE_VERSION,
            "feature_names": FEATURE_COLUMNS,
        },
        upsert=True,
    )
    print(f"[INFO] Modelo para {ticker} guardado en MongoDB ({FEATURE_VERSION}).")


def cargar_modelo_de_mongo(ticker):
    """Carga un modelo desde MongoDB.

    Retorna None si:
      - No existe el documento.
      - La versión de features no coincide con la actual (modelo obsoleto).
    En ese caso el llamador debe reentrenar el modelo.
    """
    from ml.features import FEATURE_COLUMNS  # import tardío para evitar ciclos

    db = get_db()
    doc = db.modelos_binarios.find_one({"ticker": ticker})
    if not doc or "modelo" not in doc:
        return None

    # Validar versión / firma de features
    stored_version = doc.get("feature_version")
    stored_features = doc.get("feature_names", [])

    if stored_version != FEATURE_VERSION or list(stored_features) != list(FEATURE_COLUMNS):
        print(
            f"[WARN] Modelo obsoleto para '{ticker}' "
            f"(versión almacenada: {stored_version!r}, actual: {FEATURE_VERSION!r}). "
            "Se descartará y se reentrenará con las features actuales."
        )
        # Eliminar modelo obsoleto para no acumularlo
        db.modelos_binarios.delete_one({"ticker": ticker})
        return None

    buffer = io.BytesIO(doc["modelo"])
    modelo = joblib.load(buffer)
    print(f"[INFO] Modelo para '{ticker}' cargado desde MongoDB ({FEATURE_VERSION}).")
    return modelo


def limpiar_modelos_obsoletos():
    """Elimina de MongoDB todos los modelos que no coincidan con las features actuales.

    Útil para ejecutar manualmente tras actualizar FEATURE_COLUMNS.
    """
    from ml.features import FEATURE_COLUMNS

    db = get_db()
    resultado = db.modelos_binarios.delete_many(
        {
            "$or": [
                {"feature_version": {"$ne": FEATURE_VERSION}},
                {"feature_names": {"$ne": FEATURE_COLUMNS}},
                {"feature_version": {"$exists": False}},
            ]
        }
    )
    print(f"[INFO] Modelos obsoletos eliminados: {resultado.deleted_count}")
    return resultado.deleted_count

