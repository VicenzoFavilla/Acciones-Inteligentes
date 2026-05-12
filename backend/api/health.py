from fastapi import APIRouter, Depends, HTTPException, status
from config.db import get_db
from config.settings import settings
import os
import joblib

router = APIRouter()

@router.get("/health", tags=["Health"])
def health_check():
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "ml_models": "unknown"
    }

    # Check Database
    try:
        db = get_db()
        # Ping command to check if connection is alive
        db.command("ping")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"

    # Check ML Models directory
    try:
        if os.path.exists(settings.MODEL_DIR):
            models = [f for f in os.listdir(settings.MODEL_DIR) if f.endswith('.pkl')]
            if models:
                health_status["ml_models"] = f"available ({len(models)} models)"
            else:
                health_status["ml_models"] = "no models found"
        else:
            health_status["ml_models"] = "directory not found"
    except Exception as e:
        health_status["ml_models"] = "error checking directory"
        health_status["status"] = "unhealthy"

    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_status)

    return health_status
