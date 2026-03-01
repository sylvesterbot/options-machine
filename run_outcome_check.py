#!/usr/bin/env python3
"""Check post-earnings outcomes for watchlist entries."""
import json
import datetime as dt
from pathlib import Path

import pandas as pd


def load_watchlist(path: str = "data/watchlist.jsonl") -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    entries = []
    for line in p.read_text().splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def save_watchlist(entries: list[dict], path: str = "data/watchlist.jsonl"):
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def check_outcomes(debug: bool = False):
    from openbb import obb

    entries = load_watchlist()
    today = dt.date.today()
    updated = 0
    alerts = []

    for e in entries:
        if e.get("outcome") is not None:
            continue
        edate = e.get("earnings_date")
        if not edate:
            continue
        edate = dt.date.fromisoformat(str(edate))
        # Check outcomes 1 trading day after earnings
        if today <= edate:
            continue

        symbol = e["symbol"]
        spot_at_scan = e.get("spot_at_scan")
        if not spot_at_scan:
            continue

        try:
            res = obb.equity.price.historical(
                symbol, start_date=(edate - dt.timedelta(days=5)).isoformat(),
                end_date=(edate + dt.timedelta(days=5)).isoformat(),
                provider="yfinance",
            )
            df = res.to_dataframe().reset_index()
            df["date"] = pd.to_datetime(df["date"]).dt.date

            # Get close before and after earnings
            before = df[df["date"] <= edate]["close"]
            after = df[df["date"] > edate]["close"]

            if before.empty or after.empty:
                continue

            close_before = float(before.iloc[-1])
            close_after = float(after.iloc[0])
            actual_move = abs(close_after - close_before) / close_before
            expected = e.get("expected_move_pct")

            if expected and not pd.isna(expected) and expected > 0:
                outcome = "win" if actual_move < expected else "loss"
            else:
                # Fallback: win if IV/RV was high and actual move < 5%
                outcome = "win" if actual_move < 0.05 else "loss"

            e["outcome"] = outcome
            e["actual_move_pct"] = round(actual_move, 6)
            e["close_after_earnings"] = round(close_after, 2)
            updated += 1

            alerts.append({
                "symbol": symbol,
                "earnings_date": str(edate),
                "expected_move": expected,
                "actual_move": actual_move,
                "outcome": outcome,
            })

            if debug:
                print(f"[outcome] {symbol}: expected={expected:.3%}, actual={actual_move:.3%} → {outcome}")

        except Exception as exc:
            if debug:
                print(f"[outcome] {symbol}: error — {exc}")

    if updated:
        save_watchlist(entries)
        print(f"Updated {updated} outcomes")

    # Print alerts for Telegram
    if alerts:
        print("\n📈 Outcome Updates:")
        wins = sum(1 for a in alerts if a["outcome"] == "win")
        losses = len(alerts) - wins
        for a in alerts:
            emoji = "✅" if a["outcome"] == "win" else "❌"
            exp = f"{a['expected_move']:.1%}" if a["expected_move"] else "?"
            act = f"{a['actual_move']:.1%}"
            print(f"{emoji} {a['symbol']} ({a['earnings_date']}): expected {exp}, actual {act}")

        # Running record
        all_entries = load_watchlist()
        total_wins = sum(1 for e in all_entries if e.get("outcome") == "win")
        total_losses = sum(1 for e in all_entries if e.get("outcome") == "loss")
        total = total_wins + total_losses
        wr = f"{total_wins/total:.1%}" if total else "N/A"
        print(f"\nRunning record: {total_wins}W / {total_losses}L ({wr})")
    else:
        print("No new outcomes to check")

    return alerts


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    check_outcomes(debug=args.debug)
