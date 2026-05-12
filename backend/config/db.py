from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config.settings import settings
from core.logger import logger

# Singleton para la base de datos
_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        mongo_url = settings.MONGO_URL
        logger.info(f"Conectando a base de datos...")
        try:
            # ConnectTimeoutMS para evitar bloqueos infinitos
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            # Verificar conexión
            client.admin.command('ping')
            _db_instance = client.get_database()
            logger.info("Conexión a MongoDB exitosa.")
        except Exception as e:
            logger.error(f"Error crítico al conectar a MongoDB: {e}")
            raise e
    return _db_instance