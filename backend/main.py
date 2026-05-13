import warnings
# Silenciar ruidos de scikit-learn y otras librerías (especialmente UserWarning por batch_size)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*batch_size.*")

from services.stocks import get_stock_info, get_price_history, get_sp500_tickers
from ml.recomendacion import smart_recommendation, basic_recommendation
from ml.global_models import tickers_from_usage
from services.wallet import get_wallet, update_balance, add_transaction, buy_stock, sell_stock
from services.orders import create_order, check_and_execute_orders
from config.db import get_db
from pymongo import MongoClient
import joblib
import pandas as pd
from auth_handler import get_password_hash, verify_password, create_access_token, decode_access_token
from fastapi import FastAPI, Query, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import random
from fastapi.security import OAuth2PasswordBearer
from services.scheduler import start_scheduler
from api.health import router as health_router
from core.logger import logger
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
# Silenciar ruidos de versión de scikit-learn
try:
    from sklearn.exceptions import InconsistentVersionWarning
    warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
except ImportError:
    pass


app = FastAPI()
app.include_router(health_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = get_db()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

market_prices = {}

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

async def init_market_prices():
    """Inicializa la lista de precios. Solo precarga unos pocos síncronamente
    y deja el resto para el ciclo de actualización de fondo.
    """
    all_tickers = get_sp500_tickers()
    # No cargamos 30 de forma secuencial, solo los 5 más populares para que el arranque sea rápido
    initial_tickers = all_tickers[:5]
    for t in initial_tickers:
        try:
            # Una carga mínima al inicio es aceptable
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
    """
    Obtiene precios reales de yfinance y los transmite vía WebSocket.
    Mantiene una cache local para reducir latencia y evitar bloqueos de yfinance.
    Cicla a través de todo el S&P 500 progresivamente.
    """
    all_tickers = get_sp500_tickers()
    idx = 0
    while True:
        await asyncio.sleep(5) # Aumentamos el intervalo para evitar rate limit de yfinance
        if manager.active_connections:
            # Seleccionamos el siguiente ticker de la lista global
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
                
                # Verificar órdenes cada vez que un precio cambia
                check_and_execute_orders(market_prices)
                
                await manager.broadcast({"type": "market_tick", "data": [update_msg]})

@app.websocket("/ws/market")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    # Inicia el programador de tareas para actualización de modelos
    start_scheduler()
    # Inicializa simulación de mercado
    await init_market_prices()
    asyncio.create_task(send_market_updates())

async def get_current_user(token: str = Depends(oauth2_scheme)):
    print(f"DEBUG: Token recibido: {token[:10]}...")
    payload = decode_access_token(token)
    if payload is None:
        print("DEBUG: Payload es None")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    print(f"DEBUG: Email en token: {email}")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db_conn = get_db()
    user = db_conn.users.find_one({"email": email})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@app.get("/")
def read_root():
    return {
        "message": "API de Acciones Inteligentes funcionando correctamente"
        }



@app.post("/user/watchlist/{ticker}")
def add_to_watchlist(ticker: str, current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    ticker_up = ticker.upper()
    db_conn.users.update_one(
        {"email": current_user["email"]},
        {"$addToSet": {"watchlist": ticker_up}}
    )
    return {"status": "success", "message": f"{ticker_up} agregado a favoritos"}

@app.delete("/user/watchlist/{ticker}")
def remove_from_watchlist(ticker: str, current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    ticker_up = ticker.upper()
    db_conn.users.update_one(
        {"email": current_user["email"]},
        {"$pull": {"watchlist": ticker_up}}
    )
    return {"status": "success", "message": f"{ticker_up} eliminado de favoritos"}

@app.get("/user/watchlist")
def get_watchlist(current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    user = db_conn.users.find_one({"email": current_user["email"]})
    watchlist = user.get("watchlist", [])
    
    lista_watchlist = []
    for ticker in watchlist:
        info = get_stock_info(ticker)
        if info:
            history_data = get_price_history(ticker, period="7d")
            history_list = []
            if history_data is not None and not history_data.empty:
                if hasattr(history_data, "columns"):
                    if isinstance(history_data.columns, pd.MultiIndex):
                        history_data.columns = history_data.columns.get_level_values(0)
                    if "Close" in history_data.columns:
                        history_list = history_data["Close"].tolist()
                else:
                    history_list = history_data.tolist()
            history_list = [x for x in history_list if str(x) != 'nan']
            lista_watchlist.append({
                "ticker": ticker,
                "nombre": info.get("name", ticker),
                "precio": info.get("price"),
                "variacion": info.get("change"),
                "color_green": (info.get("change") or 0) >= 0,
                "history": history_list
            })
    return {"status": "success", "watchlist": lista_watchlist}

@app.get("/user/{email}")
def get_user(email: str):
    db_conn = get_db()
    user = db_conn.users.find_one({"email": email})
    if user:
        return {"status": "success", "user": user}
    else:
        return {"status": "error", "message": "Usuario no encontrado"}


@app.post("/recomendacion")
def recomendacion(ticker: str):
    info = get_stock_info(ticker)
    if not info:
        return {"error": "No se pudo obtener información para el ticker"}
    nombre = info.get("name", ticker)
    recomendacion = basic_recommendation(info.get("change"))
    return {"ticker": ticker, "nombre": nombre, "recomendacion": recomendacion}


@app.get("/predict/{ticker}")
def predict_stock(ticker: str, period: str = "1mo"):
    ticker_up = ticker.upper()
    try:
        # Determinar intervalo basado en el periodo
        # Aumentamos la resolución para periodos cortos para evitar crash por falta de puntos (RSI, etc)
        if period == "1d":
            interval = "15m"  # ~28 puntos (mercado abierto)
        elif period == "5d":
            interval = "60m"  # ~35 puntos
        elif period == "15d":
            interval = "60m"  # ~105 puntos
        else:
            interval = "1d"   # Cierre diario para periodos largos
        
        # Intentamos obtener la recomendación inteligente
        try:
            ml_res = smart_recommendation(ticker_up, registrar=True, model_type="global_xgb")
        except Exception as e:
            logger.error(f"IA Error en predicción: {e}")
            ml_res = "Analizando..." # Valor por defecto si falla el .pkl

        info = get_stock_info(ticker_up)
        # Obtenemos historial con el periodo e intervalo solicitados
        history_df = get_price_history(ticker_up, period=period, interval=interval, full=True)
        
        # Procesamiento del historial OHLC
        history_list = []
        ohlc_list = []
        if history_df is not None and not history_df.empty:
            # Asegurar que las columnas sean simples (yfinance a veces devuelve MultiIndex)
            if hasattr(history_df.columns, "levels"):
                history_df.columns = history_df.columns.get_level_values(0)
            
            # Limpiar nombres de columnas para que sean consistentes
            history_df.columns = [str(c).lower() for c in history_df.columns]
            
            for index, row in history_df.iterrows():
                try:
                    o = float(row.get("open", 0))
                    h = float(row.get("high", 0))
                    l = float(row.get("low", 0))
                    c = float(row.get("close", 0))
                    v = float(row.get("volume", 0))
                    
                    if str(o) == 'nan' or str(c) == 'nan':
                        continue
                        
                    # Usamos formato ISO para incluir la hora si existe, asegurando unicidad
                    d = index.isoformat() if hasattr(index, "isoformat") else str(index)
                    ohlc_list.append({"open": o, "high": h, "low": l, "close": c, "volume": v, "date": d})
                    history_list.append(c)
                except Exception:
                    pass

        precio = info.get("price") if info else 0.0
        if str(precio) == 'nan':
            precio = 0.0

        return {
            "ticker": ticker_up,
            "precio": precio,
            "recomendacion": ml_res,
            "history": history_list,
            "ohlc": ohlc_list
        }
    except Exception as e:
        logger.error(f"Error general en predict_stock para {ticker}: {e}")
        # Retornamos algo básico para que Flutter no dé 'Error de conexión'
        return {
            "ticker": ticker_up, 
            "precio": 0.0, 
            "recomendacion": "Servidor en mantenimiento", 
            "history": []
        }


@app.get("/popular")
def get_popular_stocks():
    top_tickers = tickers_from_usage(limit=5)
    default_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]
    
    # Combinamos para tener siempre al menos 5 pero priorizando los usados
    seen = set()
    combined = []
    for t in top_tickers + default_list:
        if t not in seen:
            combined.append(t)
            seen.add(t)
        if len(combined) >= 5:
            break
    
    top_tickers = combined

    lista_populares = []
    for ticker in top_tickers:
        info = get_stock_info(ticker)
        if info:
            # Obtenemos los datos una sola vez
            history_data = get_price_history(ticker, period="7d")
            history_list = []

            if history_data is not None and not history_data.empty:
                # Caso 1: Es un DataFrame (tiene .columns)
                if hasattr(history_data, "columns"):
                    # Aplanamos si es MultiIndex
                    if isinstance(history_data.columns, pd.MultiIndex):
                        history_data.columns = history_data.columns.get_level_values(0)
                    
                    # Usamos "Close" con C mayúscula
                    if "Close" in history_data.columns:
                        history_list = history_data["Close"].tolist()
                
                # Caso 2: Es una Series (acceso directo)
                else:
                    history_list = history_data.tolist()

            # Limpiamos valores NaN para que JSON no falle
            history_list = [x for x in history_list if str(x) != 'nan']

            lista_populares.append({
                "ticker": ticker, # Corregido: antes decía 't'
                "nombre": info.get("name", ticker),
                "precio": info.get("price"),
                "variacion": info.get("change"),
                "color_green": (info.get("change") or 0) >= 0,
                "history": history_list # Usamos la lista que ya procesamos arriba
            })
            
    return lista_populares

    
@app.get("/market")
def get_market_list(search: Optional[str] = None, page: int = 1, page_size: int = 50):
    """Retorna la lista de acciones del mercado (S&P 500) con paginación."""
    all_tickers = get_sp500_tickers()
    
    # Filtrado por búsqueda si se provee
    if search:
        search = search.upper()
        filtered_tickers = [t for t in all_tickers if search in t]
    else:
        filtered_tickers = all_tickers
        
    total_items = len(filtered_tickers)
    total_pages = (total_items + page_size - 1) // page_size
    
    # Asegurar que la página esté en rango
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    target_tickers = filtered_tickers[start_idx:end_idx]
    
    lista_market = []
    
    def fetch_ticker_data(ticker):
        if ticker in market_prices:
            cached = market_prices[ticker]
            return {
                "ticker": ticker,
                "nombre": cached.get("name", ticker),
                "precio": cached.get("price"),
                "variacion": cached.get("change"),
                "color_green": (cached.get("change") or 0) >= 0,
                "volumen": cached.get("volume"),
                "market_cap": 0
            }
        else:
            info = get_stock_info(ticker)
            if info:
                return {
                    "ticker": ticker,
                    "nombre": info.get("name", ticker),
                    "precio": info.get("price"),
                    "variacion": info.get("change"),
                    "color_green": (info.get("change") or 0) >= 0,
                    "volumen": info.get("volume"),
                    "market_cap": 0
                }
            else:
                return {
                    "ticker": ticker,
                    "nombre": ticker,
                    "precio": 0.0,
                    "variacion": 0.0,
                    "color_green": True,
                    "volumen": 0,
                    "market_cap": 0
                }
                
    with ThreadPoolExecutor(max_workers=20) as executor:
        lista_market = list(executor.map(fetch_ticker_data, target_tickers))
            
    return {
        "items": lista_market,
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size
    }

@app.get("/feedback")
def save_user_decision(ticker: str, decision: str):
    db = get_db()
    result = db.acciones_usuario.update_one(
        {"ticker": ticker, "decision_usuario": None},
        {"$set": {"decision_usuario": decision}},
        sort=[("fecha", -1)]
    )
    return {"status": "success", "message": "Decisión guardada correctamente"}


from pydantic import BaseModel
import hashlib

# --- MODELO DE USUARIO ---
class User(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None

class PasswordChange(BaseModel):
    email: str
    old_password: str
    new_password: str

# --- RUTAS DE AUTH ---
@app.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    # Eliminar password del retorno por seguridad
    user_data = {k: v for k, v in current_user.items() if k != "password" and k != "_id"}
    return user_data

@app.post("/register")
def register(user: User):
    db_conn = get_db()
    
    # Verificar si existe
    if db_conn.users.find_one({"email": user.email}):
        return {"status": "error", "message": "El usuario ya existe"}
    
    # Hashear password y guardar (Usando auth_handler con bcrypt)
    new_user = {
        "email": user.email,
        "password": get_password_hash(user.password),
        "name": user.name or ""
    }
    db_conn.users.insert_one(new_user)
    return {"status": "success", "message": "Usuario registrado exitosamente"}

@app.post("/login")
def login(user: User):
    db_conn = get_db()
    
    existing_user = db_conn.users.find_one({"email": user.email})
    if not existing_user:
        return {"status": "error", "message": "Credenciales inválidas"}
    
    # Verificar contraseña (Soporta bcrypt)
    try:
        if verify_password(user.password, existing_user["password"]):
            access_token = create_access_token(data={"sub": user.email})
            return {
                "status": "success", 
                "message": "Login exitoso", 
                "access_token": access_token,
                "token_type": "bearer",
                "email": user.email,
                "name": existing_user.get("name", "")
            }
    except Exception:
        # Fallback para contraseñas antiguas con hashlib si es necesario (Opcional)
        # return {"status": "error", "message": "Por favor, restablezca su contraseña por motivos de seguridad."}
        pass

    return {"status": "error", "message": "Credenciales inválidas"}

@app.put("/user/update")
def update_user(user_update: UserUpdate, current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    
    # Preparamos los campos a actualizar
    update_data = {}
    if user_update.name is not None:
        update_data["name"] = user_update.name
        
    if not update_data:
        return {"status": "info", "message": "No hay datos para actualizar"}

    result = db_conn.users.update_one(
        {"email": current_user["email"]},
        {"$set": update_data}
    )
    
    return {"status": "success", "message": "Perfil actualizado correctamente"}

@app.post("/user/change_password")
def change_password(req: PasswordChange, current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    
    # Verificar contraseña anterior (Usando bcrypt)
    if not verify_password(req.old_password, current_user["password"]):
        return {"status": "error", "message": "La contraseña actual es incorrecta"}
        
    # Actualizar con la nueva (Usando bcrypt)
    db_conn.users.update_one(
        {"email": current_user["email"]},
        {"$set": {"password": get_password_hash(req.new_password)}}
    )
    
    return {"status": "success", "message": "Contraseña actualizada exitosamente"}


# --- RUTAS DE BILLETERA ---
@app.get("/wallet/info")
def wallet_info(current_user: dict = Depends(get_current_user)):
    wallet = get_wallet(current_user["email"])
    
    # Calcular P&L para cada activo y el total
    portfolio = wallet.get("portfolio", {})
    total_market_value = 0.0
    detailed_portfolio = []

    for ticker, info in portfolio.items():
        qty = info.get("quantity", 0)
        avg_price = info.get("average_price", 0.0)
        
        # Obtener precio actual
        current_data = get_stock_info(ticker)
        current_price = current_data.get("price", avg_price) if current_data else avg_price
        
        # Cálculos de rendimiento
        cost_basis = qty * avg_price
        market_value = qty * current_price
        pnl_abs = market_value - cost_basis
        pnl_pct = (pnl_abs / cost_basis * 100) if cost_basis > 0 else 0.0
        
        total_market_value += market_value
        
        detailed_portfolio.append({
            "ticker": ticker,
            "quantity": qty,
            "average_price": avg_price,
            "current_price": current_price,
            "pnl_abs": pnl_abs,
            "pnl_pct": pnl_pct,
            "market_value": market_value
        })

    wallet["portfolio_details"] = detailed_portfolio
    wallet["total_equity"] = wallet["balance"] + total_market_value
    
    # Limpiar ID de Mongo para el retorno
    if "_id" in wallet:
        del wallet["_id"]
    return {"status": "success", "wallet": wallet}

@app.post("/wallet/deposit")
def deposit_funds(amount: float, current_user: dict = Depends(get_current_user)):
    if amount <= 0:
        return {"status": "error", "message": "El monto debe ser positivo"}
    
    success = update_balance(current_user["email"], amount)
    if success:
        return {"status": "success", "message": f"Se han depositado ${amount} correctamente."}
    return {"status": "error", "message": "No se pudo actualizar el saldo."}

@app.get("/wallet/portfolio")
def portfolio_info(current_user: dict = Depends(get_current_user)):
    wallet = get_wallet(current_user["email"])
    return {"status": "success", "portfolio": wallet.get("portfolio", {})}

# --- RUTAS DE TRADING ---
@app.post("/trade/buy")
def trade_buy(ticker: str, quantity: int, current_user: dict = Depends(get_current_user)):
    if quantity <= 0:
        return {"status": "error", "message": "La cantidad debe ser mayor a 0"}
    
    ticker_up = ticker.upper()
    info = get_stock_info(ticker_up)
    if not info or not info.get("price"):
        return {"status": "error", "message": f"No se pudo obtener el precio para {ticker_up}"}
    
    price = info["price"]
    success, message = buy_stock(current_user["email"], ticker_up, quantity, price)
    
    if success:
        return {"status": "success", "message": message, "price_paid": price}
    return {"status": "error", "message": message}

@app.post("/trade/sell")
def trade_sell(ticker: str, quantity: int, current_user: dict = Depends(get_current_user)):
    if quantity <= 0:
        return {"status": "error", "message": "La cantidad debe ser mayor a 0"}
    
    ticker_up = ticker.upper()
    info = get_stock_info(ticker_up)
    if not info or not info.get("price"):
        return {"status": "error", "message": f"No se pudo obtener el precio para {ticker_up}"}
    
    price = info["price"]
    success, message = sell_stock(current_user["email"], ticker_up, quantity, price)
    
    if success:
        return {"status": "success", "message": message, "price_sold": price}
    return {"status": "error", "message": message}

# --- RUTAS DE ÓRDENES ---
@app.post("/trade/order")
def place_order(ticker: str, quantity: int, target_price: float, side: str, order_type: str = "limit", current_user: dict = Depends(get_current_user)):
    if quantity <= 0 or target_price <= 0:
        return {"status": "error", "message": "Cantidad y precio deben ser mayores a 0"}
    
    if side not in ["buy", "sell"]:
        return {"status": "error", "message": "Side debe ser 'buy' o 'sell'"}
        
    if order_type not in ["limit", "stop_loss", "take_profit"]:
        return {"status": "error", "message": "Tipo de orden no válido"}
        
    order_id = create_order(current_user["email"], ticker.upper(), quantity, target_price, side, order_type)
    return {"status": "success", "message": f"Orden {order_type} de {side} para {ticker} creada", "order_id": order_id}

@app.post("/wallet/transfer")
def transfer_funds_endpoint(from_wallet: str, to_wallet: str, amount: float, current_user: dict = Depends(get_current_user)):
    from services.wallet import transfer_between_subwallets
    success, message = transfer_between_subwallets(current_user["email"], from_wallet, to_wallet, amount)
    if success:
        return {"status": "success", "message": message}
    return {"status": "error", "message": message}

@app.get("/user/orders")
def get_user_orders(current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    orders = list(db_conn.orders.find({"email": current_user["email"]}).sort("timestamp", -1))
    for o in orders:
        if "_id" in o:
            o["_id"] = str(o["_id"])
    return {"status": "success", "orders": orders}

@app.get("/wallet/history")
def transaction_history(current_user: dict = Depends(get_current_user)):
    db = get_db()
    transactions = list(db.transactions.find({"email": current_user["email"]}).sort("timestamp", -1))
    for t in transactions:
        if "_id" in t:
            t["_id"] = str(t["_id"])
    return {"status": "success", "transactions": transactions}


class DecisionRequest(BaseModel):
    ticker: str
    decision: str

@app.post("/decision")
def save_decision(req: DecisionRequest):
    """Guarda la decisión del usuario (Comprar/No Comprar) en la BD."""
    db = get_db()
    
    # Actualizamos el registro más reciente de este ticker que no tenga decisión
    # Esto asume que el usuario acaba de pedir una predicción.
    result = db.acciones_usuario.update_one(
        {"ticker": req.ticker, "decision_usuario": None},
        {"$set": {"decision_usuario": req.decision}}
    )
    
    if result.modified_count == 0:
        # Si no encontró uno pendiente, quizás es un registro nuevo directo (opcional)
        # Por ahora devolvemos mensaje informativo
        return {"status": "info", "message": "No se encontró predicción pendiente o ya fue actualizada."}
        
    return {"status": "success", "message": "Decisión registrada correctamente."}

def main():
    """Bucle principal de interacción por consola."""
    print("=== ASESOR DE INVERSIONES ===")
    while True:
        ticker = input("\nIngresa el símbolo de una acción (o 'salir'): ").strip()
        if not ticker:
            continue
        if ticker.lower() == "salir":
            break
        ticker = ticker.upper()

        try:
            info = get_stock_info(ticker)
            if not info:
                print(f"No se pudo obtener información para el ticker: {ticker}")
                continue

            nombre = info.get("name", ticker)
            print(f"\n✓ {nombre} ({ticker})")
            print(f"Precio actual: ${info.get('price')}")
            print(f"Variación diaria: {info.get('change')}%")
            print(f"Volumen: {info.get('volume')}")

            ver_grafico = input("\n¿Ver gráfico de últimos 30 días? (s/n): ").strip().lower()
            if ver_grafico == "s":
                serie = get_price_history(ticker, period="30d")
                if serie is not None and not serie.empty:
                    try:
                        import matplotlib.pyplot as plt
                        serie.plot(title=f"Precio de cierre - últimos 30 días ({ticker})")
                        plt.ylabel("Precio ($)")
                        plt.grid(True)
                        plt.tight_layout()
                        plt.show()
                    except Exception as e:
                        print(f"No se pudo mostrar el gráfico: {e}")

            recomendacion = basic_recommendation(info.get("change"))
            print(f"\nRecomendación básica: {recomendacion}")

            usar_ml = input("\n¿Quieres usar Machine Learning para predecir si conviene comprar? (s/n): ").strip().lower()
            if usar_ml == "s":
                print("\nSelecciona modelo ML:")
                print("  1) Local XGBoost (por ticker)")
                print("  2) Global XGBoost")
                print("  3) Global MLP (red neuronal)")
                opcion = input("Opción [1/2/3]: ").strip()
                if opcion == "2":
                    model_type = "global_xgb"
                elif opcion == "3":
                    model_type = "global_mlp"
                else:
                    model_type = "local_xgb"

                umbral_txt = input("Umbral de probabilidad para 'comprar' [0.5 por defecto]: ").strip()
                try:
                    prob_threshold = float(umbral_txt) if umbral_txt else 0.5
                except ValueError:
                    prob_threshold = 0.5

                ml_recomendacion = smart_recommendation(
                    ticker,
                    registrar=True,
                    model_type=model_type,
                    prob_threshold=prob_threshold,
                )
                print(f"\nRecomendación con Machine Learning: {ml_recomendacion}")

                decision = input("¿Qué hiciste? (compré / no compré / skip): ").strip().lower()
                if decision in ["compré", "no compré"]:
                    db = get_db()
                    db.acciones_usuario.update_one(
                        {"ticker": ticker, "decision_usuario": None},
                        {"$set": {"decision_usuario": decision}}
                    )
        except Exception as e:
            print(f"Ocurrió un error al procesar el ticker {ticker}: {e}")
            continue


if __name__ == "__main__":
    main()
