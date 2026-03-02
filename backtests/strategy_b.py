from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
import numpy as np
import pandas as pd

from scanner.forward_factor import compute_forward_factor


@dataclass
class CalendarLeg:
    expiration: dt.date
    strike: float


def _to_date(v) -> dt.date:
    if isinstance(v, dt.date):
        return v
    return pd.to_datetime(v).date()


def _mid_price(chain: pd.DataFrame, expiration: dt.date, strike: float) -> float:
    c = chain.copy()
    c["expiration"] = c["expiration"].apply(_to_date)
    sub = c[(c["expiration"] == expiration) & (pd.to_numeric(c["strike"], errors="coerce") == float(strike)) & (c["option_type"].astype(str).str.lower().str.startswith("c"))]
    if sub.empty:
        raise ValueError("Missing contract for calendar leg")
    bid = pd.to_numeric(sub["bid"], errors="coerce")
    ask = pd.to_numeric(sub["ask"], errors="coerce")
    return float(((bid + ask) / 2.0).dropna().iloc[0])


def _select_legs(entry_chain: pd.DataFrame, entry_spot: float, ff_pair: str, pair_expiries: dict) -> CalendarLeg:
    if ff_pair not in pair_expiries:
        raise ValueError("Missing ff pair expiry info")
    front_exp = _to_date(pair_expiries[ff_pair][0])
    back_exp = _to_date(pair_expiries[ff_pair][1])

    c = entry_chain.copy()
    c["expiration"] = c["expiration"].apply(_to_date)
    c = c[(c["expiration"].isin([front_exp, back_exp])) & (c["option_type"].astype(str).str.lower().str.startswith("c"))]
    if c.empty:
        raise ValueError("No call options for selected FF pair")
    c["dist"] = (pd.to_numeric(c["strike"], errors="coerce") - entry_spot).abs()
    strike = float(pd.to_numeric(c.loc[c["dist"].idxmin(), "strike"], errors="coerce"))
    return CalendarLeg(expiration=front_exp, strike=strike), CalendarLeg(expiration=back_exp, strike=strike)


def simulate_strategy_b(
    provider,
    symbol: str,
    start: dt.date,
    end: dt.date,
    ff_threshold: float = 0.2,
    holding_days: int = 10,
    exit_mode: str = "fixed",  # fixed | mean_revert
    mean_revert_threshold: float = 0.05,
) -> pd.DataFrame:
    px = provider.get_underlying_prices(symbol, start, end).copy()
    if px.empty:
        return pd.DataFrame(columns=["symbol", "entry_date", "exit_date", "entry_price", "exit_price", "return_pct", "ff_entry", "ff_exit", "ff_pair"])
    px["date"] = pd.to_datetime(px["date"]).dt.date
    px = px.sort_values("date").reset_index(drop=True)

    trades = []
    i = 0
    while i < len(px) - 1:
        entry_date = px.loc[i, "date"]
        entry_spot = float(px.loc[i, "close"])
        chain = provider.get_options_chain(symbol, entry_date)
        if chain is None or len(chain) == 0:
            i += 1
            continue
        ff = compute_forward_factor(chain, entry_spot, as_of_date=entry_date)
        ff_best = float(ff.get("ff_best", float("nan")))
        if np.isnan(ff_best) or ff_best < ff_threshold:
            i += 1
            continue

        try:
            front, back = _select_legs(chain, entry_spot, ff.get("ff_best_pair", "NONE"), ff.get("pair_expiries", {}))
            entry_front = _mid_price(chain, front.expiration, front.strike)
            entry_back = _mid_price(chain, back.expiration, back.strike)
        except Exception:
            i += 1
            continue

        entry_price = entry_back - entry_front  # debit calendar
        if entry_price <= 0:
            i += 1
            continue

        exit_idx = min(i + holding_days, len(px) - 1)
        ff_exit_val = float("nan")
        if exit_mode == "mean_revert":
            for j in range(i + 1, min(i + holding_days, len(px) - 1) + 1):
                d = px.loc[j, "date"]
                c2 = provider.get_options_chain(symbol, d)
                if c2 is None or len(c2) == 0:
                    continue
                ff2 = compute_forward_factor(c2, float(px.loc[j, "close"]), as_of_date=d)
                ff2v = float(ff2.get("ff_best", float("nan")))
                if not np.isnan(ff2v) and ff2v < mean_revert_threshold:
                    exit_idx = j
                    ff_exit_val = ff2v
                    break

        exit_date = px.loc[exit_idx, "date"]
        exit_chain = provider.get_options_chain(symbol, exit_date)
        if exit_chain is None or len(exit_chain) == 0:
            i = exit_idx + 1
            continue

        try:
            exit_front = _mid_price(exit_chain, front.expiration, front.strike)
            exit_back = _mid_price(exit_chain, back.expiration, back.strike)
        except Exception:
            i = exit_idx + 1
            continue

        exit_price = exit_back - exit_front
        ret = (exit_price - entry_price) / entry_price

        trades.append(
            {
                "symbol": symbol,
                "entry_date": str(entry_date),
                "exit_date": str(exit_date),
                "entry_price": float(entry_price),
                "exit_price": float(exit_price),
                "return_pct": float(ret),
                "ff_entry": ff_best,
                "ff_exit": ff_exit_val,
                "ff_pair": ff.get("ff_best_pair", "NONE"),
            }
        )
        i = exit_idx + 1

    return pd.DataFrame(trades)


def summarize_trade_log(trades: pd.DataFrame) -> dict:
    if trades.empty or "return_pct" not in trades.columns:
        return {"trades": 0, "total_return": 0.0, "avg_return": 0.0, "volatility": 0.0, "max_drawdown": 0.0}

    r = pd.to_numeric(trades["return_pct"], errors="coerce").dropna()
    if r.empty:
        return {"trades": 0, "total_return": 0.0, "avg_return": 0.0, "volatility": 0.0, "max_drawdown": 0.0}

    equity = (1 + r).cumprod()
    peak = equity.cummax()
    dd = (equity / peak) - 1.0

    return {
        "trades": int(len(r)),
        "total_return": float(equity.iloc[-1] - 1.0),
        "avg_return": float(r.mean()),
        "volatility": float(r.std(ddof=1)) if len(r) > 1 else 0.0,
        "max_drawdown": float(dd.min()),
    }
