"""Motor de Backtesting para simulación de estrategias ML con costos transaccionales."""

from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np
import pandas as pd

from ml.backtesting.metrics import calculate_financial_metrics


@dataclass
class BacktestConfig:
    """Configuración de simulación de backtesting."""
    initial_capital: float = 10_000.0
    commission_pct: float = 0.001       # 0.10% por operación (broker fee)
    slippage_pct: float = 0.0005        # 0.05% de deslizamiento en ejecución
    position_size_pct: float = 1.0      # 100% del capital disponible por trade
    risk_free_rate: float = 0.02


class BacktestSimulator:
    """Simulador de trading orientado a evaluar señales generadas por modelos de ML."""

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()

    def run(
        self,
        df: pd.DataFrame,
        signals: pd.Series | np.ndarray,
        price_col: str = "Close",
    ) -> Dict[str, Any]:
        """Ejecuta el backtesting sobre una serie de precios y señales.

        Args:
            df: DataFrame con precios (debe contener el índice temporal y `price_col`).
            signals: Serie o array binario/categórico (1: Comprar/Mantener, 0: Salir/Liquidez).
            price_col: Nombre de la columna de precio de ejecución.

        Returns:
            Dict con:
                - `metrics`: Métricas de la estrategia
                - `benchmark_metrics`: Métricas de Buy & Hold
                - `equity_curve`: Serie temporal con la evolución de la cartera
                - `trades`: DataFrame con el registro detallado de trades
        """
        prices = df[price_col].values
        dates = df.index
        signals = np.asarray(signals)

        capital = self.config.initial_capital
        cash = capital
        shares = 0.0
        in_position = False
        entry_price = 0.0
        entry_date = None

        equity_history: List[float] = []
        trades: List[Dict[str, Any]] = []

        total_cost_factor_buy = 1.0 + (self.config.commission_pct + self.config.slippage_pct)
        total_cost_factor_sell = 1.0 - (self.config.commission_pct + self.config.slippage_pct)

        for i in range(len(prices)):
            current_price = prices[i]
            sig = signals[i]
            current_date = dates[i]

            # Lógica de Ejecución:
            # Señal de COMPRA y no estamos dentro del mercado
            if sig == 1 and not in_position:
                effective_buy_price = current_price * total_cost_factor_buy
                allocated_cash = cash * self.config.position_size_pct
                shares_to_buy = allocated_cash / effective_buy_price

                if shares_to_buy > 0:
                    shares = shares_to_buy
                    cash -= allocated_cash
                    in_position = True
                    entry_price = effective_buy_price
                    entry_date = current_date

            # Señal de VENTA (0) y estamos en posición
            elif sig == 0 and in_position:
                effective_sell_price = current_price * total_cost_factor_sell
                proceeds = shares * effective_sell_price
                pnl = proceeds - (shares * entry_price)
                return_pct = (effective_sell_price / entry_price - 1.0) * 100.0

                trades.append({
                    "entry_date": entry_date,
                    "exit_date": current_date,
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(effective_sell_price, 2),
                    "shares": round(shares, 4),
                    "pnl": round(pnl, 2),
                    "return_pct": round(return_pct, 2),
                })

                cash += proceeds
                shares = 0.0
                in_position = False

            # Valoración diaria de cartera (Equity)
            current_equity = cash + (shares * current_price)
            equity_history.append(current_equity)

        # Cierre forzoso de posición al final del periodo para liquidar métricas si seguía abierto
        if in_position:
            effective_sell_price = prices[-1] * total_cost_factor_sell
            proceeds = shares * effective_sell_price
            pnl = proceeds - (shares * entry_price)
            return_pct = (effective_sell_price / entry_price - 1.0) * 100.0
            trades.append({
                "entry_date": entry_date,
                "exit_date": dates[-1],
                "entry_price": round(entry_price, 2),
                "exit_price": round(effective_sell_price, 2),
                "shares": round(shares, 4),
                "pnl": round(pnl, 2),
                "return_pct": round(return_pct, 2),
            })
            equity_history[-1] = cash + proceeds

        equity_series = pd.Series(equity_history, index=dates, name="Strategy_Equity")
        trades_df = pd.DataFrame(trades)

        # Benchmark: Estrategia Buy & Hold pasiva
        buy_hold_shares = (self.config.initial_capital * (1.0 - self.config.commission_pct)) / prices[0]
        benchmark_equity = pd.Series(buy_hold_shares * prices, index=dates, name="Buy_Hold_Equity")

        # Cálculo de métricas
        strategy_metrics = calculate_financial_metrics(
            equity_series=equity_series,
            trades_df=trades_df,
            risk_free_rate=self.config.risk_free_rate,
        )

        benchmark_metrics = calculate_financial_metrics(
            equity_series=benchmark_equity,
            trades_df=None,
            risk_free_rate=self.config.risk_free_rate,
        )

        return {
            "metrics": strategy_metrics,
            "benchmark_metrics": benchmark_metrics,
            "equity_curve": equity_series,
            "benchmark_curve": benchmark_equity,
            "trades": trades_df,
        }
