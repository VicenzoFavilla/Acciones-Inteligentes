"""CLI del asesor de inversiones.

Permite consultar un ticker, ver datos básicos y usar modelos ML
(locales o globales) para obtener una recomendación.
"""

from services.stocks import get_stock_info, get_price_history
from ml.recomendacion import smart_recommendation, basic_recommendation
from config.db import get_db
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import joblib


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client= MongoClient("mongodb://localhost:27017")
db = client["acciones"]

@app.get("/")
def read_root():
    return {
        "message": "API de Acciones Inteligentes funcionando correctamente"
        }


@app.get("/user/{email}")
def get_user(email: str):
    user = db.users.find_one({"email": email})
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
def predict(ticker: str, model: str = "local_xgb", threshold: float = 0.5):
    res = smart_recommendation(ticker=ticker, model_type=model, prob_threshold=threshold)
    info = get_stock_info(ticker.upper())
    
    # Obtener historial para la gráfica
    history_series = get_price_history(ticker.upper(), period="1mo")
    history_data = []
    if history_series is not None:
        history_data = history_series.tolist()

    return {
        "ticker": ticker.upper(),
        "nombre": info.get("name", ticker) if info else ticker,
        "recomendacion": res,
        "precio": info.get("price") if info else None,
        "variacion": info.get("change") if info else None,
        "volumen": info.get("volume") if info else None,
        "history": history_data
    }

from pydantic import BaseModel
import hashlib

# --- MODELO DE USUARIO ---
class User(BaseModel):
    email: str
    password: str

# --- UTILS CRYPTO ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# --- RUTAS DE AUTH ---
@app.post("/register")
def register(user: User):
    db_conn = get_db()
    
    # Verificar si existe
    if db_conn.users.find_one({"email": user.email}):
        return {"status": "error", "message": "El usuario ya existe"}
    
    # Hashear password y guardar
    new_user = {
        "email": user.email,
        "password": hash_password(user.password)
    }
    db_conn.users.insert_one(new_user)
    return {"status": "success", "message": "Usuario registrado exitosamente"}

@app.post("/login")
def login(user: User):
    db_conn = get_db()
    
    existing_user = db_conn.users.find_one({"email": user.email})
    if not existing_user:
        return {"status": "error", "message": "Credenciales inválidas"}
    
    if existing_user["password"] == hash_password(user.password):
        return {"status": "success", "message": "Login exitoso", "email": user.email}
    else:
        return {"status": "error", "message": "Credenciales inválidas"}


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
