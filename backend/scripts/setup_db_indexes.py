"""Script de mantenimiento: crea índices y limpia colecciones extra."""

import sys
import os
from pymongo import ASCENDING, DESCENDING

# Asegurar que el directorio raíz del backend esté en el path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.db import get_db


def main():
    db = get_db()

    # Crear índices
    db.history.create_index([("ticker", ASCENDING), ("timestamp", DESCENDING)], name="idx_ticker_timestamp")
    db.acciones_usuario.create_index([("ticker", ASCENDING), ("fecha", DESCENDING)], name="idx_ticker_fecha")
    db.acciones_usuario.create_index([("decision_usuario", ASCENDING)], name="idx_decision_usuario")
    db.modelos_binarios.create_index([("ticker", ASCENDING)], name="uk_ticker", unique=True)
    db.modelos_uso.create_index([("ticker", ASCENDING)], name="uk_ticker", unique=True)

    # Eliminar colección extra si existe
    if "historico_modelo" in db.list_collection_names():
        db.drop_collection("historico_modelo")
        print("[INFO] Colección 'historico_modelo' eliminada.")
    else:
        print("[INFO] Colección 'historico_modelo' no existe. Nada que eliminar.")

    print("[OK] Índices creados/asegurados y limpieza completada.")


if __name__ == "__main__":
    main()
