"""Recomendaciones básicas y con ML (locales y globales).

Este módulo expone:
- basic_recommendation: regla simple basada en variación diaria.
- smart_recommendation: predicción ML con soporte a modelos locales y globales.

Alinea la ingeniería de variables entre entrenamiento y predicción para evitar
desajustes, y limpia los textos con acentos correctos.
"""

from datetime import datetime
import joblib
import yfinance as yf
import pandas as pd

from config.db import get_db
from config.alman_model import guardar_modelo_en_mongo, cargar_modelo_de_mongo
from ml.trainer import train_buy_model_optimizado
from ml.features import add_basic_features, make_supervised, get_X_y, FEATURE_COLUMNS


def basic_recommendation(change: float | None) -> str:
    """Regla simple según variación diaria del precio.

    - change < -2%: sugerir comprar
    - -2% <= change <= 2%: sugerir esperar
    - change > 2%: sugerir esperar una corrección
    """
    if change is None:
        return "No hay suficiente información para recomendar."

    if change < -2:
        return "El precio bajó bastante hoy. Podría ser un buen momento para comprar."
    elif -2 <= change <= 2:
        return "El precio está estable. Podés observar unos días más."
    else:
        return "El precio subió bastante. Tal vez sea mejor esperar una baja."


def _load_global_model(kind: str):
    """Carga el modelo global desde MongoDB (preferente) o filesystem.

    kind: "GLOBAL_XGB" o "GLOBAL_MLP"
    """
    model = cargar_modelo_de_mongo(kind)
    if model is not None:
        return model
    try:
        path = "models/global_xgb.pkl" if kind == "GLOBAL_XGB" else "models/global_mlp.pkl"
        return joblib.load(path)
    except Exception:
        return None


def smart_recommendation(
    ticker: str = "AAPL",
    registrar: bool = False,
    model_type: str = "local_xgb",
    prob_threshold: float = 0.5,
) -> str:
    """Genera una recomendación usando ML.

    Parámetros:
      - ticker: símbolo a evaluar.
      - registrar: si True, guarda la recomendación en MongoDB.
      - model_type:
          * "local_xgb": modelo específico por ticker (entrena si no existe).
          * "global_xgb": modelo XGBoost global (varios tickers).
          * "global_mlp": red neuronal MLP global (varios tickers).
      - prob_threshold: umbral de probabilidad para recomendar "comprar".
    """
    db = get_db()
    model = None
    accuracy = None

    # Selección/carga de modelo
    if model_type == "local_xgb":
        model = cargar_modelo_de_mongo(ticker)
        if model is None:
            try:
                model, accuracy = train_buy_model_optimizado(ticker)
            except Exception as e:
                return f"No se pudo entrenar el modelo para {ticker}. Error: {e}"
            guardar_modelo_en_mongo(ticker, model)
    elif model_type == "global_xgb":
        model = _load_global_model("GLOBAL_XGB")
        if model is None:
            return "No hay modelo global XGB disponible. Ejecuta scripts/update_models.py."
    elif model_type == "global_mlp":
        model = _load_global_model("GLOBAL_MLP")
        if model is None:
            return "No hay modelo global MLP disponible. Ejecuta scripts/update_models.py."
    else:
        return f"Tipo de modelo no soportado: {model_type}"

    # Datos → features alineadas
    stock = yf.Ticker(ticker)
    data = stock.history(period="2y")
    if data.empty or len(data) < 20:
        return "No hay suficientes datos para predecir."

    df = add_basic_features(data.copy())
    df = make_supervised(df, up_pct=0.01)
    df.dropna(inplace=True)
    if df.empty:
        return "No hay suficientes datos válidos después del procesamiento."

    row = df.iloc[-1]
    row_df = pd.DataFrame([row[FEATURE_COLUMNS]])

    # Predicción (probabilidad si es posible)
    try:
        if hasattr(model, "predict_proba"):
            prob = float(model.predict_proba(row_df)[:, 1][0])
            pred = 1 if prob >= prob_threshold else 0
        else:
            pred = int(model.predict(row_df)[0])
            prob = None
    except Exception as e:
        return f"Error al predecir: {e}"

    recomendacion = "comprar" if pred == 1 else "no_comprar"

    if registrar:
        # persistimos también el vector de features usado para permitir auto-entrenamiento
        feature_values = {col: float(row[col]) for col in FEATURE_COLUMNS}
        db.acciones_usuario.insert_one({
            "ticker": ticker,
            "fecha": datetime.now(),
            "precio": float(row["Close"]),
            "recomendacion_ml": recomendacion,
            "probabilidad": prob,
            "y_pred": int(pred),
            "features": feature_values,
            "decision_usuario": None,
            "modelo_usado": model_type,
            "umbral": prob_threshold,
        })

        # entrenamiento incremental del MLP global a partir de la BD (pseudo-etiquetas si no hay y_true)
        try:
            from ml.self_training import train_mlp_from_db_recent
            train_mlp_from_db_recent(limit=500)
        except Exception:
            # si falla, no interrumpir la CLI
            pass

    # Registrar uso del modelo (por ticker consultado)
    db.modelos_uso.update_one(
        {"ticker": ticker},
        {"$inc": {"veces_usado": 1}, "$set": {"ultima_vez": datetime.now()}},
        upsert=True,
    )

    if pred == 1:
        return "El modelo predice que el precio subirá. Podría ser buen momento para comprar."
    else:
        return "El modelo predice que el precio bajará. Mejor esperar."
