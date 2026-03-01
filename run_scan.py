#!/usr/bin/env python3
"""Daily scanner entry point — runs scan, logs watchlist, prints alert."""
import argparse
import pandas as pd
from openbb_earnings_iv_scanner import scan
from watchlist import append_watchlist
from alerts import format_daily_alert


def main():
    parser = argparse.ArgumentParser(description="Options Machine — Daily Scan")
    parser.add_argument("--window-days", type=int, default=14)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--min-oi", type=int, default=0)
    parser.add_argument("--min-vol", type=int, default=0)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--alert", action="store_true", help="Print Telegram alert to stdout")
    args = parser.parse_args()

    df = scan(args.window_days, args.top_n, args.min_oi, args.min_vol, debug=args.debug)

    if not df.empty:
        # Only log entries that have at least one strategy signal
        signaled = df[df["strategies"].str.len() > 0]
        if not signaled.empty:
            append_watchlist(signaled)

    if args.alert or not args.debug:
        alert = format_daily_alert(df)
        print(alert)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
