"""Event volatility decomposition — per Volatility Vibes methodology."""

import math


def decompose_event_vol(iv30: float, rv30: float, dte: int) -> dict:
    """Decompose implied vol into ambient + event components.

    iv30: 30-day implied volatility (annualized)
    rv30: 30-day realized volatility (annualized, proxy for ambient vol)
    dte: days to earnings

    Returns dict with event_vol (annualized), ambient_vol, event_premium_pct.
    """
    if math.isnan(iv30) or math.isnan(rv30) or dte <= 0:
        return {
            "event_vol": float("nan"),
            "ambient_vol": rv30,
            "event_premium_pct": float("nan"),
        }

    iv_daily_var = (iv30**2) / 252.0
    ambient_daily_var = (rv30**2) / 252.0

    total_var = iv_daily_var * dte
    ambient_var = ambient_daily_var * max(0, dte - 1)

    event_var = max(0.0, total_var - ambient_var)
    event_vol_daily = math.sqrt(event_var)

    event_vol_ann = event_vol_daily * math.sqrt(252)
    event_premium = (event_vol_ann / rv30 - 1.0) if rv30 > 0 else float("nan")

    return {
        "event_vol": event_vol_ann,
        "ambient_vol": rv30,
        "event_premium_pct": event_premium,
    }
