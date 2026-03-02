from __future__ import annotations

import numpy as np


def compute_kelly_fraction(returns: list[float], min_trades: int = 50, default_alloc: float = 0.04) -> float:
    if len(returns) < min_trades:
        return float(default_alloc)

    arr = np.array(returns, dtype=float)
    mu = float(np.mean(arr))
    var = float(np.var(arr, ddof=1)) if len(arr) > 1 else 0.0
    if var <= 1e-10:
        return float(default_alloc)

    kelly = mu / var
    fractional = 0.25 * kelly

    # drawdown guard: if mean negative, force floor
    if mu <= 0:
        fractional = 0.02

    return float(min(0.08, max(0.02, fractional)))
