"""Validación de Series Temporales con TimeSeriesSplit y Walk-Forward Validation."""

from typing import Dict, Any, List, Generator, Tuple, Callable
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, precision_score, recall_score


class TimeSeriesValidator:
    """Validador para modelos de predicción financiera respetando la causalidad temporal."""

    def __init__(self, n_splits: int = 5, max_train_size: int | None = None):
        self.n_splits = n_splits
        self.max_train_size = max_train_size
        self.tscv = TimeSeriesSplit(n_splits=n_splits, max_train_size=max_train_size)

    def split(
        self, X: pd.DataFrame, y: pd.Series | None = None
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """Genera índices de entrenamiento y prueba respetando el orden temporal."""
        return self.tscv.split(X, y)

    def evaluate_model(
        self,
        model_factory: Callable[[pd.Series], Any],
        X: pd.DataFrame,
        y: pd.Series,
        optimal_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Ejecuta Cross-Validation temporal evaluando métricas OOF (Out-Of-Fold).

        Args:
            model_factory: Función o clase instanciable para crear un modelo limpio por fold.
            X: Matriz de características.
            y: Vector objetivo.
            optimal_threshold: Umbral de decisión para clasificación binaria.

        Returns:
            Dict con métricas promedio, desviación estándar y desglose por fold.
        """
        fold_results: List[Dict[str, float]] = []
        oof_predictions = np.full(len(y), np.nan)
        oof_probabilities = np.full(len(y), np.nan)

        for fold, (train_idx, val_idx) in enumerate(self.split(X, y), start=1):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # Instanciar y ajustar modelo fresco para el fold
            model = model_factory(y_train=y_train)
            
            # Ajuste con early stopping si el estimador lo soporta
            if hasattr(model, "fit"):
                try:
                    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
                except TypeError:
                    model.fit(X_train, y_train)

            # Probabilidades y Predicciones
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(X_val)[:, 1]
                preds = (probs >= optimal_threshold).astype(int)
                oof_probabilities[val_idx] = probs
            else:
                preds = model.predict(X_val)
                probs = preds.astype(float)
                oof_probabilities[val_idx] = probs

            oof_predictions[val_idx] = preds

            # Métricas del Fold
            acc = accuracy_score(y_val, preds)
            f1 = f1_score(y_val, preds, zero_division=0)
            prec = precision_score(y_val, preds, zero_division=0)
            rec = recall_score(y_val, preds, zero_division=0)
            
            try:
                auc = roc_auc_score(y_val, probs) if len(np.unique(y_val)) > 1 else np.nan
            except Exception:
                auc = np.nan

            fold_results.append({
                "fold": fold,
                "train_size": len(train_idx),
                "val_size": len(val_idx),
                "accuracy": acc,
                "f1_score": f1,
                "precision": prec,
                "recall": rec,
                "auc": auc,
            })

        df_folds = pd.DataFrame(fold_results)

        summary = {
            "n_splits": self.n_splits,
            "mean_accuracy": round(float(df_folds["accuracy"].mean()), 4),
            "std_accuracy": round(float(df_folds["accuracy"].std()), 4),
            "mean_f1": round(float(df_folds["f1_score"].mean()), 4),
            "mean_auc": round(float(df_folds["auc"].dropna().mean()), 4) if not df_folds["auc"].dropna().empty else 0.0,
            "mean_precision": round(float(df_folds["precision"].mean()), 4),
            "mean_recall": round(float(df_folds["recall"].mean()), 4),
            "folds_detail": fold_results,
            "oof_predictions": oof_predictions,
            "oof_probabilities": oof_probabilities,
        }

        return summary
