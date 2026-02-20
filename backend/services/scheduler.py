from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import os
from scripts.update_models import main as update_models_main
from config.alman_model import cargar_modelo_de_mongo

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_update_task():
    """Ejecuta el script de actualización de modelos."""
    logger.info("Iniciando actualización automática de modelos de IA...")
    try:
        # Mocking sys.argv para que argparse no rompa si se llama desde aquí
        import sys
        original_args = sys.argv
        sys.argv = ['update_models.py', '--period', '1y']
        update_models_main()
        sys.argv = original_args
        logger.info("Actualización automática de modelos completada exitosamente.")
    except Exception as e:
        logger.error(f"Error durante la actualización automática de modelos: {e}")

def start_scheduler():
    """Inicia el programador de tareas."""
    scheduler = BackgroundScheduler()
    
    # Programar para que corra todos los días a las 00:00 (medianoche)
    trigger = CronTrigger(hour=0, minute=0)
    scheduler.add_job(run_update_task, trigger=trigger, name="update_ai_models")
    
    scheduler.start()
    logger.info("Programador de tareas iniciado (Actualización diaria a media noche).")

    # Verificación inicial: Si no hay modelos en Mongo, entrenar en segundo plano para no bloquear el inicio del servidor
    try:
        xgb = cargar_modelo_de_mongo("GLOBAL_XGB")
        mlp = cargar_modelo_de_mongo("GLOBAL_MLP")
        
        if xgb is None or mlp is None:
            logger.info("No se detectaron modelos globales. Programando entrenamiento inicial en segundo plano...")
            # Ejecutar inmediatamente pero como tarea de fondo
            scheduler.add_job(run_update_task, name="initial_ai_training")
    except Exception as e:
        logger.error(f"Error en la verificación inicial de modelos: {e}")
