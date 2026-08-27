"""Script de ejecución diaria para MLOps: Ingesta, Inferencia, Backtesting y Guardado de Métricas."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any

# Asegurar path raíz del backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import logger
from ml.trainer import train_and_backtest_pipeline
from ml.data import get_data_loader


def run_daily_pipeline(
    tickers: List[str],
    period: str = "2y",
    output_dir: str = "reports",
    save_to_mongo: bool = True,
) -> Dict[str, Any]:
    """Ejecuta el pipeline automatizado diario para una lista de tickers."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    logger.info(f"Iniciando pipeline diario de ML para {len(tickers)} activos: {tickers}")

    pipeline_report: Dict[str, Any] = {
        "execution_date": datetime.now(timezone.utc).isoformat(),
        "period": period,
        "processed_tickers": [],
        "failed_tickers": [],
        "summary": {},
    }

    loader = get_data_loader("yfinance")

    for ticker in tickers:
        ticker = ticker.strip().upper()
        if not ticker:
            continue
        try:
            logger.info(f"Procesando ticker: {ticker}...")
            model, report = train_and_backtest_pipeline(
                ticker=ticker,
                period=period,
                n_splits=5,
                commission_pct=0.001,
                data_loader=loader,
            )

            pipeline_report["processed_tickers"].append(ticker)
            pipeline_report["summary"][ticker] = report

            logger.info(
                f"[{ticker}] Procesado con éxito -> Sharpe: {report['financial_metrics']['sharpe_ratio']} | "
                f"Retorno: {report['financial_metrics']['total_return_pct']}% | "
                f"Win Rate: {report['financial_metrics']['win_rate_pct']}%"
            )

            # Persistir opcionalmente en MongoDB si get_db está configurado
            if save_to_mongo:
                try:
                    from config.db import get_db
                    db = get_db()
                    db.pipeline_daily_metrics.insert_one({
                        "ticker": ticker,
                        "timestamp": datetime.utcnow(),
                        "report": report,
                    })
                except Exception as db_err:
                    logger.warning(f"No se pudo guardar métricas en MongoDB para {ticker}: {db_err}")

        except Exception as e:
            logger.error(f"Error procesando {ticker}: {e}", exc_info=True)
            pipeline_report["failed_tickers"].append({"ticker": ticker, "error": str(e)})

    # Guardar reporte JSON en disco
    report_filename = f"daily_metrics_{timestamp_str}.json"
    report_path = os.path.join(output_dir, report_filename)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(pipeline_report, f, indent=2, ensure_ascii=False)

    logger.info(f"Pipeline diario finalizado. Reporte guardado en: {report_path}")
    return pipeline_report


def main():
    parser = argparse.ArgumentParser(description="Pipeline Diario de MLOps y Backtesting")
    parser.add_argument(
        "--tickers",
        type=str,
        default="AAPL MSFT GOOGL AMZN NVDA TSLA",
        help="Lista de tickers separados por espacio",
    )
    parser.add_argument("--period", type=str, default="2y", help="Periodo histórico (ej. 1y, 2y)")
    parser.add_argument("--output-dir", type=str, default="reports", help="Directorio de reportes")
    parser.add_argument("--no-mongo", action="store_true", help="Deshabilita guardado en MongoDB")

    args = parser.parse_args()
    tickers_list = [t.strip() for t in args.tickers.split() if t.strip()]

    run_daily_pipeline(
        tickers=tickers_list,
        period=args.period,
        output_dir=args.output_dir,
        save_to_mongo=not args.no_mongo,
    )


if __name__ == "__main__":
    main()
