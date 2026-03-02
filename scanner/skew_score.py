"""Strategy C: Skew scoring — delta-based OTM selection with RV-edge filter."""
import datetime as dt
import numpy as np
import pandas as pd

from scanner.greeks import enrich_chain_with_greeks


def compute_skew_score(chain: pd.DataFrame, spot: float, rv30: float) -> dict:
    today = dt.date.today()
    expiries = sorted([e for e in chain["expiration"].unique() if e > today])
    EMPTY = {
        "atm_iv": float("nan"),
        "otm_put_iv": float("nan"),
        "otm_call_iv": float("nan"),
        "put_skew": float("nan"),
        "call_skew": float("nan"),
        "skew_rv_ratio": float("nan"),
        "otm_put_strike": float("nan"),
        "otm_call_strike": float("nan"),
        "otm_put_delta": float("nan"),
        "otm_call_delta": float("nan"),
        "rv_edge_put": float("nan"),
        "rv_edge_call": float("nan"),
        "skew_signal": "NONE",
    }

    if not expiries:
        return EMPTY

    target = today + dt.timedelta(days=30)
    exp = min(expiries, key=lambda e: abs((e - target).days))
    e_df = chain[chain["expiration"] == exp].copy()
    if e_df.empty:
        return EMPTY

    e_df = enrich_chain_with_greeks(e_df, spot=spot)
    e_df["dist"] = (e_df["strike"] - spot).abs()
    atm_strike = e_df.loc[e_df["dist"].idxmin(), "strike"]

    atm_options = e_df[e_df["strike"] == atm_strike]
    atm_iv = float(atm_options["implied_volatility"].dropna().mean()) if "implied_volatility" in atm_options else float("nan")

    puts = e_df[e_df["option_type"].str.lower().str.startswith("p")].copy()
    calls = e_df[e_df["option_type"].str.lower().str.startswith("c")].copy()

    otm_put_iv = otm_call_iv = float("nan")
    otm_put_strike = otm_call_strike = float("nan")
    otm_put_delta = otm_call_delta = float("nan")

    if not puts.empty:
        puts["delta_target_dist"] = (puts["delta"] + 0.25).abs()
        p_row = puts.loc[puts["delta_target_dist"].idxmin()]
        otm_put_iv = float(p_row.get("implied_volatility", float("nan")))
        otm_put_strike = float(p_row.get("strike", float("nan")))
        otm_put_delta = float(p_row.get("delta", float("nan")))

    if not calls.empty:
        calls["delta_target_dist"] = (calls["delta"] - 0.25).abs()
        c_row = calls.loc[calls["delta_target_dist"].idxmin()]
        otm_call_iv = float(c_row.get("implied_volatility", float("nan")))
        otm_call_strike = float(c_row.get("strike", float("nan")))
        otm_call_delta = float(c_row.get("delta", float("nan")))

    put_skew = otm_put_iv / atm_iv if atm_iv and atm_iv > 0 else float("nan")
    call_skew = otm_call_iv / atm_iv if atm_iv and atm_iv > 0 else float("nan")
    skew_rv = otm_put_iv / rv30 if rv30 and rv30 > 0 and not np.isnan(rv30) else float("nan")
    rv_edge_put = (otm_put_iv - rv30) if rv30 and not np.isnan(otm_put_iv) else float("nan")
    rv_edge_call = (otm_call_iv - rv30) if rv30 and not np.isnan(otm_call_iv) else float("nan")

    signal = "NONE"
    if not np.isnan(put_skew) and put_skew > 1.3 and not np.isnan(skew_rv) and skew_rv > 1.3 and (not np.isnan(rv_edge_put) and rv_edge_put > 0):
        signal = "RICH_PUT_SKEW"
    elif not np.isnan(call_skew) and call_skew > 1.3 and (not np.isnan(rv_edge_call) and rv_edge_call > 0):
        signal = "RICH_CALL_SKEW"

    return {
        "atm_iv": atm_iv,
        "otm_put_iv": otm_put_iv,
        "otm_call_iv": otm_call_iv,
        "put_skew": put_skew,
        "call_skew": call_skew,
        "skew_rv_ratio": skew_rv,
        "otm_put_strike": otm_put_strike,
        "otm_call_strike": otm_call_strike,
        "otm_put_delta": otm_put_delta,
        "otm_call_delta": otm_call_delta,
        "rv_edge_put": rv_edge_put,
        "rv_edge_call": rv_edge_call,
        "skew_signal": signal,
    }
