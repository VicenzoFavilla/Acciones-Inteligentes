"""Etiqueta registros de acciones_usuario con el resultado real (y_true).

Para cada documento sin y_true, descarga el cierre del día siguiente y marca
y_true=1 si Close_{t+1} > Close_t * 1.01, si no y_true=0.
"""

from datetime import timedelta

import yfinance as yf
from pymongo import MongoClient


def main():
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
    db = client["acciones_ml"]

    cur = db.acciones_usuario.find({"y_true": {"$exists": False}}).sort("fecha", 1)
    updated = 0
    for doc in cur:
        ticker = doc.get("ticker")
        fecha = doc.get("fecha")
        precio_t = doc.get("precio")
        if not ticker or not fecha or precio_t is None:
            continue
        # ventana pequeña alrededor del día siguiente por zonas horarias/mercados
        start = fecha + timedelta(days=1)
        end = start + timedelta(days=3)
        try:
            hist = yf.Ticker(ticker).history(start=start.date(), end=end.date(), interval="1d")
            if hist is None or hist.empty:
                continue
            close_next = float(hist["Close"].iloc[0])
            y_true = 1 if close_next > float(precio_t) * 1.01 else 0
            db.acciones_usuario.update_one({"_id": doc["_id"]}, {"$set": {"y_true": y_true}})
            updated += 1
        except Exception:
            continue

    print(f"[OK] Registros actualizados con y_true: {updated}")


if __name__ == "__main__":
    main()
