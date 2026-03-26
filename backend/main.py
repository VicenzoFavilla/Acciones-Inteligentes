"""CLI del asesor de inversiones.

Permite consultar un ticker, ver datos básicos y usar modelos ML
(locales o globales) para obtener una recomendación.
"""

from services.stocks import get_stock_info, get_price_history
from ml.recomendacion import smart_recommendation, basic_recommendation
from ml.global_models import tickers_from_usage
from services.wallet import get_wallet, update_balance, add_transaction, buy_stock, sell_stock

from services.stocks import get_stock_info, get_price_history
from config.db import get_db
from pymongo import MongoClient
import joblib
import pandas as pd
import warnings
from auth_handler import get_password_hash, verify_password, create_access_token, decode_access_token
from fastapi import FastAPI, Query, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from services.scheduler import start_scheduler

# Silenciar ruidos de versión de scikit-learn
try:
    from sklearn.exceptions import InconsistentVersionWarning
    warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
except ImportError:
    pass


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = get_db()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.on_event("startup")
async def startup_event():
    # Inicia el programador de tareas para actualización de modelos
    start_scheduler()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
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
def predict_stock(ticker: str):
    ticker_up = ticker.upper()
    try:
        # Intentamos obtener la recomendación inteligente
        # Si el modelo no existe, smart_recommendation debería manejarlo,
        # pero lo envolvemos por seguridad.
        try:
            ml_res = smart_recommendation(ticker_up, registrar=True, model_type="global_xgb")
        except Exception as e:
            print(f"IA Error: {e}")
            ml_res = "Analizando..." # Valor por defecto si falla el .pkl

        info = get_stock_info(ticker_up)
        history_df = get_price_history(ticker_up, period="30d")
        
        # Procesamiento del historial (Asegurando que no sea nulo)
        history_list = []
        if history_df is not None and not history_df.empty:
            # Caso 1: Es un DataFrame (tiene .columns)
            if hasattr(history_df, "columns"):
                if isinstance(history_df.columns, pd.MultiIndex):
                    history_df.columns = history_df.columns.get_level_values(0)
                
                col = "Close" if "Close" in history_df.columns else "close"
                if col in history_df.columns:
                    history_list = [float(x) for x in history_df[col].dropna().tolist()]
            # Caso 2: Es una Series (acceso directo)
            else:
                history_list = [float(x) for x in history_df.dropna().tolist()]

        return {
            "ticker": ticker_up,
            "precio": info.get("price") if info else 0.0,
            "recomendacion": ml_res,
            "history": history_list
        }
    except Exception as e:
        print(f"Error general en predict: {e}")
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

    
@app.get("/crypto")
def get_crypto_list():
    import yfinance as yf
    top_cryptos = ["BTC-USD", "ETH-USD", "USDT-USD", "BNB-USD", "SOL-USD", "XRP-USD", "USDC-USD", "TRX-USD", "DOGE-USD", "ADA-USD"]
    
    lista_crypto = []
    
    name_map = {
        "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "USDT-USD": "TetherUS",
        "BNB-USD": "BNB", "SOL-USD": "Solana", "XRP-USD": "XRP",
        "USDC-USD": "USDC", "TRX-USD": "TRON", "DOGE-USD": "Dogecoin", "ADA-USD": "Cardano"
    }

    for ticker in top_cryptos:
        info = get_stock_info(ticker)
        if info:
            market_cap = 0
            try:
                stock_yf = yf.Ticker(ticker)
                inf = stock_yf.info
                if inf and "marketCap" in inf:
                    market_cap = inf["marketCap"]
            except Exception:
                pass
                
            lista_crypto.append({
                "ticker": ticker.replace("-USD", ""),
                "nombre": name_map.get(ticker, info.get("name", ticker.replace("-USD", ""))),
                "precio": info.get("price"),
                "variacion": info.get("change"),
                "color_green": (info.get("change") or 0) >= 0,
                "volumen": info.get("volume"),
                "market_cap": market_cap
            })
            
    return lista_crypto

@app.get("/market")
def get_market_list():
    import yfinance as yf
    top_stocks = ["TSLA", "AMZN", "MSFT", "GOOGL", "META", "NFLX", "NVDA", "AMD", "INTC", "BABA"]
    
    lista_market = []
    
    for ticker in top_stocks:
        info = get_stock_info(ticker)
        if info:
            market_cap = 0
            try:
                stock_yf = yf.Ticker(ticker)
                inf = stock_yf.info
                if inf and "marketCap" in inf:
                    market_cap = inf["marketCap"]
            except Exception:
                pass
                
            lista_market.append({
                "ticker": ticker,
                "nombre": info.get("name", ticker),
                "precio": info.get("price"),
                "variacion": info.get("change"),
                "color_green": (info.get("change") or 0) >= 0,
                "volumen": info.get("volume"),
                "market_cap": market_cap
            })
            
    return lista_market

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

from typing import Optional

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

# --- UTILS CRYPTO ---
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
