"""Trade Journal — tracks scanner signals and their outcomes."""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

JOURNAL_PATH = Path("outputs/trade_journal.csv")
JOURNAL_COLUMNS = [
    "timestamp",
    "symbol",
    "strategies",
    "tier",
    "iv_rv_ratio",
    "ff_best",
    "put_skew",
    "event_premium_pct",
    "suggested_allocation_pct",
    "earnings_date",
    "days_to_earnings",
    "regime",
    "action_taken",
    "entry_price",
    "exit_price",
    "realized_pnl_pct",
    "exit_reason",
    "notes",
]


def log_signal(row: dict, regime: str = "UNKNOWN") -> None:
    """Append a scanner signal to the trade journal CSV."""
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = JOURNAL_PATH.exists()

    entry = {
        "timestamp": dt.datetime.now().isoformat(),
        "symbol": row.get("symbol", ""),
        "strategies": row.get("strategies", ""),
        "tier": row.get("tier_label", ""),
        "iv_rv_ratio": row.get("iv_rv_ratio", ""),
        "ff_best": row.get("ff_best", ""),
        "put_skew": row.get("put_skew", ""),
        "event_premium_pct": row.get("event_premium_pct", ""),
        "suggested_allocation_pct": row.get("suggested_allocation_pct", ""),
        "earnings_date": row.get("earnings_date", ""),
        "days_to_earnings": row.get("days_to_earnings", ""),
        "regime": regime,
        "action_taken": "",
        "entry_price": "",
        "exit_price": "",
        "realized_pnl_pct": "",
        "exit_reason": "",
        "notes": "",
    }

    with open(JOURNAL_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=JOURNAL_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)


def load_journal() -> list[dict]:
    """Load all journal entries."""
    if not JOURNAL_PATH.exists():
        return []
    with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_hit_rate(entries: list[dict]) -> dict:
    """Compute signal hit rate from journal entries that have outcomes."""
    completed = [e for e in entries if e.get("realized_pnl_pct")]
    if not completed:
        return {
            "total_signals": len(entries),
            "completed": 0,
            "hit_rate": 0.0,
            "avg_pnl_pct": 0.0,
            "win_count": 0,
            "loss_count": 0,
        }
    wins = [e for e in completed if float(e["realized_pnl_pct"]) > 0]
    pnls = [float(e["realized_pnl_pct"]) for e in completed]
    return {
        "total_signals": len(entries),
        "completed": len(completed),
        "hit_rate": len(wins) / len(completed),
        "avg_pnl_pct": sum(pnls) / len(pnls),
        "win_count": len(wins),
        "loss_count": len(completed) - len(wins),
    }
