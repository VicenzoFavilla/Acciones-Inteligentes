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
            # Inicializar índices
            init_db(_db_instance)
        except Exception as e:
            logger.error(f"Error crítico al conectar a MongoDB: {e}")
            raise e
    return _db_instance

def init_db(db):
    """Inicializa índices compuestos para optimizar consultas."""
    try:
        # Transacciones: búsqueda rápida por usuario y fecha
        db.transactions.create_index([("email", 1), ("timestamp", -1)])
        # Órdenes: búsqueda para ejecución rápida
        db.orders.create_index([("status", 1), ("ticker", 1)])
        # Historial: para gráficos y analítica
        db.history.create_index([("ticker", 1), ("timestamp", -1)], name="idx_ticker_timestamp")
        print("Índices de MongoDB inicializados correctamente.")
    except Exception as e:
        print(f"Error inicializando índices: {e}")