"""Actualiza modelos globales (XGB y MLP) con tickers recientes o provistos."""

import argparse

from ml.global_models import train_or_update_xgb_global, train_or_update_mlp_global, tickers_from_usage


def main():
    parser = argparse.ArgumentParser(description="Actualiza modelos globales con tickers recientes")
    parser.add_argument("--tickers", nargs="*", help="Lista de tickers a usar", default=None)
    parser.add_argument("--period", default="2y", help="Periodo de historial por ticker (ej: 6mo, 1y, 2y)")
    args = parser.parse_args()

    tickers = args.tickers if args.tickers else tickers_from_usage()
    print(f"[INFO] Entrenando/actualizando con tickers: {tickers}")

    xgb = train_or_update_xgb_global(tickers, period=args.period)
    print("[OK] XGBoost global actualizado.")

    mlp = train_or_update_mlp_global(tickers, period=args.period)
    print("[OK] MLP global actualizado.")


if __name__ == "__main__":
    main()
