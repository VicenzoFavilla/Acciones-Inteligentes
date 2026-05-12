import logging
import sys
from pydantic import BaseModel

class LogConfig(BaseModel):
    """Logging configuration to be set for the server"""
    LOGGER_NAME: str = "acciones_inteligentes"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(name)s | %(message)s"
    LOG_LEVEL: str = "DEBUG"

    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: dict = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers: dict = {
        LOGGER_NAME: {"handlers": ["default"], "level": LOG_LEVEL},
    }

# Setup logger
import logging.config
logging.config.dictConfig(LogConfig().dict())
logger = logging.getLogger("acciones_inteligentes")
