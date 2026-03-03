from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
import numpy as np
import pandas as pd

from scanner.forward_factor import compute_forward_factor

from backtests.kelly import compute_kelly_fraction


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
    iv_rv_max: float = 2.0,
    use_kelly: bool = False,
    initial_capital: float = 100000.0,
    stop_loss_pct: float = -0.20,
    max_concurrent: int = 1,
    slippage_pct: float = 0.0,
) -> pd.DataFrame:
    px = provider.get_underlying_prices(symbol, start, end).copy()
    if px.empty:
        return pd.DataFrame(columns=["symbol", "entry_date", "exit_date", "entry_price", "exit_price", "return_pct", "ff_entry", "ff_exit", "ff_pair", "stopped_out"])
    px["date"] = pd.to_datetime(px["date"]).dt.date
    px = px.sort_values("date").reset_index(drop=True)

    trades = []
    trade_returns: list[float] = []
    capital = float(initial_capital)
    peak_capital = float(initial_capital)
    i = 0
    max_concurrent = max(1, int(max_concurrent))
    slippage_pct = max(0.0, float(slippage_pct))
    while i < len(px) - 1:
        if max_concurrent < 1:
            i += 1
            continue

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

        # Regime filter: skip extreme IV relative to recent realized vol (backwardation trap)
        iv_30 = float(ff.get("front_iv", float("nan")))
        if not np.isnan(iv_30) and iv_rv_max is not None and iv_rv_max > 0:
            px_window = px.iloc[max(0, i - 30) : i + 1]
            if len(px_window) > 5:
                log_rets = np.log(px_window["close"] / px_window["close"].shift(1)).dropna()
                rv30 = float(log_rets.std() * np.sqrt(252)) if len(log_rets) > 2 else 0.0
            else:
                rv30 = 0.0
            if rv30 > 0:
                iv_rv = iv_30 / rv30
                if iv_rv > iv_rv_max:
                    i += 1
                    continue

        try:
            front, back = _select_legs(chain, entry_spot, ff.get("ff_best_pair", "NONE"), ff.get("pair_expiries", {}))
            entry_front = _mid_price(chain, front.expiration, front.strike)
            entry_back = _mid_price(chain, back.expiration, back.strike)
        except Exception:
            i += 1
            continue

        raw_entry_price = entry_back - entry_front  # debit calendar
        entry_price = raw_entry_price * (1.0 + slippage_pct)
        if entry_price <= 0:
            i += 1
            continue

        exit_idx = min(i + holding_days, len(px) - 1)
        ff_exit_val = float("nan")
        stopped_out = False

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

        # Intra-trade daily stop-loss check
        last_check = min(i + holding_days, len(px) - 1)
        for j in range(i + 1, last_check + 1):
            d = px.loc[j, "date"]
            c_daily = provider.get_options_chain(symbol, d)
            if c_daily is None or len(c_daily) == 0:
                continue
            try:
                daily_front = _mid_price(c_daily, front.expiration, front.strike)
                daily_back = _mid_price(c_daily, back.expiration, back.strike)
            except Exception:
                continue
            raw_exit_daily = daily_back - daily_front
            exit_daily = raw_exit_daily * (1.0 - slippage_pct)
            ret_daily = float((exit_daily - entry_price) / entry_price)
            if ret_daily <= float(stop_loss_pct):
                exit_idx = j
                stopped_out = True
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

        raw_exit_price = exit_back - exit_front
        exit_price = raw_exit_price * (1.0 - slippage_pct)
        ret = float((exit_price - entry_price) / entry_price)

        # Portfolio sizing
        alloc = 1.0
        portfolio_dd = (capital / peak_capital - 1.0) if peak_capital > 0 else 0.0
        if use_kelly:
            alloc = float(compute_kelly_fraction(returns=trade_returns, portfolio_dd=portfolio_dd))

        portfolio_return = alloc * ret
        capital *= (1.0 + portfolio_return)
        peak_capital = max(peak_capital, capital)
        trade_returns.append(ret)

        trades.append(
            {
                "symbol": symbol,
                "entry_date": str(entry_date),
                "exit_date": str(exit_date),
                "entry_price": float(entry_price),
                "exit_price": float(exit_price),
                "return_pct": float(ret),
                "alloc": float(alloc),
                "portfolio_return": float(portfolio_return),
                "capital": float(capital),
                "ff_entry": ff_best,
                "ff_exit": ff_exit_val,
                "ff_pair": ff.get("ff_best_pair", "NONE"),
                "stopped_out": bool(stopped_out),
            }
        )
        i = exit_idx + 1

    return pd.DataFrame(trades)


def summarize_trade_log(trades: pd.DataFrame) -> dict:
    empty = {"trades": 0, "total_return": 0.0, "avg_return": 0.0, "volatility": 0.0, "max_drawdown": 0.0, "sharpe": 0.0}
    if trades.empty or "return_pct" not in trades.columns:
        return empty

    col = "portfolio_return" if "portfolio_return" in trades.columns else "return_pct"
    r = pd.to_numeric(trades[col], errors="coerce").dropna()
    if r.empty:
        return empty

    equity = (1 + r).cumprod()
    peak = equity.cummax()
    dd = (equity / peak) - 1.0
    vol = float(r.std(ddof=1)) if len(r) > 1 else 0.0
    sharpe = float((r.mean() / vol) * np.sqrt(252)) if vol > 0 else 0.0

    return {
        "trades": int(len(r)),
        "total_return": float(equity.iloc[-1] - 1.0),
        "avg_return": float(r.mean()),
        "volatility": vol,
        "max_drawdown": float(dd.min()),
        "sharpe": sharpe,
    }
