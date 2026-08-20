import warnings
# Silenciar ruidos de scikit-learn y otras librerías
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*batch_size.*")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from services.scheduler import start_scheduler
from api.health import router as health_router
from api.auth import router as auth_router
from api.stocks import router as stocks_router
from api.wallet import router as wallet_router
from api.trading import router as trading_router
from api.websocket import router as ws_router, init_market_prices, send_market_updates
from api.agent import router as agent_router

app = FastAPI(title="Acciones Inteligentes API")

# Middleware CORS
# NOTA: allow_origins=["*"] es incompatible con allow_credentials=True (estándar HTTP).
# Se utiliza allow_origin_regex para admitir cualquier puerto en localhost / 127.0.0.1 durante desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_origin_regex=r"http://localhost(:\d+)?|http://127.0.0.1(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir Routers
app.include_router(health_router, tags=["Health"])
app.include_router(auth_router, tags=["Auth"])
app.include_router(stocks_router, tags=["Stocks"])
app.include_router(wallet_router, tags=["Wallet"])
app.include_router(trading_router, tags=["Trading"])
app.include_router(ws_router, tags=["WebSocket"])
app.include_router(agent_router, tags=["AI Agent"])

@app.on_event("startup")
async def startup_event():
    # Inicia el programador de tareas
    start_scheduler()
    # Inicializa simulación de mercado
    await init_market_prices()
    asyncio.create_task(send_market_updates())

@app.get("/")
def read_root():
    return {
        "message": "API de Acciones Inteligentes funcionando correctamente",
        "version": "2.0.0 (Modular)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)

