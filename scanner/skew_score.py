"""Strategy C: Skew scoring — detect overpriced OTM options."""
import datetime as dt
import numpy as np
import pandas as pd


def compute_skew_score(chain: pd.DataFrame, spot: float, rv30: float) -> dict:
    today = dt.date.today()
    expiries = sorted([e for e in chain["expiration"].unique() if e > today])
    EMPTY = {"atm_iv": float("nan"), "otm_put_iv": float("nan"),
             "otm_call_iv": float("nan"), "put_skew": float("nan"),
             "call_skew": float("nan"), "skew_rv_ratio": float("nan"),
             "skew_signal": "NONE"}

    if not expiries:
        return EMPTY

    target = today + dt.timedelta(days=30)
    exp = min(expiries, key=lambda e: abs((e - target).days))
    e_df = chain[chain["expiration"] == exp].copy()
    if e_df.empty:
        return EMPTY

    e_df["dist"] = (e_df["strike"] - spot).abs()
    atm_strike = e_df.loc[e_df["dist"].idxmin(), "strike"]

    atm_options = e_df[e_df["strike"] == atm_strike]
    atm_iv = float(atm_options["implied_volatility"].dropna().mean())

    puts = e_df[e_df["option_type"].str.lower().str.startswith("p")]
    calls = e_df[e_df["option_type"].str.lower().str.startswith("c")]

    otm_put_iv = float("nan")
    if not puts.empty:
        p = puts.copy()
        p["d"] = (p["strike"] - spot * 0.95).abs()
        otm_put_iv = float(p.loc[p["d"].idxmin(), "implied_volatility"])

    otm_call_iv = float("nan")
    if not calls.empty:
        c = calls.copy()
        c["d"] = (c["strike"] - spot * 1.05).abs()
        otm_call_iv = float(c.loc[c["d"].idxmin(), "implied_volatility"])

    put_skew = otm_put_iv / atm_iv if atm_iv and atm_iv > 0 else float("nan")
    call_skew = otm_call_iv / atm_iv if atm_iv and atm_iv > 0 else float("nan")
    skew_rv = otm_put_iv / rv30 if rv30 and rv30 > 0 and not np.isnan(rv30) else float("nan")

    signal = "NONE"
    if not np.isnan(put_skew) and put_skew > 1.3 and not np.isnan(skew_rv) and skew_rv > 1.3:
        signal = "RICH_PUT_SKEW"
    elif not np.isnan(call_skew) and call_skew > 1.3:
        signal = "RICH_CALL_SKEW"

    return {
        "atm_iv": atm_iv,
        "otm_put_iv": otm_put_iv,
        "otm_call_iv": otm_call_iv,
        "put_skew": put_skew,
        "call_skew": call_skew,
        "skew_rv_ratio": skew_rv,
        "skew_signal": signal,
    }
