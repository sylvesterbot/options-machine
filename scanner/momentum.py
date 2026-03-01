"""Momentum filter for Strategy C directional confirmation."""
import pandas as pd


def compute_momentum(price_df: pd.DataFrame, window: int = 20) -> dict:
    if len(price_df) < window + 1:
        return {"momentum_pct": float("nan"), "momentum_dir": "NEUTRAL"}
    current = float(price_df["close"].iloc[-1])
    past = float(price_df["close"].iloc[-(window + 1)])
    mom = (current - past) / past
    direction = "NEUTRAL"
    if mom > 0.02:
        direction = "BULLISH"
    elif mom < -0.02:
        direction = "BEARISH"
    return {"momentum_pct": mom, "momentum_dir": direction}
