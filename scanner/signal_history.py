from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

DEFAULT_PATH = "data/signal_history.csv"

COLUMNS = [
    "timestamp_utc",
    "symbol",
    "iv_rv_ratio",
    "ff_best",
    "put_skew",
    "expected_move_pct",
]


def load_history(path: str = DEFAULT_PATH) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(p)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = np.nan
    return df[COLUMNS]


def append_signals(records: list[dict], path: str = DEFAULT_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    old = load_history(path)
    new = pd.DataFrame(records)
    for c in COLUMNS:
        if c not in new.columns:
            new[c] = np.nan
    out = pd.concat([old, new[COLUMNS]], ignore_index=True)
    out.to_csv(p, index=False)


def _zscore(series: pd.Series, value: float, min_obs: int = 20) -> float:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < min_obs:
        return float("nan")
    std = float(s.std(ddof=1))
    if std <= 1e-9:
        return float("nan")
    return float((value - float(s.mean())) / std)


def get_ticker_zscore(symbol: str, field: str, value: float, path: str = DEFAULT_PATH) -> float:
    h = load_history(path)
    return _zscore(h[h["symbol"] == symbol][field], value)


def get_cross_sectional_percentile(field: str, value: float, path: str = DEFAULT_PATH) -> float:
    h = load_history(path)
    s = pd.to_numeric(h[field], errors="coerce").dropna()
    if s.empty:
        return float("nan")
    return float((s <= value).mean())


def get_iv_percentile(symbol: str, iv_rv_value: float, path: str = DEFAULT_PATH) -> float:
    h = load_history(path)
    s = pd.to_numeric(h[h["symbol"] == symbol]["iv_rv_ratio"], errors="coerce").dropna()
    if s.empty:
        return float("nan")
    return float((s <= iv_rv_value).mean())
