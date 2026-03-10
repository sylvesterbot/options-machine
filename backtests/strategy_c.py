from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from backtests.kelly import compute_kelly_fraction
from scanner.skew_score import compute_skew_score


REQUIRED_COLUMNS = [
    "symbol",
    "entry_date",
    "exit_date",
    "short_strike",
    "long_strike",
    "entry_credit",
    "exit_cost",
    "max_loss",
    "entry_price",
    "exit_price",
    "return_pct",
    "alloc",
    "portfolio_return",
    "capital",
    "put_skew",
    "rv_edge",
    "stopped_out",
    "exit_reason",
]


def _to_date(v) -> dt.date:
    if isinstance(v, dt.date):
        return v
    return pd.to_datetime(v).date()


def _mid_put(chain: pd.DataFrame, expiration: dt.date, strike: float) -> float:
    c = chain.copy()
    c["expiration"] = c["expiration"].apply(_to_date)
    c["strike"] = pd.to_numeric(c["strike"], errors="coerce")
    sub = c[
        (c["expiration"] == expiration)
        & (c["strike"] == float(strike))
        & (c["option_type"].astype(str).str.lower().str.startswith("p"))
    ]
    if sub.empty:
        raise ValueError("missing put leg")

    bid = pd.to_numeric(sub.get("bid"), errors="coerce")
    ask = pd.to_numeric(sub.get("ask"), errors="coerce")
    if bid.notna().any() and ask.notna().any():
        return float(((bid + ask) / 2.0).dropna().iloc[0])

    if "mid" in sub.columns:
        mid = pd.to_numeric(sub["mid"], errors="coerce").dropna()
        if not mid.empty:
            return float(mid.iloc[0])

    raise ValueError("missing bid/ask for put leg")


def _rv30(px: pd.DataFrame, i: int) -> float:
    w = px.iloc[max(0, i - 30) : i + 1]
    if len(w) <= 5:
        return 0.2
    r = np.log(w["close"] / w["close"].shift(1)).dropna()
    if len(r) <= 2:
        return 0.2
    return float(r.std() * np.sqrt(252))


def simulate_strategy_c(
    provider,
    symbol: str,
    start: dt.date,
    end: dt.date,
    skew_threshold: float = 1.3,
    rv_edge_min: float = 0.0,
    holding_days: int = 10,
    stop_loss_pct: float = -0.50,
    target_profit_pct: float = 0.50,
    use_kelly: bool = False,
    initial_capital: float = 100000.0,
    slippage_pct: float = 0.0,
    kelly_min_trades: int = 50,
) -> pd.DataFrame:
    px = provider.get_underlying_prices(symbol, start, end).copy()
    if px.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    px["date"] = pd.to_datetime(px["date"]).dt.date
    px = px.sort_values("date").reset_index(drop=True)

    trades: list[dict] = []
    trade_returns: list[float] = []
    capital = float(initial_capital)
    peak_capital = float(initial_capital)
    slippage_pct = max(0.0, float(slippage_pct))

    i = 0
    while i < len(px) - 1:
        entry_date = px.loc[i, "date"]
        entry_spot = float(px.loc[i, "close"])

        chain = provider.get_options_chain(symbol, entry_date)
        if chain is None or len(chain) == 0:
            i += 1
            continue

        chain = chain.copy()
        chain["expiration"] = chain["expiration"].apply(_to_date)
        chain["strike"] = pd.to_numeric(chain["strike"], errors="coerce")

        rv30 = _rv30(px, i)
        skew = compute_skew_score(chain, entry_spot, rv30, as_of_date=entry_date)

        put_skew = float(skew.get("put_skew", float("nan")))
        rv_edge = float(skew.get("rv_edge_put", float("nan")))
        target_short = float(skew.get("otm_put_strike", float("nan")))

        if np.isnan(put_skew) or put_skew < float(skew_threshold):
            i += 1
            continue
        if np.isnan(rv_edge) or rv_edge < float(rv_edge_min):
            i += 1
            continue

        expiries = sorted([e for e in chain["expiration"].unique() if e > entry_date])
        if not expiries:
            i += 1
            continue
        target_exp = entry_date + dt.timedelta(days=30)
        expiry = min(expiries, key=lambda e: abs((e - target_exp).days))

        puts = chain[
            (chain["expiration"] == expiry)
            & (chain["option_type"].astype(str).str.lower().str.startswith("p"))
        ].copy()
        if puts.empty:
            i += 1
            continue

        strikes = sorted(pd.to_numeric(puts["strike"], errors="coerce").dropna().unique())
        if len(strikes) < 2:
            i += 1
            continue

        if np.isnan(target_short):
            candidates = [s for s in strikes if s <= entry_spot]
            short_strike = max(candidates) if candidates else strikes[-1]
        else:
            short_strike = min(strikes, key=lambda s: abs(s - target_short))

        lower = [s for s in strikes if s < short_strike]
        if not lower:
            i += 1
            continue
        long_strike = max(lower)

        try:
            short_mid = _mid_put(puts, expiry, short_strike)
            long_mid = _mid_put(puts, expiry, long_strike)
        except Exception:
            i += 1
            continue

        raw_entry_credit = short_mid - long_mid
        entry_credit = raw_entry_credit * (1.0 - slippage_pct)
        width = float(short_strike - long_strike)
        max_loss = width - entry_credit
        if entry_credit <= 0 or max_loss <= 0:
            i += 1
            continue

        exit_idx = min(i + int(holding_days), len(px) - 1)
        stopped_out = False
        exit_reason = "expiry"

        for j in range(i + 1, exit_idx + 1):
            d = px.loc[j, "date"]
            c_daily = provider.get_options_chain(symbol, d)
            if c_daily is None or len(c_daily) == 0:
                continue
            c_daily = c_daily.copy()
            c_daily["expiration"] = c_daily["expiration"].apply(_to_date)
            c_daily["strike"] = pd.to_numeric(c_daily["strike"], errors="coerce")
            c_daily = c_daily[
                (c_daily["expiration"] == expiry)
                & (c_daily["option_type"].astype(str).str.lower().str.startswith("p"))
            ]
            if c_daily.empty:
                continue
            try:
                short_daily = _mid_put(c_daily, expiry, short_strike)
                long_daily = _mid_put(c_daily, expiry, long_strike)
            except Exception:
                continue

            raw_exit_cost_daily = short_daily - long_daily
            exit_cost_daily = raw_exit_cost_daily * (1.0 + slippage_pct)
            ret_daily = float((entry_credit - exit_cost_daily) / max_loss)
            if ret_daily >= float(target_profit_pct):
                exit_idx = j
                exit_reason = "profit_target"
                break
            if ret_daily <= float(stop_loss_pct):
                exit_idx = j
                stopped_out = True
                exit_reason = "stop_loss"
                break

        exit_date = px.loc[exit_idx, "date"]
        exit_spot = float(px.loc[exit_idx, "close"])
        exit_chain = provider.get_options_chain(symbol, exit_date)
        if exit_chain is None or len(exit_chain) == 0:
            i = exit_idx + 1
            continue
        exit_chain = exit_chain.copy()
        exit_chain["expiration"] = exit_chain["expiration"].apply(_to_date)
        exit_chain["strike"] = pd.to_numeric(exit_chain["strike"], errors="coerce")
        exit_chain = exit_chain[
            (exit_chain["expiration"] == expiry)
            & (exit_chain["option_type"].astype(str).str.lower().str.startswith("p"))
        ]
        if exit_chain.empty:
            i = exit_idx + 1
            continue

        try:
            short_exit = _mid_put(exit_chain, expiry, short_strike)
            long_exit = _mid_put(exit_chain, expiry, long_strike)
        except Exception:
            i = exit_idx + 1
            continue

        raw_exit_cost = short_exit - long_exit
        exit_cost = raw_exit_cost * (1.0 + slippage_pct)
        ret = float((entry_credit - exit_cost) / max_loss)

        alloc = 1.0
        portfolio_dd = (capital / peak_capital - 1.0) if peak_capital > 0 else 0.0
        if use_kelly:
            alloc = float(
                compute_kelly_fraction(
                    returns=trade_returns,
                    portfolio_dd=portfolio_dd,
                    min_trades=kelly_min_trades,
                )
            )

        portfolio_return = alloc * ret
        capital *= 1.0 + portfolio_return
        peak_capital = max(peak_capital, capital)
        trade_returns.append(ret)

        trades.append(
            {
                "symbol": symbol,
                "entry_date": str(entry_date),
                "exit_date": str(exit_date),
                "short_strike": float(short_strike),
                "long_strike": float(long_strike),
                "entry_credit": float(entry_credit),
                "exit_cost": float(exit_cost),
                "max_loss": float(max_loss),
                "entry_price": float(entry_spot),
                "exit_price": float(exit_spot),
                "return_pct": float(ret),
                "alloc": float(alloc),
                "portfolio_return": float(portfolio_return),
                "capital": float(capital),
                "put_skew": float(put_skew),
                "rv_edge": float(rv_edge),
                "stopped_out": bool(stopped_out),
                "exit_reason": str(exit_reason),
            }
        )
        i = exit_idx + 1

    return pd.DataFrame(trades, columns=REQUIRED_COLUMNS)
