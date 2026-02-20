import os
from pymongo import MongoClient

def get_db():
    # Usamos localhost por defecto para ejecución local, Docker lo sobreescribirá vía env var
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017/acciones_ml")

    print(f"Intentando conectar a: {mongo_url}")
    client = MongoClient(mongo_url)
    return client.get_database()