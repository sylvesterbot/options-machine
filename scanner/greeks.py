from __future__ import annotations

import math
from typing import Literal

from scipy.stats import norm
import pandas as pd


OptionType = Literal["call", "put"]


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        raise ValueError("Invalid BSM inputs")
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def bsm_price(S: float, K: float, T: float, r: float, sigma: float, option_type: OptionType) -> float:
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    if option_type == "call":
        return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def bsm_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: OptionType) -> dict[str, float]:
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    pdf = norm.pdf(d1)
    if option_type == "call":
        delta = norm.cdf(d1)
        theta = (-S * pdf * sigma / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365.0
    else:
        delta = norm.cdf(d1) - 1
        theta = (-S * pdf * sigma / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365.0
    gamma = pdf / (S * sigma * math.sqrt(T))
    vega = S * pdf * math.sqrt(T) / 100.0
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta}


def enrich_chain_with_greeks(chain: pd.DataFrame, spot: float, r: float = 0.05) -> pd.DataFrame:
    if chain.empty:
        return chain.copy()
    c = chain.copy()
    today = pd.Timestamp.now("UTC").date()
    c["expiration"] = pd.to_datetime(c["expiration"], errors="coerce").dt.date
    c["T"] = c["expiration"].apply(lambda d: max((d - today).days / 365.0, 1 / 365.0))
    c["implied_volatility"] = pd.to_numeric(c.get("implied_volatility"), errors="coerce").fillna(0.2)
    c["strike"] = pd.to_numeric(c["strike"], errors="coerce")
    c["option_type"] = c["option_type"].astype(str).str.lower().str[0].map({"c": "call", "p": "put"})

    deltas, gammas, vegas, thetas = [], [], [], []
    for _, row in c.iterrows():
        try:
            g = bsm_greeks(spot, float(row["strike"]), float(row["T"]), r, float(row["implied_volatility"]), row["option_type"])
        except Exception:
            g = {"delta": float("nan"), "gamma": float("nan"), "vega": float("nan"), "theta": float("nan")}
        deltas.append(g["delta"])
        gammas.append(g["gamma"])
        vegas.append(g["vega"])
        thetas.append(g["theta"])
    c["delta"] = deltas
    c["gamma"] = gammas
    c["vega"] = vegas
    c["theta"] = thetas
    return c


def compute_position_greeks(chain: pd.DataFrame) -> dict[str, float]:
    if chain.empty:
        return {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
    qty_col = chain["position_qty"] if "position_qty" in chain.columns else pd.Series([1.0]*len(chain), index=chain.index)
    qty = pd.to_numeric(qty_col, errors="coerce").fillna(1.0)
    return {
        "delta": float((pd.to_numeric(chain.get("delta"), errors="coerce").fillna(0.0) * qty).sum()),
        "gamma": float((pd.to_numeric(chain.get("gamma"), errors="coerce").fillna(0.0) * qty).sum()),
        "vega": float((pd.to_numeric(chain.get("vega"), errors="coerce").fillna(0.0) * qty).sum()),
        "theta": float((pd.to_numeric(chain.get("theta"), errors="coerce").fillna(0.0) * qty).sum()),
    }
