#!/usr/bin/env python3
"""Daily scanner entry point — single entry for scan + outputs + watchlist + tracker + alert."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from alerts import format_daily_alert
from openbb_earnings_iv_scanner import append_tracker, scan, to_markdown as generate_markdown
from watchlist import append_watchlist


def run_pipeline(args: argparse.Namespace) -> pd.DataFrame:
    df = scan(args.window_days, args.top_n, args.min_oi, args.min_vol, debug=args.debug)

    out_csv = Path(args.out_csv)
    out_md = Path(args.out_md)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(out_csv, index=False)
    md = generate_markdown(df, args)
    out_md.write_text(md, encoding="utf-8")

    append_tracker(df, Path(args.tracker_jsonl), args)

    if not df.empty:
        signaled = df[df["strategies"].str.len() > 0]
        if not signaled.empty:
            append_watchlist(signaled, path=args.watchlist_jsonl)

    if args.alert or not args.debug:
        alert = format_daily_alert(df)
        print(alert)

    print(f"Scan done. rows={len(df)}")
    print(f"CSV: {out_csv}")
    print(f"MD:  {out_md}")
    print(f"Tracker append: {args.tracker_jsonl}")

    return df


def main() -> int:
    parser = argparse.ArgumentParser(description="Options Machine — Daily Scan")
    parser.add_argument("--window-days", type=int, default=14)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--min-oi", type=int, default=0)
    parser.add_argument("--min-vol", type=int, default=0)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--alert", action="store_true", help="Print Telegram alert to stdout")
    parser.add_argument("--out-csv", default="outputs/openbb_earnings_iv_scan.csv")
    parser.add_argument("--out-md", default="outputs/openbb_earnings_iv_scan.md")
    parser.add_argument("--tracker-jsonl", default="outputs/backtest_tracker.jsonl")
    parser.add_argument("--watchlist-jsonl", default="data/watchlist.jsonl")
    args = parser.parse_args()

    run_pipeline(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
