"""Strategy B: Forward Factor — detect term structure dislocations with multi-pair tenors."""
import datetime as dt
import numpy as np
import pandas as pd


EMPTY = {
    "forward_factor": float("nan"),
    "ff_30_60": float("nan"),
    "ff_60_90": float("nan"),
    "ff_30_90": float("nan"),
    "ff_best": float("nan"),
    "ff_best_pair": "NONE",
    "ff_signal": "NONE",
    "front_iv": float("nan"),
    "back_iv": float("nan"),
    "forward_iv": float("nan"),
    "front_dte": 0,
    "back_dte": 0,
    "pair_expiries": {},
}


def compute_forward_factor(chain: pd.DataFrame, spot: float, as_of_date: dt.date | None = None) -> dict:
    today = as_of_date or dt.date.today()
    expiries = sorted([e for e in chain["expiration"].unique() if e > today])
    if len(expiries) < 2:
        return dict(EMPTY)

    def nearest(days: int):
        tgt = today + dt.timedelta(days=days)
        return min(expiries, key=lambda e: abs((e - tgt).days))

    exp_30, exp_60, exp_90 = nearest(30), nearest(60), nearest(90)

    def atm_iv(exp):
        e_df = chain[chain["expiration"] == exp].copy()
        if e_df.empty:
            return None
        e_df["dist"] = (e_df["strike"] - spot).abs()
        atm = e_df[e_df["dist"] == e_df["dist"].min()]
        iv = atm["implied_volatility"].dropna().mean()
        return float(iv) if not np.isnan(iv) else None

    iv_30, iv_60, iv_90 = atm_iv(exp_30), atm_iv(exp_60), atm_iv(exp_90)

    def ff_from_pair(front_exp, back_exp, front_iv, back_iv):
        if not front_iv or not back_iv or front_iv <= 0 or back_iv <= 0:
            return float("nan")
        tf = (front_exp - today).days / 365.0
        tb = (back_exp - today).days / 365.0
        if tb <= tf or tf <= 0:
            return float("nan")
        fwd_var = (back_iv**2 * tb - front_iv**2 * tf) / (tb - tf)
        fwd_iv = np.sqrt(max(fwd_var, 0.0001))
        return float((front_iv - fwd_iv) / fwd_iv)

    ff_30_60 = ff_from_pair(exp_30, exp_60, iv_30, iv_60)
    ff_60_90 = ff_from_pair(exp_60, exp_90, iv_60, iv_90)
    ff_30_90 = ff_from_pair(exp_30, exp_90, iv_30, iv_90)

    pairs = {"30-60": ff_30_60, "60-90": ff_60_90, "30-90": ff_30_90}
    valid = {k: v for k, v in pairs.items() if not np.isnan(v)}
    if not valid:
        out = dict(EMPTY)
        out["ff_30_60"] = ff_30_60
        out["ff_60_90"] = ff_60_90
        out["ff_30_90"] = ff_30_90
        out["pair_expiries"] = {
            "30-60": [str(exp_30), str(exp_60)],
            "60-90": [str(exp_60), str(exp_90)],
            "30-90": [str(exp_30), str(exp_90)],
        }
        return out

    ff_best_pair, ff_best = max(valid.items(), key=lambda kv: kv[1])
    signal = "NONE"
    if ff_best >= 0.2:
        signal = "STRONG"
    elif ff_best >= 0.1:
        signal = "MODERATE"

    return {
        "forward_factor": float(ff_best),
        "ff_30_60": ff_30_60,
        "ff_60_90": ff_60_90,
        "ff_30_90": ff_30_90,
        "ff_best": float(ff_best),
        "ff_best_pair": ff_best_pair,
        "ff_signal": signal,
        "front_iv": iv_30 if iv_30 is not None else float("nan"),
        "back_iv": iv_90 if iv_90 is not None else float("nan"),
        "forward_iv": float("nan"),
        "front_dte": (exp_30 - today).days,
        "back_dte": (exp_90 - today).days,
        "pair_expiries": {
            "30-60": [str(exp_30), str(exp_60)],
            "60-90": [str(exp_60), str(exp_90)],
            "30-90": [str(exp_30), str(exp_90)],
        },
    }
