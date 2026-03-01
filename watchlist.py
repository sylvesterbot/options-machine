"""Log scan recommendations to watchlist JSONL for forward testing."""
import json
import datetime as dt
from pathlib import Path
import pandas as pd


def append_watchlist(df: pd.DataFrame, path: str = "data/watchlist.jsonl"):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    scan_date = dt.date.today().isoformat()
    counter = 0
    with p.open("a", encoding="utf-8") as f:
        for _, row in df.iterrows():
            d = row.to_dict()
            # Convert NaN to None for JSON
            for k, v in d.items():
                try:
                    if pd.isna(v):
                        d[k] = None
                except (TypeError, ValueError):
                    pass
            entry = {
                "id": f"REC-{scan_date}-{counter:03d}",
                "scan_date": scan_date,
                "symbol": d.get("symbol"),
                "earnings_date": d.get("earnings_date"),
                "strategies": d.get("strategies", ""),
                "iv_rv_ratio": d.get("iv_rv_ratio"),
                "forward_factor": d.get("forward_factor"),
                "ff_signal": d.get("ff_signal"),
                "put_skew": d.get("put_skew"),
                "skew_signal": d.get("skew_signal"),
                "momentum_dir": d.get("momentum_dir"),
                "spot_at_scan": d.get("spot"),
                "iv30": d.get("iv30_proxy"),
                "rv30": d.get("rv30"),
                "expected_move_pct": d.get("expected_move_pct"),
                "outcome": None,
                "actual_move_pct": None,
                "close_after_earnings": None,
            }
            f.write(json.dumps(entry) + "\n")
            counter += 1
    print(f"Watchlist: appended {counter} entries to {path}")
