"""Módulo de cálculo de métricas financieras y de riesgo para estrategias cuantitativas."""

from typing import Dict, Any
import numpy as np
import pandas as pd


def calculate_financial_metrics(
    equity_series: pd.Series,
    trades_df: pd.DataFrame | None = None,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> Dict[str, Any]:
    """Calcula métricas clave de desempeño financiero y riesgo.
    
    Args:
        equity_series: Serie temporal con la evolución del capital (Equity Curve).
        trades_df: DataFrame con el historial de operaciones ejecutadas (opcional).
        risk_free_rate: Tasa libre de riesgo anualizada (default: 2% = 0.02).
        periods_per_year: Días de trading por año (252 para acciones).
    
    Returns:
        Dict con métricas: Total Return, CAGR, Volatilidad, Sharpe, Sortino, MDD, Win Rate, Profit Factor, etc.
    """
    if equity_series.empty or len(equity_series) < 2:
        return {
            "total_return_pct": 0.0,
            "cagr_pct": 0.0,
            "annualized_volatility_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
        }

    # 1. Retornos Diarios
    daily_returns = equity_series.pct_change().dropna()
    initial_val = equity_series.iloc[0]
    final_val = equity_series.iloc[-1]
    
    # 2. Retorno Total & CAGR
    total_return = (final_val - initial_val) / initial_val
    n_periods = len(daily_returns)
    years = n_periods / periods_per_year
    cagr = ((final_val / initial_val) ** (1.0 / years) - 1.0) if (years > 0 and initial_val > 0 and final_val > 0) else total_return

    # 3. Volatilidad Anualizada
    daily_vol = daily_returns.std()
    annualized_vol = daily_vol * np.sqrt(periods_per_year) if not np.isnan(daily_vol) else 0.0

    # 4. Sharpe Ratio
    rf_daily = (1.0 + risk_free_rate) ** (1.0 / periods_per_year) - 1.0
    excess_returns = daily_returns - rf_daily
    excess_mean = excess_returns.mean()
    sharpe = (excess_mean / (daily_vol + 1e-9)) * np.sqrt(periods_per_year) if daily_vol > 0 else 0.0

    # 5. Sortino Ratio (considera sólo la volatilidad a la baja)
    downside_returns = daily_returns[daily_returns < rf_daily] - rf_daily
    downside_std = np.sqrt(np.mean(downside_returns**2)) if len(downside_returns) > 0 else 0.0
    sortino = (excess_mean / (downside_std + 1e-9)) * np.sqrt(periods_per_year) if downside_std > 0 else 0.0

    # 6. Maximum Drawdown (MDD)
    cumulative_max = equity_series.cummax()
    drawdown = (equity_series - cumulative_max) / (cumulative_max + 1e-9)
    max_drawdown = float(drawdown.min())  # Valor negativo

    # 7. Métricas de Trades (Win Rate, Profit Factor)
    win_rate = 0.0
    profit_factor = 0.0
    total_trades = 0

    if trades_df is not None and not trades_df.empty and "pnl" in trades_df.columns:
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df["pnl"] > 0]
        losing_trades = trades_df[trades_df["pnl"] < 0]

        win_rate = (len(winning_trades) / total_trades) * 100.0 if total_trades > 0 else 0.0

        gross_profit = winning_trades["pnl"].sum()
        gross_loss = abs(losing_trades["pnl"].sum())

        if gross_loss > 0:
            profit_factor = float(gross_profit / gross_loss)
        elif gross_profit > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0.0

    return {
        "total_return_pct": round(float(total_return * 100.0), 2),
        "cagr_pct": round(float(cagr * 100.0), 2),
        "annualized_volatility_pct": round(float(annualized_vol * 100.0), 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "sortino_ratio": round(float(sortino), 2),
        "max_drawdown_pct": round(float(max_drawdown * 100.0), 2),
        "win_rate_pct": round(float(win_rate), 2),
        "profit_factor": round(float(profit_factor), 2) if profit_factor != float("inf") else 999.0,
        "total_trades": int(total_trades),
    }
