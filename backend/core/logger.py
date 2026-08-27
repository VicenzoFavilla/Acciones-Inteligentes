"""Sistema de Logging Estructurado (JSON y Formato Consola) para MLOps y Backend."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Formateador de logs en formato JSON estructurado para producción / cloud / MLOps."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineNo": record.lineno,
        }

        # Extraer atributos extras pasados en logger.info("msg", extra={...})
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_obj["data"] = record.extra_data

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logger(
    name: str = "acciones_inteligentes",
    log_level: str | None = None,
    use_json: bool | None = None,
) -> logging.Logger:
    """Configura y retorna una instancia de logger estructurado."""
    level_name = log_level or os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # Determinar si usar JSON a partir de variable de entorno o parámetro
    if use_json is None:
        use_json = os.getenv("LOG_FORMAT", "TEXT").upper() == "JSON"

    logger_inst = logging.getLogger(name)
    logger_inst.setLevel(level)

    # Evitar duplicación de handlers si ya fue configurado
    if not logger_inst.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        if use_json:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        handler.setFormatter(formatter)
        logger_inst.addHandler(handler)

    logger_inst.propagate = False
    return logger_inst


# Instancia por defecto
logger = setup_logger()
