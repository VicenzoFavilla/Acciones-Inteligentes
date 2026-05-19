"""Modelos globales entrenados con múltiples tickers (XGB y MLP).

Pensado para actualizarse de forma incremental sin bloquear la CLI:
se ejecuta mediante scripts/update_models.py.
"""

import os
from typing import List, Tuple

import numpy as np
import joblib
import yfinance as yf
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import f1_score
from xgboost import XGBClassifier
import warnings
from sklearn.exceptions import ConvergenceWarning

from ml.features import add_basic_features, make_supervised, get_X_y
from config.alman_model import guardar_modelo_en_mongo
from config.db import get_db
from config.settings import settings


def build_dataset_for_tickers(tickers: List[str], period: str = "2y") -> Tuple[pd.DataFrame, pd.Series]:
    """Concatena datasets de varios tickers en un único X, y."""
    frames = []
    for t in tickers:
        try:
            df = yf.Ticker(t).history(period=period)
            if df is None or df.empty:
                continue
            df = add_basic_features(df)
            df = make_supervised(df, up_pct=0.01)
            if df.empty:
                continue
            X, y = get_X_y(df)
            X = X.copy()
            X["ticker"] = t
            X["y"] = y.values
            frames.append(X)
        except Exception:
            continue
    if not frames:
        raise ValueError("No se pudo construir dataset con los tickers indicados.")
    data = pd.concat(frames, axis=0, ignore_index=True)
    y = data.pop("y")
    data.drop(columns=["ticker"], inplace=True)
    return data, y


def train_or_update_xgb_global(tickers: List[str], period: str = "2y", model_path: str = None):
    """Entrena o continúa entrenando un XGBoost global con regularización y calibración de umbral, y lo guarda en FS+Mongo."""
    if model_path is None:
        model_path = os.path.join(settings.MODEL_DIR, "global_xgb.pkl")
    X, y = build_dataset_for_tickers(tickers, period=period)

    # Split temporal simple
    n = len(X)
    split = int(n * 0.8)
    X_train, X_val = X.iloc[:split], X.iloc[split:]
    y_train, y_val = y.iloc[:split], y.iloc[split:]

    pos = int((y_train == 1).sum())
    neg = int((y_train == 0).sum())
    spw = max(1.0, neg / max(1, pos))

    # Parámetros altamente regularizados para mitigar el sobreajuste
    params = dict(
        n_estimators=1000,
        learning_rate=0.03,        # Ritmo de aprendizaje menor
        max_depth=4,                # Profundidad de árbol reducida
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,              # Regularización L1
        reg_lambda=3.0,             # Regularización L2
        min_child_weight=3,
        gamma=0.1,
        objective="binary:logistic",
        eval_metric="auc",
        scale_pos_weight=spw,
        early_stopping_rounds=50,
        random_state=42,
    )

    xgb = XGBClassifier(**params)

    # Warm-start desde modelo previo si existe
    prev_booster = None
    if os.path.exists(model_path):
        try:
            prev_model = joblib.load(model_path)
            prev_booster = prev_model.get_booster()
        except Exception:
            prev_booster = None

    xgb.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
        xgb_model=prev_booster,
    )

    # Calibración del umbral óptimo maximizando el F1-Score en el set de validación
    best_thresh = 0.5
    best_f1 = 0.0
    try:
        y_prob = xgb.predict_proba(X_val)[:, 1]
        thresholds = np.arange(0.3, 0.7, 0.02)
        for thresh in thresholds:
            y_pred_thresh = (y_prob >= thresh).astype(int)
            f1 = f1_score(y_val, y_pred_thresh, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_thresh = thresh
    except Exception:
        pass

    # Almacenar dinámicamente el umbral óptimo dentro del propio objeto del modelo
    xgb.optimal_threshold = float(best_thresh)
    print(f"[INFO] Modelo XGBoost global entrenado. Umbral F1 Óptimo: {best_thresh:.2f} (F1: {best_f1:.3f})")

    os.makedirs("models", exist_ok=True)
    joblib.dump(xgb, model_path)
    guardar_modelo_en_mongo("GLOBAL_XGB", xgb)
    return xgb


def train_or_update_mlp_global(tickers: List[str], period: str = "2y", model_path: str = None):
    """Entrena o continúa entrenando un MLP global (pipeline con scaler)."""
    if model_path is None:
        model_path = os.path.join(settings.MODEL_DIR, "global_mlp.pkl")
    X, y = build_dataset_for_tickers(tickers, period=period)

    # pipeline con estandarización + MLP warm_start
    if os.path.exists(model_path):
        try:
            pipe = joblib.load(model_path)
            # continuará entrenamiento al llamar fit, por warm_start=True
        except Exception:
            pipe = None
    else:
        pipe = None

    if pipe is None:
        # Ajustamos batch_size inicial; fit lo sobreescribirá abajo si es necesario
        mlp = MLPClassifier(hidden_layer_sizes=(64, 32), activation="relu", solver="adam", alpha=1e-4,
                            batch_size="auto", learning_rate_init=1e-3, max_iter=50, warm_start=True, random_state=42)
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("mlp", mlp),
        ])
    else:
        # asegurar warm_start activo y ajustar batch_size según datos actuales
        mlp = pipe.named_steps.get("mlp")
        if mlp:
            mlp.warm_start = True
            mlp.batch_size = min(128, len(X))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        warnings.simplefilter("ignore", UserWarning)
        pipe.fit(X, y)

    os.makedirs("models", exist_ok=True)
    joblib.dump(pipe, model_path)
    guardar_modelo_en_mongo("GLOBAL_MLP", pipe)
    return pipe


def tickers_from_usage(limit: int = 20) -> List[str]:
    """Obtiene tickers más consultados desde la colección modelos_uso.
    Si la BD está vacía, devuelve una lista por defecto para permitir el entrenamiento.
    """
    db = get_db()
    DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]
    try:
        cur = db.modelos_uso.find({}).sort("ultima_vez", -1).limit(limit)
        tks = [d.get("ticker") for d in cur if d.get("ticker")]
        if not tks:
            return DEFAULT_TICKERS
        return list({t for t in tks})  # únicos
    except Exception:
        return DEFAULT_TICKERS
