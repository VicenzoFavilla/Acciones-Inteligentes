"""Modelos globales entrenados con múltiples tickers (XGB y MLP).

Pensado para actualizarse de forma incremental sin bloquear la CLI:
se ejecuta mediante scripts/update_models.py.
"""

import os
from typing import List, Tuple

import joblib
import yfinance as yf
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier

from ml.features import add_basic_features, make_supervised, get_X_y
from config.alman_model import guardar_modelo_en_mongo
from config.db import get_db


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


def train_or_update_xgb_global(tickers: List[str], period: str = "2y", model_path: str = "models/global_xgb.pkl"):
    """Entrena o continúa entrenando un XGBoost global, y lo guarda en FS+Mongo."""
    X, y = build_dataset_for_tickers(tickers, period=period)

    # Split temporal simple
    n = len(X)
    split = int(n * 0.8)
    X_train, X_val = X.iloc[:split], X.iloc[split:]
    y_train, y_val = y.iloc[:split], y.iloc[split:]

    pos = int((y_train == 1).sum())
    neg = int((y_train == 0).sum())
    spw = max(1.0, neg / max(1, pos))

    params = dict(
        n_estimators=1000,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        objective="binary:logistic",
        eval_metric="auc",
        scale_pos_weight=spw,
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
        early_stopping_rounds=50,
        verbose=False,
        xgb_model=prev_booster,
    )

    os.makedirs("models", exist_ok=True)
    joblib.dump(xgb, model_path)
    guardar_modelo_en_mongo("GLOBAL_XGB", xgb)
    return xgb


def train_or_update_mlp_global(tickers: List[str], period: str = "2y", model_path: str = "models/global_mlp.pkl"):
    """Entrena o continúa entrenando un MLP global (pipeline con scaler)."""
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
        mlp = MLPClassifier(hidden_layer_sizes=(64, 32), activation="relu", solver="adam", alpha=1e-4,
                            batch_size=128, learning_rate_init=1e-3, max_iter=50, warm_start=True, random_state=42)
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("mlp", mlp),
        ])
    else:
        # asegurar warm_start activo
        if hasattr(pipe.named_steps.get("mlp"), "warm_start"):
            pipe.named_steps["mlp"].warm_start = True

    pipe.fit(X, y)

    os.makedirs("models", exist_ok=True)
    joblib.dump(pipe, model_path)
    guardar_modelo_en_mongo("GLOBAL_MLP", pipe)
    return pipe


def tickers_from_usage(limit: int = 20) -> List[str]:
    """Obtiene tickers más consultados desde la colección modelos_uso."""
    db = get_db()
    try:
        cur = db.modelos_uso.find({}).sort("ultima_vez", -1).limit(limit)
        tks = [d.get("ticker") for d in cur if d.get("ticker")]
        return list({t for t in tks})  # únicos
    except Exception:
        return ["AAPL", "KO", "NVDA"]
