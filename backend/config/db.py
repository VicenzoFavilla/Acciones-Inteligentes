from pymongo import MongoClient
from pymongo.errors import PyMongoError
from config.settings import settings
from core.logger import logger

# Singleton para el CLIENTE de la base de datos (no para la base de datos en sí)
_mongo_client = None

def get_db():
    """
    Retorna la instancia de la base de datos utilizando un cliente Singleton.
    """
    global _mongo_client
    
    if _mongo_client is None:
        mongo_url = settings.MONGO_URL
        logger.info("Conectando a MongoDB...")
        try:
            # serverSelectionTimeoutMS controla el tiempo de espera del ping y selección de servidor
            _mongo_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            
            # Verificar conexión real antes de continuar
            _mongo_client.admin.command('ping')
            logger.info("Conexión a MongoDB exitosa.")
            
            # Inicializar índices una sola vez al conectar
            db_instance = _mongo_client.get_database()
            init_db(db_instance)
            
        except PyMongoError as e:
            _mongo_client = None  # Resetear en caso de fallo para permitir reintentos
            logger.critical(f"Error crítico al conectar a MongoDB: {e}")
            raise e
            
    return _mongo_client.get_database()

def init_db(db):
    """Inicializa índices compuestos para optimizar consultas."""
    try:
        # Transacciones: búsqueda rápida por usuario y fecha
        db.transactions.create_index([("email", 1), ("timestamp", -1)])
        # Órdenes: búsqueda para ejecución rápida
        db.orders.create_index([("status", 1), ("ticker", 1)])
        # Historial: para gráficos y analítica
        db.history.create_index([("ticker", 1), ("timestamp", -1)], name="idx_ticker_timestamp")
        logger.info("Índices de MongoDB inicializados correctamente.")
    except PyMongoError as e:
        logger.error(f"Error inicializando índices: {e}")