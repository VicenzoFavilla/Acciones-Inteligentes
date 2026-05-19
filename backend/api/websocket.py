import asyncio
import random
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from services.stocks import get_stock_info, get_sp500_tickers
from services.orders import check_and_execute_orders

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()
market_prices = {}

async def init_market_prices():
    """Inicializa la lista de precios."""
    all_tickers = get_sp500_tickers()
    initial_tickers = all_tickers[:5]
    for t in initial_tickers:
        try:
            info = get_stock_info(t)
            if info and info.get("price"):
                market_prices[t] = {
                    "price": info.get("price"),
                    "change": info.get("change") or 0.0,
                    "name": info.get("name", t),
                    "volume": info.get("volume", 0)
                }
        except Exception:
            pass

async def send_market_updates():
    """Obtiene precios reales y los transmite vía WebSocket."""
    all_tickers = get_sp500_tickers()
    idx = 0
    while True:
        await asyncio.sleep(5)
        if manager.active_connections:
            t = all_tickers[idx % len(all_tickers)]
            idx += 1
            info = get_stock_info(t)
            if info:
                price = info["price"]
                change = info["change"]
                market_prices[t] = {
                    "price": price,
                    "change": change,
                    "name": info.get("name", t),
                    "volume": info.get("volume", 0)
                }
                update_msg = {
                    "ticker": t,
                    "precio": price,
                    "variacion": change,
                    "color_green": (change or 0.0) >= 0
                }
                check_and_execute_orders(market_prices)
                await manager.broadcast({"type": "market_tick", "data": [update_msg]})

@router.websocket("/ws/market")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
