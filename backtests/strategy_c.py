from __future__ import annotations

import datetime as dt
import numpy as np
import pandas as pd

from scanner.skew_score import compute_skew_score


def simulate_strategy_c(
    provider,
    symbol: str,
    start: dt.date,
    end: dt.date,
    skew_threshold: float = 1.30,
    holding_days: int = 10,
) -> pd.DataFrame:
    px = provider.get_underlying_prices(symbol, start, end).copy()
    if px.empty:
        return pd.DataFrame(columns=["symbol", "entry_date", "exit_date", "entry_spot", "exit_spot", "return_pct", "put_skew", "signal"])

    px["date"] = pd.to_datetime(px["date"]).dt.date
    px = px.sort_values("date").reset_index(drop=True)

    trades: list[dict] = []
    i = 0
    while i < len(px) - 1:
        entry_date = px.loc[i, "date"]
        entry_spot = float(px.loc[i, "close"])

        # lightweight RV proxy from local history
        w = px.iloc[max(0, i - 30): i + 1]
        if len(w) > 5:
            r = np.log(w["close"] / w["close"].shift(1)).dropna()
            rv30 = float(r.std() * np.sqrt(252)) if len(r) > 2 else 0.2
        else:
            rv30 = 0.2

        chain = provider.get_options_chain(symbol, entry_date)
        if chain is None or len(chain) == 0:
            i += 1
            continue

        skew = compute_skew_score(chain, spot=entry_spot, rv30=rv30, as_of_date=entry_date)
        put_skew = float(skew.get("put_skew", float("nan")))
        if np.isnan(put_skew) or put_skew < skew_threshold:
            i += 1
            continue

        exit_idx = min(i + holding_days, len(px) - 1)
        exit_date = px.loc[exit_idx, "date"]
        exit_spot = float(px.loc[exit_idx, "close"])

        # directional proxy: rich put skew => mean-reversion up-bias
        ret = float((exit_spot - entry_spot) / entry_spot)

        trades.append(
            {
                "symbol": symbol,
                "entry_date": str(entry_date),
                "exit_date": str(exit_date),
                "entry_spot": entry_spot,
                "exit_spot": exit_spot,
                "return_pct": ret,
                "put_skew": put_skew,
                "signal": str(skew.get("skew_signal", "RICH_PUT_SKEW")),
            }
        )
        i = exit_idx + 1

    return pd.DataFrame(trades)
