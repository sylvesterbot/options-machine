"""Strategy B: Forward Factor — detect term structure dislocations."""
import datetime as dt
import numpy as np
import pandas as pd


def compute_forward_factor(chain: pd.DataFrame, spot: float) -> dict:
    today = dt.date.today()
    expiries = sorted([e for e in chain["expiration"].unique() if e > today])
    EMPTY = {"forward_factor": float("nan"), "ff_signal": "NONE",
             "front_iv": float("nan"), "back_iv": float("nan"),
             "forward_iv": float("nan"), "front_dte": 0, "back_dte": 0}

    if len(expiries) < 2:
        return EMPTY

    front_target = today + dt.timedelta(days=30)
    back_target = today + dt.timedelta(days=90)
    front_exp = min(expiries, key=lambda e: abs((e - front_target).days))
    back_candidates = [e for e in expiries if e > front_exp]
    if not back_candidates:
        return EMPTY
    back_exp = min(back_candidates, key=lambda e: abs((e - back_target).days))

    def atm_iv(exp):
        e_df = chain[chain["expiration"] == exp].copy()
        if e_df.empty:
            return None
        e_df["dist"] = (e_df["strike"] - spot).abs()
        atm = e_df[e_df["dist"] == e_df["dist"].min()]
        iv = atm["implied_volatility"].dropna().mean()
        return float(iv) if not np.isnan(iv) else None

    front_iv = atm_iv(front_exp)
    back_iv = atm_iv(back_exp)
    if not front_iv or not back_iv or front_iv <= 0 or back_iv <= 0:
        return EMPTY

    T_f = (front_exp - today).days / 365.0
    T_b = (back_exp - today).days / 365.0
    if T_b <= T_f or T_f <= 0:
        return EMPTY

    fwd_var = (back_iv**2 * T_b - front_iv**2 * T_f) / (T_b - T_f)
    fwd_iv = np.sqrt(max(fwd_var, 0.0001))
    ff = (front_iv - fwd_iv) / fwd_iv

    signal = "NONE"
    if ff >= 0.2:
        signal = "STRONG"
    elif ff >= 0.1:
        signal = "MODERATE"

    return {
        "forward_factor": float(ff),
        "ff_signal": signal,
        "front_iv": front_iv,
        "back_iv": back_iv,
        "forward_iv": float(fwd_iv),
        "front_dte": (front_exp - today).days,
        "back_dte": (back_exp - today).days,
    }
