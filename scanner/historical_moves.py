from __future__ import annotations

import datetime as dt
import math
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf


def _as_naive_date(value: Any) -> dt.date | None:
    if value is None:
        return None
    try:
        ts = pd.Timestamp(value)
    except Exception:
        return None
    if pd.isna(ts):
        return None
    if ts.tzinfo is not None:
        ts = ts.tz_convert(None)
    return ts.date()


def compute_historical_move_stats_from_data(
    earnings_dates: list[dt.datetime] | list[pd.Timestamp],
    price_history: pd.DataFrame,
    current_expected_move: float,
) -> dict[str, float | int]:
    if price_history.empty or "date" not in price_history.columns or "close" not in price_history.columns:
        return {
            "avg_hist_move": float("nan"),
            "max_hist_move": float("nan"),
            "num_earnings": 0,
            "move_ratio": float("nan"),
        }

    px = price_history.copy()
    px["date"] = pd.to_datetime(px["date"], errors="coerce")
    px["close"] = pd.to_numeric(px["close"], errors="coerce")
    px = px.dropna(subset=["date", "close"]).sort_values("date")
    if px.empty:
        return {
            "avg_hist_move": float("nan"),
            "max_hist_move": float("nan"),
            "num_earnings": 0,
            "move_ratio": float("nan"),
        }

    trading_dates = [d.date() for d in px["date"]]
    closes = px["close"].to_list()

    moves: list[float] = []
    for e in earnings_dates:
        ed = _as_naive_date(e)
        if ed is None:
            continue

        before_idx = None
        after_idx = None
        for i, d in enumerate(trading_dates):
            if d < ed:
                before_idx = i
            if d > ed and after_idx is None:
                after_idx = i

        if before_idx is None or after_idx is None:
            continue

        close_before = closes[before_idx]
        close_after = closes[after_idx]
        if close_before and not math.isnan(close_before) and not math.isnan(close_after):
            move = abs(close_after - close_before) / close_before
            moves.append(float(move))

    if not moves:
        return {
            "avg_hist_move": float("nan"),
            "max_hist_move": float("nan"),
            "num_earnings": 0,
            "move_ratio": float("nan"),
        }

    avg_hist_move = float(np.mean(moves))
    max_hist_move = float(np.max(moves))
    move_ratio = float(current_expected_move / avg_hist_move) if avg_hist_move > 0 else float("nan")

    return {
        "avg_hist_move": avg_hist_move,
        "max_hist_move": max_hist_move,
        "num_earnings": len(moves),
        "move_ratio": move_ratio,
    }


def compute_historical_move_stats(
    symbol: str,
    current_expected_move: float,
    obb_client: Any,
    earnings_limit: int = 8,
) -> dict[str, float | int]:
    try:
        ticker = yf.Ticker(symbol)
        earnings = ticker.get_earnings_dates(limit=earnings_limit)
    except Exception:
        return {
            "avg_hist_move": float("nan"),
            "max_hist_move": float("nan"),
            "num_earnings": 0,
            "move_ratio": float("nan"),
        }
    if earnings is None or len(earnings) == 0:
        return {
            "avg_hist_move": float("nan"),
            "max_hist_move": float("nan"),
            "num_earnings": 0,
            "move_ratio": float("nan"),
        }

    raw_idx = list(getattr(earnings, "index", []))
    earnings_idx = [e for e in raw_idx if _as_naive_date(e) is not None]
    if not earnings_idx:
        return {
            "avg_hist_move": float("nan"),
            "max_hist_move": float("nan"),
            "num_earnings": 0,
            "move_ratio": float("nan"),
        }

    first_date = _as_naive_date(min(earnings_idx))
    last_date = _as_naive_date(max(earnings_idx))
    if first_date is None or last_date is None:
        return {
            "avg_hist_move": float("nan"),
            "max_hist_move": float("nan"),
            "num_earnings": 0,
            "move_ratio": float("nan"),
        }

    start = first_date - dt.timedelta(days=7)
    end = last_date + dt.timedelta(days=7)
    out = obb_client.obb.equity.price.historical(
        symbol,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        provider="yfinance",
    )
    price_df = out.to_df() if hasattr(out, "to_df") else out

    if isinstance(price_df, pd.DataFrame) and price_df.index.name and str(price_df.index.name).lower() == "date":
        price_df = price_df.reset_index()

    cols = {str(c).lower(): c for c in price_df.columns}
    date_col = cols.get("date") or cols.get("timestamp")
    close_col = cols.get("close") or cols.get("adj_close")
    if not date_col or not close_col:
        return {
            "avg_hist_move": float("nan"),
            "max_hist_move": float("nan"),
            "num_earnings": 0,
            "move_ratio": float("nan"),
        }

    normalized = pd.DataFrame({"date": price_df[date_col], "close": price_df[close_col]})
    return compute_historical_move_stats_from_data(earnings_idx, normalized, current_expected_move)
