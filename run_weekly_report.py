#!/usr/bin/env python3
"""Generate weekly forward test summary report."""
import json
import datetime as dt
from pathlib import Path


def load_watchlist(path: str = "data/watchlist.jsonl") -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def generate_weekly_report():
    entries = load_watchlist()
    today = dt.date.today()
    week_num = today.isocalendar()[1]
    year = today.year

    # This week's entries
    week_start = today - dt.timedelta(days=today.weekday())
    week_entries = [e for e in entries if e.get("scan_date") and
                    dt.date.fromisoformat(e["scan_date"]) >= week_start]

    # All-time stats
    resolved = [e for e in entries if e.get("outcome")]
    wins = sum(1 for e in resolved if e["outcome"] == "win")
    losses = sum(1 for e in resolved if e["outcome"] == "loss")
    total = wins + losses
    win_rate = f"{wins/total:.1%}" if total else "N/A"

    # Avg actual vs expected
    ratios = []
    for e in resolved:
        if e.get("actual_move_pct") and e.get("expected_move_pct") and e["expected_move_pct"] > 0:
            ratios.append(e["actual_move_pct"] / e["expected_move_pct"])
    avg_ratio = f"{sum(ratios)/len(ratios):.2f}x" if ratios else "N/A"

    lines = [
        f"# Weekly Forward Test Report — Week {week_num}, {year}",
        "",
        "## Summary",
        f"- Report date: {today.isoformat()}",
        f"- Stocks scanned this week: {len(week_entries)}",
        f"- Total recommendations (all time): {len(entries)}",
        f"- Outcomes recorded: {total}",
        f"- Win rate: {win_rate} ({wins}W / {losses}L)",
        f"- Avg actual/expected move ratio: {avg_ratio}",
        "",
        "## This Week's Picks",
        "",
        "| Symbol | Earnings | IV/RV | FF | Strategies | Outcome |",
        "|--------|----------|-------|----|------------|---------|",
    ]

    for e in week_entries:
        sym = e.get("symbol", "?")
        edate = e.get("earnings_date", "?")
        iv_rv = f"{e['iv_rv_ratio']:.2f}" if e.get("iv_rv_ratio") else "-"
        ff = f"{e['forward_factor']:.2f}" if e.get("forward_factor") else "-"
        strats = e.get("strategies", "-") or "-"
        outcome = e.get("outcome", "pending") or "pending"
        emoji = "✅" if outcome == "win" else "❌" if outcome == "loss" else "⏳"
        lines.append(f"| {sym} | {edate} | {iv_rv} | {ff} | {strats} | {emoji} {outcome} |")

    if resolved:
        lines += [
            "",
            "## Cumulative Results (All Time)",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total recommendations | {len(entries)} |",
            f"| Outcomes recorded | {total} |",
            f"| Win rate | {win_rate} |",
            f"| Wins | {wins} |",
            f"| Losses | {losses} |",
            f"| Avg actual/expected | {avg_ratio} |",
        ]

    lines += [
        "",
        "---",
        "*Strategy: Volatility Vibes earnings IV selling + Forward Factor + Skew*",
        "*Type: Forward test (paper trading)*",
    ]

    report = "\n".join(lines)

    # Save to data/weekly/
    weekly_dir = Path("data/weekly")
    weekly_dir.mkdir(parents=True, exist_ok=True)
    report_path = weekly_dir / f"{year}-W{week_num:02d}.md"
    report_path.write_text(report, encoding="utf-8")

    # Also save to brain
    brain_dir = Path("/home/jy/.openclaw/brain/weekly-reports")
    brain_dir.mkdir(parents=True, exist_ok=True)
    (brain_dir / f"{year}-W{week_num:02d}.md").write_text(report, encoding="utf-8")

    print(report)
    print(f"\nSaved to: {report_path}")
    return report


if __name__ == "__main__":
    generate_weekly_report()
