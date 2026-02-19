import os
from pymongo import MongoClient

def get_db():
    # El nombre "mongodb" debe coincidir con el nombre del servicio en tu YAML
    mongo_url = os.getenv("MONGO_URL", "mongodb://mongodb:27017/acciones_ml")

    print(f"Intentando conectar a: {mongo_url}")
    client = MongoClient(mongo_url)
    return client.get_database()