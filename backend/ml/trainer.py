"""Entrenamiento del modelo local por ticker (XGBoost).

Incluye validación temporal, early stopping y manejo de desbalance.
"""
import os
import joblib
import yfinance as yf
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, roc_auc_score

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


def train_buy_model_optimizado(ticker="AAPL", periodo="6m"):
    """Entrena/actualiza un modelo XGBoost local para un ticker.

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

    model = XGBClassifier(
        n_estimators=1000,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        gamma=0.0,
        objective="binary:logistic",
        eval_metric="auc",
        scale_pos_weight=scale_pos_weight,
        random_state=42,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
        early_stopping_rounds=50,
    )

    y_pred = model.predict(X_val)
    try:
        y_prob = model.predict_proba(X_val)[:, 1]
        auc = roc_auc_score(y_val, y_prob)
    except Exception:
        auc = float("nan")
    acc = accuracy_score(y_val, y_pred)
    print(f"Precisión del modelo ({ticker}): {acc:.2f} | AUC: {auc:.3f}")

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, f"models/{ticker}_buy_model_optimizado.pkl")

    return model, acc
