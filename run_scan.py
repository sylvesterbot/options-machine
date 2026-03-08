#!/usr/bin/env python3
"""Daily scanner entry point — single entry for scan + outputs + watchlist + tracker + alert."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from alerts import format_daily_alert, format_trade_alert, send_discord_webhook
from openbb_earnings_iv_scanner import append_tracker, scan, analyze_single_ticker, to_markdown as generate_markdown
from watchlist import append_watchlist


def run_pipeline(args: argparse.Namespace) -> pd.DataFrame:
    if getattr(args, 'analyze', None):
        ticker = args.analyze.strip().upper()
        print(f"\n=== ANALYZING {ticker} ===\n")
        result = analyze_single_ticker(ticker, args)
        if result is not None:
            if hasattr(result, "items"):
                for k, v in result.items():
                    print(f"  {k}: {v}")
        return pd.DataFrame()

    df = scan(
        args.window_days,
        args.top_n,
        args.min_oi,
        args.min_vol,
        debug=args.debug,
        capital=args.capital,
        default_alloc=args.default_alloc,
        portfolio_dd=args.portfolio_dd,
    )

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

    if getattr(args, 'iron_fly', False) and not df.empty and "tier" in df.columns:
        from scanner.iron_fly import calculate_iron_fly
        from openbb_earnings_iv_scanner import OpenBBClient
        t1 = df[df["tier"] == 1]
        for _, row in t1.iterrows():
            try:
                client = OpenBBClient()
                chain = client.get_options_chain(row["symbol"])
                fly = calculate_iron_fly(chain, spot=row["spot"])
                if not fly["error"]:
                    print(f"\n  IRON FLY for {row['symbol']}:")
                    print(f"    SHORT: ${fly['short_put_strike']}P / ${fly['short_call_strike']}C = ${fly['total_credit']} credit")
                    print(f"    LONG:  ${fly['long_put_strike']}P / ${fly['long_call_strike']}C = ${fly['total_debit']} debit")
                    print(f"    Net: ${fly['net_credit']} | Max loss: ${fly['max_loss']} | R:R 1:{fly['risk_reward_ratio']}")
                    print(f"    BEs: {fly['lower_breakeven']} - {fly['upper_breakeven']}")
            except Exception as e:
                print(f"  Iron Fly error for {row['symbol']}: {e}")

    webhook = getattr(args, "discord_webhook", "")
    if webhook and not df.empty:
        signaled = df[df["strategies"].fillna("").astype(str).str.len() > 0]
        ok_all = True
        for _, row in signaled.iterrows():
            message = format_trade_alert(row.to_dict())
            ok = send_discord_webhook(message, webhook)
            ok_all = ok_all and ok
        print(f"Discord webhook: {'ok' if ok_all else 'failed'}")

    print(f"Scan done. rows={len(df)}")
    print(f"CSV: {out_csv}")
    print(f"MD:  {out_md}")
    print(f"Tracker append: {args.tracker_jsonl}")

    return df


def main() -> int:
    parser = argparse.ArgumentParser(description="Options Machine — Daily Scan")
    parser.add_argument("--window-days", type=int, default=14)
    parser.add_argument("-a", "--analyze", default="", help="Analyze a single ticker symbol")
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--min-oi", type=int, default=0)
    parser.add_argument("--min-vol", type=int, default=0)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--alert", action="store_true", help="Print Telegram alert to stdout")
    parser.add_argument("--out-csv", default="outputs/openbb_earnings_iv_scan.csv")
    parser.add_argument("--out-md", default="outputs/openbb_earnings_iv_scan.md")
    parser.add_argument("--tracker-jsonl", default="outputs/backtest_tracker.jsonl")
    parser.add_argument("--watchlist-jsonl", default="data/watchlist.jsonl")
    parser.add_argument("--capital", type=float, default=None)
    parser.add_argument("--default-alloc", type=float, default=0.04)
    parser.add_argument("--portfolio-dd", type=float, default=0.0)
    parser.add_argument("--discord-webhook", default="", help="Optional Discord webhook URL for trade alert push")
    parser.add_argument("--iron-fly", "-i", action="store_true", help="Calculate Iron Fly for Tier 1 candidates")
    args = parser.parse_args()

    run_pipeline(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
