import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Singleton para la base de datos
_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017/acciones_ml")
        print(f"Intentando conectar a: {mongo_url}")
        try:
            # ConnectTimeoutMS para evitar bloqueos infinitos
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            # Verificar conexión
            client.admin.command('ping')
            _db_instance = client.get_database()
        except Exception as e:
            print(f"Error de conexión a MongoDB: {e}")
            raise e
    return _db_instance