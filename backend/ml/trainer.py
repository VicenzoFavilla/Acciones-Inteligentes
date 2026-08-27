"""Entrenamiento del modelo local por ticker (XGBoost) con Validación Temporal y Backtesting.

Incluye TimeSeriesSplit (Walk-Forward CV), simulación de trading con comisiones,
cálculo de métricas financieras (Sharpe, MDD, Win Rate), DataLoader abstracto y calibración de umbrales.
"""

import os
from typing import Dict, Any, Tuple, Optional
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import f1_score

from ml.features import add_basic_features, make_supervised, get_X_y
from ml.data import DataLoader, get_data_loader
from ml.validation.walk_forward import TimeSeriesValidator
from ml.backtesting.engine import BacktestSimulator, BacktestConfig


def _get_xgb_factory(y_train: pd.Series, early_stopping_rounds: int | None = 40):
    """Crea una instancia de XGBClassifier regularizada y con balanceo dinámico."""
    pos = int((y_train == 1).sum())
    neg = int((y_train == 0).sum())
    spw = max(1.0, neg / max(1, pos))

    params = dict(
        n_estimators=600,
        learning_rate=0.03,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=3.0,
        min_child_weight=3,
        gamma=0.1,
        objective="binary:logistic",
        eval_metric="auc",
        scale_pos_weight=spw,
        random_state=42,
    )
    if early_stopping_rounds is not None:
        params["early_stopping_rounds"] = early_stopping_rounds

    return XGBClassifier(**params)


def train_and_backtest_pipeline(
    ticker: str = "AAPL",
    period: str = "2y",
    n_splits: int = 5,
    commission_pct: float = 0.001,
    data_loader: Optional[DataLoader] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Pipeline integral: Ingesta con DataLoader -> Features -> TimeSeries CV -> Backtesting -> Serialización.

    Returns:
        Tupla con (modelo_final_entrenado, reporte_completo_ml_y_financiero).
    """
    # 1. Ingesta extensible mediante DataLoader
    loader = data_loader or get_data_loader(source="yfinance")
    df_raw = loader.fetch_data(ticker=ticker, period=period)
    if df_raw.empty:
        raise ValueError(f"No se pudieron descargar datos para el ticker: {ticker}")

    df = add_basic_features(df_raw)
    df = make_supervised(df, up_pct=0.01)
    X, y = get_X_y(df)

    if len(X) < 40:
        raise ValueError(f"Datos insuficientes ({len(X)} filas) para validación temporal con {n_splits} folds.")

    # Ajustar n_splits si la muestra es pequeña
    actual_splits = min(n_splits, max(2, len(X) // 25))

    # 2. Calibración y Validación Temporal (Walk-Forward)
    validator = TimeSeriesValidator(n_splits=actual_splits)
    
    cv_summary = validator.evaluate_model(
        model_factory=lambda y_train: _get_xgb_factory(y_train, early_stopping_rounds=40),
        X=X,
        y=y,
        optimal_threshold=0.5,
    )

    # 3. Optimización del Umbral de Probabilidad en predicciones OOF
    oof_probs = cv_summary["oof_probabilities"]
    valid_mask = ~np.isnan(oof_probs)
    y_valid = y[valid_mask]
    probs_valid = oof_probs[valid_mask]

    best_thresh = 0.5
    best_f1 = 0.0
    for thresh in np.arange(0.35, 0.70, 0.02):
        score = f1_score(y_valid, (probs_valid >= thresh).astype(int), zero_division=0)
        if score > best_f1:
            best_f1 = score
            best_thresh = round(float(thresh), 2)

    # 4. Simulación de Backtesting sobre predicciones Out-Of-Fold
    df_evaluated = df.iloc[valid_mask].copy()
    model_signals = (probs_valid >= best_thresh).astype(int)

    backtester = BacktestSimulator(BacktestConfig(
        initial_capital=10_000.0,
        commission_pct=commission_pct,
        slippage_pct=0.0005,
        risk_free_rate=0.02,
    ))

    backtest_results = backtester.run(
        df=df_evaluated,
        signals=model_signals,
        price_col="Close",
    )

    # 5. Entrenamiento del Modelo Final (con todo el historial disponible)
    final_model = _get_xgb_factory(y, early_stopping_rounds=None)
    final_model.fit(X, y, verbose=False)
    final_model.optimal_threshold = float(best_thresh)

    # 6. Guardado en disco
    os.makedirs("models", exist_ok=True)
    model_path = os.path.join("models", f"{ticker}_buy_model_optimizado.pkl")
    joblib.dump(final_model, model_path)

    # Consolidación del Reporte
    report = {
        "ticker": ticker,
        "period": period,
        "optimal_threshold": best_thresh,
        "ml_validation_metrics": {
            "mean_accuracy": cv_summary["mean_accuracy"],
            "std_accuracy": cv_summary["std_accuracy"],
            "mean_f1": cv_summary["mean_f1"],
            "mean_auc": cv_summary["mean_auc"],
            "mean_precision": cv_summary["mean_precision"],
            "mean_recall": cv_summary["mean_recall"],
        },
        "financial_metrics": backtest_results["metrics"],
        "benchmark_metrics": backtest_results["benchmark_metrics"],
        "total_trades_executed": len(backtest_results["trades"]),
    }

    print(f"\n=======================================================")
    print(f"📊 REPORTE DE ENTRENAMIENTO & BACKTESTING: {ticker}")
    print(f"=======================================================")
    print(f"• CV TimeSeriesSplit ({actual_splits} folds) -> Acc: {report['ml_validation_metrics']['mean_accuracy']:.2%} (±{report['ml_validation_metrics']['std_accuracy']:.2%}) | AUC: {report['ml_validation_metrics']['mean_auc']:.3f}")
    print(f"• Umbral Óptimo Calibrado: {best_thresh} (F1 OOF: {best_f1:.3f})")
    print(f"-------------------------------------------------------")
    print(f"• Retorno Estrategia: {report['financial_metrics']['total_return_pct']}% vs Buy & Hold: {report['benchmark_metrics']['total_return_pct']}%")
    print(f"• Sharpe Ratio: {report['financial_metrics']['sharpe_ratio']} | Sortino: {report['financial_metrics']['sortino_ratio']}")
    print(f"• Max Drawdown: {report['financial_metrics']['max_drawdown_pct']}% (B&H MDD: {report['benchmark_metrics']['max_drawdown_pct']}%)")
    print(f"• Win Rate: {report['financial_metrics']['win_rate_pct']}% | Profit Factor: {report['financial_metrics']['profit_factor']}")
    print(f"• Operaciones Ejecutadas: {report['total_trades_executed']}")
    print(f"=======================================================\n")

    return final_model, report


def train_buy_model_optimizado(ticker="AAPL", periodo="1y"):
    """Función de compatibilidad con la API existente."""
    model, report = train_and_backtest_pipeline(ticker=ticker, period=periodo)
    accuracy = report["ml_validation_metrics"]["mean_accuracy"]
    return model, accuracy


if __name__ == "__main__":
    model, report = train_and_backtest_pipeline(ticker="AAPL", period="2y")
