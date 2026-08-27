"""Tests unitarios para la Fase 3: Logging Estructurado y Pipeline Diario de MLOps."""

import json
import logging
import os
import pytest
from unittest.mock import patch, MagicMock

from core.logger import setup_logger, JSONFormatter
from scripts.daily_ml_pipeline import run_daily_pipeline
from ml.data import MemoryDataLoader


def test_json_formatter_structure():
    """Verifica que JSONFormatter genere logs parseables con metadata completa."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Operación completada con éxito",
        args=(),
        exc_info=None,
    )
    record.extra_data = {"ticker": "AAPL", "sharpe": 1.85}

    formatted_str = formatter.format(record)
    log_json = json.loads(formatted_str)

    assert log_json["level"] == "INFO"
    assert log_json["logger"] == "test_logger"
    assert log_json["message"] == "Operación completada con éxito"
    assert log_json["lineNo"] == 42
    assert "timestamp" in log_json
    assert log_json["data"]["ticker"] == "AAPL"
    assert log_json["data"]["sharpe"] == 1.85


@patch("scripts.daily_ml_pipeline.train_and_backtest_pipeline")
@patch("scripts.daily_ml_pipeline.get_data_loader")
def test_run_daily_pipeline_execution(mock_get_loader, mock_train_pipeline, tmp_path):
    """Verifica la orquestación del pipeline diario y la generación del archivo de métricas."""
    mock_loader = MagicMock()
    mock_get_loader.return_value = mock_loader

    mock_report = {
        "ticker": "AAPL",
        "period": "2y",
        "optimal_threshold": 0.52,
        "ml_validation_metrics": {"mean_accuracy": 0.62, "std_accuracy": 0.04, "mean_auc": 0.68},
        "financial_metrics": {
            "total_return_pct": 24.5,
            "sharpe_ratio": 1.42,
            "max_drawdown_pct": -8.3,
            "win_rate_pct": 58.0,
            "profit_factor": 2.1,
            "total_trades": 12,
        },
        "benchmark_metrics": {"total_return_pct": 15.0, "max_drawdown_pct": -14.2},
        "total_trades_executed": 12,
    }
    mock_train_pipeline.return_value = (MagicMock(), mock_report)

    output_dir = str(tmp_path / "test_reports")
    pipeline_res = run_daily_pipeline(
        tickers=["AAPL", "MSFT"],
        period="2y",
        output_dir=output_dir,
        save_to_mongo=False,
    )

    assert "AAPL" in pipeline_res["processed_tickers"]
    assert "MSFT" in pipeline_res["processed_tickers"]
    assert len(pipeline_res["failed_tickers"]) == 0

    # Verificar que el archivo JSON fue escrito
    files = os.listdir(output_dir)
    assert len(files) == 1
    assert files[0].startswith("daily_metrics_") and files[0].endswith(".json")

    with open(os.path.join(output_dir, files[0]), "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "AAPL" in data["summary"]
        assert data["summary"]["AAPL"]["financial_metrics"]["sharpe_ratio"] == 1.42
