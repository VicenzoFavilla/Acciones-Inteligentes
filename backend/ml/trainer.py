"""Entrenamiento del modelo local por ticker (XGBoost).

Incluye validación temporal, early stopping y manejo de desbalance.
"""
import os
import joblib
import yfinance as yf
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score

from ml.features import add_basic_features, make_supervised, get_X_y


def _train_val_split_time(X, y, val_size=0.2):
    """Split temporal simple (80/20 por defecto)."""
    n = len(X)
    split = int(n * (1 - val_size))
    return X.iloc[:split], X.iloc[split:], y.iloc[:split], y.iloc[split:]


def _compute_scale_pos_weight(y):
    """Calcula scale_pos_weight según el desbalance observado."""
    pos = int((y == 1).sum())
    neg = int((y == 0).sum())
    if pos == 0:
        return 1.0
    return max(1.0, neg / max(1, pos))


def train_buy_model_optimizado(ticker="AAPL", periodo="1y"):
    """Entrena/actualiza un modelo XGBoost local para un ticker con regularización y calibración de umbral.

    Retorna (modelo, precisión en validación).
    """
    stock = yf.Ticker(ticker)
    df = stock.history(period=periodo)
    if df.empty:
        raise ValueError(f"No se pudo obtener datos para el ticker proporcionado. {ticker}")

    df = add_basic_features(df)
    df = make_supervised(df, up_pct=0.01)

    X, y = get_X_y(df)
    X_train, X_val, y_train, y_val = _train_val_split_time(X, y, val_size=0.2)

    scale_pos_weight = _compute_scale_pos_weight(y_train)

    # Hiperparámetros altamente optimizados y regularizados para prevenir sobreajuste en mercados ruidosos
    model = XGBClassifier(
        n_estimators=1000,
        learning_rate=0.03,        # Ritmo de aprendizaje ligeramente menor para un ajuste más suave
        max_depth=4,                # Profundidad reducida de 5 a 4 para prevenir memorización de ruido
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,              # Penalización L1 (lasso) para selección implícita de variables
        reg_lambda=3.0,             # Penalización L2 aumentada (ridge) para regularizar pesos
        min_child_weight=3,         # Exigir un mínimo de muestras por hoja para evitar divisiones frágiles
        gamma=0.1,                  # Mínima reducción de pérdida para realizar una partición
        objective="binary:logistic",
        eval_metric="auc",
        scale_pos_weight=scale_pos_weight,
        early_stopping_rounds=50,
        random_state=42,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    y_pred = model.predict(X_val)
    try:
        y_prob = model.predict_proba(X_val)[:, 1]
        auc = roc_auc_score(y_val, y_prob)
    except Exception:
        auc = float("nan")
        y_prob = None
    
    # Calibración del umbral óptimo maximizando el F1-Score en el set de validación
    best_thresh = 0.5
    best_f1 = 0.0
    if y_prob is not None:
        thresholds = np.arange(0.3, 0.7, 0.02)
        for thresh in thresholds:
            y_pred_thresh = (y_prob >= thresh).astype(int)
            f1 = f1_score(y_val, y_pred_thresh, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_thresh = thresh
    
    # Almacenar dinámicamente el umbral óptimo dentro del propio objeto del modelo
    model.optimal_threshold = float(best_thresh)

    acc = accuracy_score(y_val, y_pred)
    print(f"Precisión del modelo ({ticker}): {acc:.2f} | AUC: {auc:.3f} | Umbral F1 Óptimo: {best_thresh:.2f} (F1: {best_f1:.3f})")

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, f"models/{ticker}_buy_model_optimizado.pkl")

    return model, acc
