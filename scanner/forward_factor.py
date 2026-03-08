"""Strategy B: Forward Factor — detect term structure dislocations with multi-pair tenors."""
import datetime as dt
import numpy as np
import pandas as pd

from scanner.signal_history import get_ticker_zscore


EMPTY = {
    "forward_factor": float("nan"),
    "ff_30_60": float("nan"),
    "ff_60_90": float("nan"),
    "ff_30_90": float("nan"),
    "ff_best": float("nan"),
    "ff_best_pair": "NONE",
    "ff_signal": "NONE",
    "ff_signal_raw": "NONE",
    "ff_signal_adaptive": "NONE",
    "ff_zscore": float("nan"),
    "front_iv": float("nan"),
    "back_iv": float("nan"),
    "forward_iv": float("nan"),
    "front_dte": 0,
    "back_dte": 0,
    "nearest_gap_30": float("nan"),
    "nearest_gap_60": float("nan"),
    "nearest_gap_90": float("nan"),
    "pair_expiries": {},
}


def compute_forward_factor(chain: pd.DataFrame, spot: float, as_of_date: dt.date | None = None, symbol: str = "", signal_history_path: str = "",
                           ff_strong_threshold: float = 0.20, ff_moderate_threshold: float = 0.10) -> dict:
    today = as_of_date or dt.date.today()
    adaptive_strong_z = 1.0
    adaptive_moderate_z = 0.3
    prefer_60_90_min = 0.1
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
        # Prefer delta-based (35-50Δ) if delta column exists
        if "delta" in e_df.columns:
            e_df["abs_delta"] = pd.to_numeric(e_df["delta"], errors="coerce").abs()
            atm_delta = e_df[(e_df["abs_delta"] >= 0.35) & (e_df["abs_delta"] <= 0.50)]
            if not atm_delta.empty:
                iv = pd.to_numeric(atm_delta["implied_volatility"], errors="coerce").dropna().mean()
                return float(iv) if not np.isnan(iv) else None
        # Fallback: nearest strike distance
        e_df["dist"] = (e_df["strike"] - spot).abs()
        atm = e_df[e_df["dist"] == e_df["dist"].min()]
        iv = pd.to_numeric(atm["implied_volatility"], errors="coerce").dropna().mean()
        return float(iv) if not np.isnan(iv) else None

    iv_30, iv_60, iv_90 = atm_iv(exp_30), atm_iv(exp_60), atm_iv(exp_90)

    def ff_from_pair(front_exp, back_exp, front_iv, back_iv):
        if not front_iv or not back_iv or front_iv <= 0 or back_iv <= 0:
            return float("nan"), float("nan")
        tf = (front_exp - today).days / 365.0
        tb = (back_exp - today).days / 365.0
        if tb <= tf or tf <= 0:
            return float("nan"), float("nan")
        fwd_var = (back_iv**2 * tb - front_iv**2 * tf) / (tb - tf)
        fwd_iv = np.sqrt(max(fwd_var, 0.0001))
        ff = float((front_iv - fwd_iv) / fwd_iv)
        return ff, float(fwd_iv)

    ff_30_60, fwd_30_60 = ff_from_pair(exp_30, exp_60, iv_30, iv_60)
    ff_60_90, fwd_60_90 = ff_from_pair(exp_60, exp_90, iv_60, iv_90)
    ff_30_90, fwd_30_90 = ff_from_pair(exp_30, exp_90, iv_30, iv_90)

    pairs = {"30-60": ff_30_60, "60-90": ff_60_90, "30-90": ff_30_90}
    valid = {k: v for k, v in pairs.items() if not np.isnan(v)}
    if not valid:
        out = dict(EMPTY)
        out.update({
            "ff_30_60": ff_30_60,
            "ff_60_90": ff_60_90,
            "ff_30_90": ff_30_90,
            "nearest_gap_30": abs((exp_30 - (today + dt.timedelta(days=30))).days),
            "nearest_gap_60": abs((exp_60 - (today + dt.timedelta(days=60))).days),
            "nearest_gap_90": abs((exp_90 - (today + dt.timedelta(days=90))).days),
            "pair_expiries": {"30-60": [str(exp_30), str(exp_60)], "60-90": [str(exp_60), str(exp_90)], "30-90": [str(exp_30), str(exp_90)]},
        })
        return out

    # Amendment 5 preference
    if not np.isnan(ff_60_90) and ff_60_90 >= prefer_60_90_min:
        ff_best_pair, ff_best = "60-90", ff_60_90
    else:
        ff_best_pair, ff_best = max(valid.items(), key=lambda kv: kv[1])

    ff_signal_raw = "NONE"
    if ff_best >= ff_strong_threshold:
        ff_signal_raw = "STRONG"
    elif ff_best >= ff_moderate_threshold:
        ff_signal_raw = "MODERATE"

    ff_z = float("nan")
    ff_signal_adaptive = "NONE"
    if symbol and signal_history_path:
        ff_z = get_ticker_zscore(symbol, "ff_best", ff_best, path=signal_history_path)
        if not np.isnan(ff_z):
            if ff_z >= adaptive_strong_z:
                ff_signal_adaptive = "STRONG"
            elif ff_z >= adaptive_moderate_z:
                ff_signal_adaptive = "MODERATE"

    ff_signal = ff_signal_adaptive if ff_signal_adaptive != "NONE" else ff_signal_raw

    forward_iv_map = {"30-60": fwd_30_60, "60-90": fwd_60_90, "30-90": fwd_30_90}

    return {
        "forward_factor": float(ff_best),
        "ff_30_60": ff_30_60,
        "ff_60_90": ff_60_90,
        "ff_30_90": ff_30_90,
        "ff_best": float(ff_best),
        "ff_best_pair": ff_best_pair,
        "ff_signal": ff_signal,
        "ff_signal_raw": ff_signal_raw,
        "ff_signal_adaptive": ff_signal_adaptive,
        "ff_zscore": ff_z,
        "front_iv": iv_30 if iv_30 is not None else float("nan"),
        "back_iv": iv_90 if iv_90 is not None else float("nan"),
        "forward_iv": float(forward_iv_map.get(ff_best_pair, float("nan"))),
        "front_dte": (exp_30 - today).days,
        "back_dte": (exp_90 - today).days,
        "nearest_gap_30": abs((exp_30 - (today + dt.timedelta(days=30))).days),
        "nearest_gap_60": abs((exp_60 - (today + dt.timedelta(days=60))).days),
        "nearest_gap_90": abs((exp_90 - (today + dt.timedelta(days=90))).days),
        "pair_expiries": {
            "30-60": [str(exp_30), str(exp_60)],
            "60-90": [str(exp_60), str(exp_90)],
            "30-90": [str(exp_30), str(exp_90)],
        },
    }
