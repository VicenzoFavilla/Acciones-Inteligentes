"""Router FastAPI para el Agente Financiero Autónomo y gestión Human-In-The-Loop."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone

from api.deps import get_current_user
from config.db import get_db
from core.logger import logger
from agent.orchestrator import run_financial_agent, AVAILABLE_TOOLS, SYSTEM_INSTRUCTION
from services.wallet import buy_stock, sell_stock

router = APIRouter(prefix="/agent", tags=["AI Agent"])


class AgentAnalysisRequest(BaseModel):
    ticker: str = Field(..., example="NVDA", description="Símbolo del activo a analizar")
    model: Optional[str] = Field(None, example="gemini-2.5-flash", description="Modelo de Gemini a utilizar")


class OrderApprovalRequest(BaseModel):
    notes: Optional[str] = Field(None, description="Notas u observaciones del usuario al aprobar")


@router.post("/analyze")
def analyze_ticker(
    request: AgentAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Ejecuta el ciclo de razonamiento del Agente Financiero Autónomo para un ticker.
    
    Combina señales de XGBoost, noticias de mercado, estado de la cartera y gestión de riesgo.
    """
    user_email = current_user.get("email", "default_user@acciones.com")
    ticker = request.ticker.upper().strip()

    try:
        result = run_financial_agent(
            ticker_query=ticker,
            user_email=user_email,
            model=request.model
        )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error al ejecutar análisis del agente para {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Error durante el análisis agéntico: {str(e)}")


@router.get("/traces")
def get_agent_traces(
    ticker: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Obtiene el historial de decisiones, herramientas invocadas y auditoría de riesgo."""
    db = get_db()
    query: Dict[str, Any] = {"email": current_user.get("email")}
    if ticker:
        query["ticker"] = ticker.upper().strip()

    try:
        traces = list(
            db.agent_traces.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        for t in traces:
            t["_id"] = str(t["_id"])
            if isinstance(t.get("created_at"), datetime):
                t["created_at"] = t["created_at"].isoformat()

        return {
            "status": "success",
            "count": len(traces),
            "traces": traces
        }
    except Exception as e:
        logger.error(f"Error al recuperar trazas del agente: {e}")
        raise HTTPException(status_code=500, detail="Error consultando historial de trazas.")


@router.post("/orders/{order_id}/approve")
def approve_agent_order(
    order_id: str,
    payload: Optional[OrderApprovalRequest] = None,
    current_user: dict = Depends(get_current_user)
):
    """Aprobación Human-In-The-Loop: el usuario autoriza la ejecución de una orden sugerida por la IA."""
    db = get_db()
    email = current_user.get("email")

    try:
        query = {"_id": ObjectId(order_id), "email": email}
    except Exception:
        query = {"_id": order_id, "email": email}

    order = db.orders.find_one(query)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada o no pertenece al usuario.")

    if order.get("status") != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"La orden ya se encuentra en estado '{order.get('status')}' y no puede ser aprobada nuevamente."
        )

    ticker = order["ticker"]
    action = order["action"]
    quantity = int(order["quantity"])
    price = float(order.get("estimated_price", 100.0))

    # Ejecutar en la billetera virtual
    if action == "BUY":
        success, msg = buy_stock(email, ticker, quantity, price)
    else:
        success, msg = sell_stock(email, ticker, quantity, price)

    if not success:
        db.orders.update_one(
            query,
            {"$set": {"status": "execution_failed", "error": msg, "updated_at": datetime.now(timezone.utc)}}
        )
        raise HTTPException(status_code=400, detail=f"Fallo al ejecutar orden: {msg}")

    db.orders.update_one(
        query,
        {
            "$set": {
                "status": "executed",
                "approved_by_user": True,
                "approved_at": datetime.now(timezone.utc),
                "approval_notes": payload.notes if payload else None,
                "execution_price": price
            }
        }
    )

    return {
        "status": "success",
        "message": f"Orden {order_id} aprobada y ejecutada exitosamente.",
        "details": msg
    }


@router.post("/orders/{order_id}/reject")
def reject_agent_order(
    order_id: str,
    payload: Optional[OrderApprovalRequest] = None,
    current_user: dict = Depends(get_current_user)
):
    """Rechazo Human-In-The-Loop: el usuario descarta una orden sugerida por el agente."""
    db = get_db()
    email = current_user.get("email")

    try:
        query = {"_id": ObjectId(order_id), "email": email}
    except Exception:
        query = {"_id": order_id, "email": email}

    order = db.orders.find_one(query)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    db.orders.update_one(
        query,
        {
            "$set": {
                "status": "rejected_by_user",
                "rejected_at": datetime.now(timezone.utc),
                "rejection_notes": payload.notes if payload else None
            }
        }
    )

    return {
        "status": "success",
        "message": f"Orden {order_id} rechazada correctamente."
    }


@router.get("/info")
def get_agent_info():
    """Retorna información general del agente, reglas operativas y herramientas disponibles."""
    return {
        "name": "Agente Financiero Senior de Acciones Inteligentes",
        "description": "Arquitectura híbrida XGBoost + Google GenAI (Gemini) + News + Risk Management",
        "system_instruction": SYSTEM_INSTRUCTION,
        "available_tools": list(AVAILABLE_TOOLS.keys()),
        "risk_limits": {
            "max_capital_per_operation_pct": 10.0,
            "human_in_the_loop_required": True
        }
    }
