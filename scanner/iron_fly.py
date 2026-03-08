"""Iron Fly strategy calculator for earnings plays (Strategy A)."""
from __future__ import annotations

import datetime as dt
import pandas as pd


def calculate_iron_fly(
    chain: pd.DataFrame,
    spot: float,
    expiration: dt.date | None = None,
    wing_multiplier: float = 3.0,
) -> dict:
    """Calculate Iron Fly strikes, premiums, break-evens, risk/reward.

    Structure: Sell ATM call + put, buy OTM wings.
    Wing width = wing_multiplier × net credit.
    """
    empty = {
        "expiration": "", "short_call_strike": float("nan"),
        "short_put_strike": float("nan"), "long_call_strike": float("nan"),
        "long_put_strike": float("nan"), "short_call_mid": float("nan"),
        "short_put_mid": float("nan"), "long_call_mid": float("nan"),
        "long_put_mid": float("nan"), "total_credit": float("nan"),
        "total_debit": float("nan"), "net_credit": float("nan"),
        "wing_width": float("nan"), "max_profit": float("nan"),
        "max_loss": float("nan"), "lower_breakeven": float("nan"),
        "upper_breakeven": float("nan"), "risk_reward_ratio": float("nan"),
        "error": "",
    }

    if chain.empty:
        empty["error"] = "Empty chain"
        return empty

    today = dt.date.today()
    if expiration is None:
        expiries = sorted([e for e in chain["expiration"].unique() if e > today])
        if not expiries:
            empty["error"] = "No future expirations"
            return empty
        short_expiries = [e for e in expiries if (e - today).days <= 9]
        expiration = short_expiries[0] if short_expiries else expiries[0]

    exp_chain = chain[chain["expiration"] == expiration].copy()
    if exp_chain.empty:
        empty["error"] = f"No options for {expiration}"
        return empty

    calls = exp_chain[exp_chain["option_type"].str.lower().str.startswith("c")]
    puts = exp_chain[exp_chain["option_type"].str.lower().str.startswith("p")]
    if calls.empty or puts.empty:
        empty["error"] = "Missing calls or puts"
        return empty

    if "delta" in calls.columns:
        calls = calls.copy()
        calls["delta_dist"] = (calls["delta"].abs() - 0.50).abs()
        short_call = calls.loc[calls["delta_dist"].idxmin()]
    else:
        calls = calls.copy()
        calls["dist"] = (calls["strike"] - spot).abs()
        short_call = calls.loc[calls["dist"].idxmin()]

    if "delta" in puts.columns:
        puts = puts.copy()
        puts["delta_dist"] = (puts["delta"].abs() - 0.50).abs()
        short_put = puts.loc[puts["delta_dist"].idxmin()]
    else:
        puts = puts.copy()
        puts["dist"] = (puts["strike"] - spot).abs()
        short_put = puts.loc[puts["dist"].idxmin()]

    sc_strike = float(short_call["strike"])
    sp_strike = float(short_put["strike"])
    sc_mid = (float(short_call.get("bid", 0)) + float(short_call.get("ask", 0))) / 2.0
    sp_mid = (float(short_put.get("bid", 0)) + float(short_put.get("ask", 0))) / 2.0
    total_credit = sc_mid + sp_mid
    if total_credit <= 0:
        empty["error"] = "Zero credit"
        return empty

    wing_width = wing_multiplier * total_credit
    lc_candidates = calls[calls["strike"] >= sc_strike + wing_width].sort_values("strike")
    lp_candidates = puts[puts["strike"] <= sp_strike - wing_width].sort_values("strike", ascending=False)

    if lc_candidates.empty:
        lc_candidates = calls[calls["strike"] > sc_strike].sort_values("strike")
    if lp_candidates.empty:
        lp_candidates = puts[puts["strike"] < sp_strike].sort_values("strike", ascending=False)
    if lc_candidates.empty or lp_candidates.empty:
        empty["error"] = "No suitable wing strikes"
        return empty

    long_call = lc_candidates.iloc[0]
    long_put = lp_candidates.iloc[0]
    lc_actual = float(long_call["strike"])
    lp_actual = float(long_put["strike"])
    lc_mid = (float(long_call.get("bid", 0)) + float(long_call.get("ask", 0))) / 2.0
    lp_mid = (float(long_put.get("bid", 0)) + float(long_put.get("ask", 0))) / 2.0

    total_debit = lc_mid + lp_mid
    net_credit = total_credit - total_debit
    actual_wing = max(lc_actual - sc_strike, sp_strike - lp_actual)
    if actual_wing <= net_credit:
        actual_wing = net_credit + 0.01
    max_loss = actual_wing - net_credit
    risk_reward = float(max_loss / net_credit) if net_credit > 0 else float("nan")

    return {
        "expiration": str(expiration),
        "short_call_strike": sc_strike, "short_put_strike": sp_strike,
        "long_call_strike": lc_actual, "long_put_strike": lp_actual,
        "short_call_mid": sc_mid, "short_put_mid": sp_mid,
        "long_call_mid": lc_mid, "long_put_mid": lp_mid,
        "total_credit": round(total_credit, 2),
        "total_debit": round(total_debit, 2),
        "net_credit": round(net_credit, 2),
        "wing_width": round(actual_wing, 2),
        "max_profit": round(net_credit, 2),
        "max_loss": round(max_loss, 2),
        "lower_breakeven": round(sp_strike - net_credit, 2),
        "upper_breakeven": round(sc_strike + net_credit, 2),
        "risk_reward_ratio": risk_reward,
        "error": "",
    }
