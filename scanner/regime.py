"""VIX regime awareness — per Volatility Vibes methodology."""
from __future__ import annotations


def classify_regime(vix_level: float) -> dict:
    """Classify market regime based on VIX level."""
    if vix_level < 15:
        return {
            "regime": "CALM",
            "allocation_multiplier": 1.0,
            "stop_loss_multiplier": 0.8,
            "note": "Low vol environment — full allocation",
        }
    elif vix_level < 25:
        return {
            "regime": "NORMAL",
            "allocation_multiplier": 1.0,
            "stop_loss_multiplier": 1.0,
            "note": "Normal volatility — standard allocation",
        }
    elif vix_level < 35:
        return {
            "regime": "ELEVATED",
            "allocation_multiplier": 0.5,
            "stop_loss_multiplier": 1.3,
            "note": "Elevated uncertainty — reduce allocation by 50%",
        }
    else:
        return {
            "regime": "CRISIS",
            "allocation_multiplier": 0.0,
            "stop_loss_multiplier": 0.0,
            "note": "Crisis mode — halt new positions",
        }


def get_vix_level() -> float:
    """Attempt to fetch current VIX. Returns NaN if unavailable."""
    try:
        import yfinance as yf

        vix = yf.Ticker("^VIX")
        hist = vix.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return float("nan")
