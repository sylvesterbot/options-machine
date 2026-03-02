from __future__ import annotations

import datetime as dt
import pandas as pd


def select_a1_contract(options_chain: pd.DataFrame, spot: float, entry_date: dt.date, exit_date: dt.date) -> dict:
    chain = options_chain.copy()
    chain = chain[(chain["expiration"] > exit_date)]
    chain["dte"] = (chain["expiration"] - entry_date).dt.days if hasattr(chain["expiration"], 'dt') else chain["expiration"].apply(lambda d: (d - entry_date).days)
    chain = chain[(chain["dte"] >= 21) & (chain["dte"] <= 45)]
    if chain.empty:
        raise ValueError("No valid expiration in 21-45 DTE window after exit date")

    expiries = sorted(chain["expiration"].unique())
    chosen_exp = expiries[0]
    sub = chain[chain["expiration"] == chosen_exp].copy()
    sub["dist"] = (sub["strike"] - spot).abs()
    strike = float(sub.loc[sub["dist"].idxmin(), "strike"])
    return {"expiration": chosen_exp, "strike": strike}
