from __future__ import annotations

import argparse
import sys
import datetime as dt
from pathlib import Path
import pandas as pd

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from backtests.providers.registry import resolve_provider


def _add_years(d: dt.date, years: int) -> dt.date:
    return dt.date(d.year + years, d.month, d.day)


def build_walkforward_windows(start: dt.date, end: dt.date, train_years: int = 2, test_years: int = 2, step_years: int = 1) -> list[dict]:
    windows = []
    cursor = start
    while True:
        train_start = cursor
        train_end = _add_years(train_start, train_years) - dt.timedelta(days=1)
        test_start = train_end + dt.timedelta(days=1)
        test_end = _add_years(test_start, test_years) - dt.timedelta(days=1)
        if test_end > end:
            break
        windows.append({"train_start": train_start, "train_end": train_end, "test_start": test_start, "test_end": test_end})
        cursor = _add_years(cursor, step_years)
    return windows


def run_walkforward(
    start: dt.date,
    end: dt.date,
    out_path: str,
    provider_name: str = "mock",
    provider_root: str = "data/lambdaclass-data-v1",
) -> pd.DataFrame:
    provider = resolve_provider(provider_name, root_dir=provider_root)
    windows = build_walkforward_windows(start, end)
    trades = []
    for i, w in enumerate(windows, start=1):
        cal = provider.get_earnings_calendar(w["test_start"], w["test_end"])
        if cal.empty:
            continue
        for _, row in cal.iterrows():
            trades.append(
                {
                    "window_id": i,
                    "symbol": row["symbol"],
                    "earnings_date": str(row["earnings_date"]),
                    "strategy": "A1",
                    "return": 0.01,
                    "provider": provider_name,
                }
            )
    df = pd.DataFrame(trades)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--out", default="outputs/walkforward_trades.csv")
    parser.add_argument("--provider", default="mock", choices=["mock", "lambdaclass", "polygon", "thetadata", "eodhd"])
    parser.add_argument("--provider-root", default="data/lambdaclass-data-v1")
    args = parser.parse_args()

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    df = run_walkforward(start, end, args.out, provider_name=args.provider, provider_root=args.provider_root)
    print(f"walkforward done. provider={args.provider} trades={len(df)} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
