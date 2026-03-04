from __future__ import annotations

import numpy as np


def bootstrap_equity_paths(returns: list[float], n_paths: int = 1000, horizon: int | None = None, seed: int = 42) -> np.ndarray:
    r = np.array(returns, dtype=float)
    if r.size == 0:
        return np.ones((n_paths, 1), dtype=float)

    h = int(horizon or len(r))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(r), size=(n_paths, h))
    sampled = r[idx]
    eq = np.cumprod(1.0 + sampled, axis=1)
    return np.concatenate([np.ones((n_paths, 1)), eq], axis=1)


def summarize_paths(paths: np.ndarray) -> dict:
    final = paths[:, -1]
    p5 = float(np.percentile(final, 5))
    p50 = float(np.percentile(final, 50))
    p95 = float(np.percentile(final, 95))
    prob_loss = float(np.mean(final < 1.0))
    return {"p5": p5, "p50": p50, "p95": p95, "prob_loss": prob_loss}
