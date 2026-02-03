"""Auto-entrenamiento del MLP global a partir de interacciones guardadas.

Construye un dataset desde la colección acciones_usuario utilizando:
- y_true (si está disponible) como etiqueta real
- si no, usa y_pred (pseudolabel) para seguir aprendiendo de forma incremental

Guarda/actualiza el modelo GLOBAL_MLP en filesystem y MongoDB.
"""

from __future__ import annotations

import os
from typing import List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.exceptions import ConvergenceWarning
import warnings

from config.db import get_db
from config.alman_model import guardar_modelo_en_mongo
from ml.features import FEATURE_COLUMNS


def _load_or_init_pipeline(model_path: str = "models/global_mlp.pkl") -> Pipeline:
    if os.path.exists(model_path):
        try:
            pipe = joblib.load(model_path)
            # asegurar flags deseados si el modelo ya existía
            if hasattr(pipe, "named_steps") and "mlp" in pipe.named_steps:
                mlp = pipe.named_steps["mlp"]
                mlp.warm_start = True
                mlp.early_stopping = True
                mlp.validation_fraction = 0.1
                mlp.n_iter_no_change = 5
            return pipe
        except Exception:
            pass
    mlp = MLPClassifier(
        hidden_layer_sizes=(64, 32),
        activation="relu",
        solver="adam",
        alpha=1e-4,
        batch_size=128,
        learning_rate_init=1e-3,
        max_iter=30,
        warm_start=True,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=5,
        random_state=42,
    )
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("mlp", mlp),
    ])
    return pipe


def _dataset_from_db(limit: int = 1000) -> Tuple[pd.DataFrame, np.ndarray]:
    db = get_db()
    cursor = db.acciones_usuario.find({"features": {"$exists": True}}).sort("fecha", -1).limit(limit)
    X_list: List[List[float]] = []
    y_list: List[int] = []
    for doc in cursor:
        feats = doc.get("features") or {}
        # ordenar features según FEATURE_COLUMNS
        row = []
        valid = True
        for c in FEATURE_COLUMNS:
            if c in feats:
                row.append(float(feats[c]))
            else:
                valid = False
                break
        if not valid:
            continue
        y_true = doc.get("y_true")
        y_pred = doc.get("y_pred")
        if y_true is None and y_pred is None:
            continue
        label = int(y_true if y_true is not None else y_pred)
        X_list.append(row)
        y_list.append(label)
    if not X_list:
        raise ValueError("No hay suficientes muestras en BD para entrenar el MLP.")
    X = pd.DataFrame(X_list, columns=FEATURE_COLUMNS)
    y = np.array(y_list, dtype=int)
    # invertimos para que el orden temporal vaya ascendente (antiguo → reciente)
    X = X.iloc[::-1].reset_index(drop=True)
    y = y[::-1]
    return X, y


def train_mlp_from_db_recent(limit: int = 500, model_path: str = "models/global_mlp.pkl"):
    """Entrena/actualiza el MLP global usando las últimas N muestras de la BD.

    Usa y_true cuando está disponible; si no, usa y_pred como pseudo-etiqueta.
    Guarda en filesystem y en MongoDB bajo la clave GLOBAL_MLP.
    """
    X, y = _dataset_from_db(limit=limit)
    pipe = _load_or_init_pipeline(model_path)

    # Ajustes dinámicos para evitar warnings y acelerar convergencia
    try:
        n = len(X)
        if hasattr(pipe, "named_steps") and "mlp" in pipe.named_steps:
            mlp = pipe.named_steps["mlp"]
            mlp.batch_size = max(1, min(128, n))  # evitar clipping
            # iteraciones en función del tamaño (mantenerlo rápido en la CLI)
            mlp.max_iter = 50 if n >= 500 else 30
    except Exception:
        pass

    # Reducir ruido de convergencia en entrenamiento incremental
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        pipe.fit(X, y)

    os.makedirs("models", exist_ok=True)
    joblib.dump(pipe, model_path)
    guardar_modelo_en_mongo("GLOBAL_MLP", pipe)
    return pipe
