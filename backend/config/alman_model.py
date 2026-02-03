"""Persistencia de modelos en MongoDB como binarios."""

from config.db import get_db
from bson.binary import Binary
import joblib
import io
from datetime import datetime

def guardar_modelo_en_mongo(ticker, modelo):
    """Guarda un modelo serializado (joblib) en MongoDB bajo la clave ticker."""
    buffer = io.BytesIO()
    joblib.dump(modelo, buffer)
    buffer.seek(0)

    db = get_db()
    db.modelos_binarios.replace_one(
        {"ticker": ticker},
        {
            "ticker": ticker,
            "modelo": Binary(buffer.read()),
            "ultima_actualizacion": datetime.now()
        },
        upsert=True
    )
    print(f"[INFO] Modelo para {ticker} guardado en MongoDB.")


def cargar_modelo_de_mongo(ticker):
    """Carga un modelo desde MongoDB (o None si no existe)."""
    db = get_db()
    doc = db.modelos_binarios.find_one({"ticker": ticker})
    if doc and "modelo" in doc:
        buffer = io.BytesIO(doc["modelo"])
        modelo = joblib.load(buffer)
        print(f"[INFO] Modelo para {ticker} cargado desde MongoDB.")
        return modelo
    return None
