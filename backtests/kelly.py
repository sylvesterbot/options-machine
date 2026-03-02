from __future__ import annotations

import numpy as np


def apply_drawdown_governor(allocation: float, portfolio_dd: float) -> float:
    """portfolio_dd expressed as negative drawdown fraction (e.g. -0.15)."""
    if portfolio_dd <= -0.20:
        allocation *= 0.5
    elif portfolio_dd <= -0.10:
        allocation *= 0.75
    return float(min(0.08, max(0.02, allocation)))


def compute_kelly_discrete(win_rate: float, avg_win: float, avg_loss: float) -> float:
    if avg_loss <= 0:
        return 0.0
    b = avg_win / avg_loss
    if b <= 0:
        return 0.0
    k = win_rate - (1 - win_rate) / b
    return float(max(0.0, k))


def compute_kelly_empirical(returns: list[float], n_grid: int = 200) -> float:
    arr = np.array(returns, dtype=float)
    if len(arr) < 2:
        return 0.0
    grid = np.linspace(0.005, 0.50, n_grid)
    best_f = 0.0
    best_obj = -np.inf
    for f in grid:
        vals = 1.0 + f * arr
        if np.any(vals <= 0):
            continue
        obj = float(np.mean(np.log(vals)))
        if obj > best_obj:
            best_obj = obj
            best_f = float(f)
    return float(max(0.0, best_f))


def compute_kelly_fraction(
    returns: list[float] | None = None,
    min_trades: int = 50,
    default_alloc: float = 0.04,
    strategy: str | None = None,
    win_rate: float | None = None,
    avg_win: float | None = None,
    avg_loss: float | None = None,
    portfolio_dd: float = 0.0,
) -> float:
    """Backward compatible entrypoint + v2 dispatch."""
    returns = returns or []
    if len(returns) < min_trades and not (win_rate is not None and avg_win is not None and avg_loss is not None):
        return apply_drawdown_governor(float(default_alloc), portfolio_dd)

    if strategy == "A" and win_rate is not None and avg_win is not None and avg_loss is not None:
        k = compute_kelly_discrete(win_rate, avg_win, avg_loss)
    else:
        k = compute_kelly_empirical(returns)

    frac = 0.25 * k
    frac = float(min(0.08, max(0.02, frac if frac > 0 else default_alloc)))
    return apply_drawdown_governor(frac, portfolio_dd)
