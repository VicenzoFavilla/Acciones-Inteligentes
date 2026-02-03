"""Script utilitario: verifica conexión y estado de colecciones en MongoDB."""

import sys
from datetime import datetime

try:
    from pymongo import MongoClient
except Exception as e:
    print(f"[ERROR] pymongo no está instalado: {e}")
    sys.exit(2)


def main():
    uri = "mongodb://localhost:27017/"
    print(f"[INFO] Conectando a MongoDB en {uri} ...")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.server_info()  # fuerza la conexión
    except Exception as e:
        print(f"[ERROR] No se pudo conectar a MongoDB: {e}")
        sys.exit(1)

    db = client["acciones_ml"]
    print("[INFO] Conectado. DB: acciones_ml")

    try:
        collections = db.list_collection_names()
        print(f"[INFO] Colecciones: {collections}")
    except Exception as e:
        print(f"[WARN] No se pudo listar colecciones: {e}")
        collections = []

    def preview(coll_name, sort_field=None, limit=3):
        if coll_name not in collections:
            print(f"- {coll_name}: no existe")
            return
        count = db[coll_name].count_documents({})
        print(f"- {coll_name}: {count} documentos")
        cursor = db[coll_name].find({})
        if sort_field:
            try:
                cursor = cursor.sort(sort_field, -1)
            except Exception:
                pass
        try:
            docs = list(cursor.limit(limit))
            for i, d in enumerate(docs, 1):
                # limitar campos para no saturar la salida
                subset = {}
                for k in [
                    "ticker","name","price","change","volume","timestamp",
                    "fecha","recomendacion_ml","decision_usuario",
                    "ultima_actualizacion","veces_usado","ultima_vez"
                ]:
                    if k in d:
                        subset[k] = d[k]
                print(f"  · doc#{i}: {subset}")
        except Exception as e:
            print(f"  · error al obtener muestra: {e}")

    print("[INFO] Revisando colecciones esperadas...")
    preview("history", sort_field="timestamp")
    preview("acciones_usuario", sort_field="fecha")
    preview("modelos_binarios", sort_field="ultima_actualizacion")
    preview("modelos_uso", sort_field="ultima_vez")

    print("[OK] Revisión completada.")


if __name__ == "__main__":
    main()
