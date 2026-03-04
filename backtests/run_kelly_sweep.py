from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import sys

import pandas as pd

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from backtests.run_walkforward import run_walkforward
from backtests.strategy_b import summarize_trade_log


def main() -> int:
    p = argparse.ArgumentParser(description="Kelly min-trades sweep for Strategy B")
    p.add_argument("--provider", default="lambdaclass")
    p.add_argument("--provider-root", default="data/lambdaclass_data_v1/extracted_spy_2020_2024")
    p.add_argument("--start", default="2020-01-01")
    p.add_argument("--end", default="2024-12-31")
    p.add_argument("--symbols", default="SPY")
    p.add_argument("--out", default="outputs/kelly_sweep.csv")
    p.add_argument("--grid", default="10,20,30,50,80")
    args = p.parse_args()

    root = Path(args.provider_root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not root.exists():
        df = pd.DataFrame([
            {
                "status": "blocked",
                "reason": f"dataset missing: {root}",
            }
        ])
        df.to_csv(out, index=False)
        print(f"blocked: dataset missing at {root}")
        print(f"wrote blocker artifact: {out}")
        return 0

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    rows: list[dict] = []
    for mt in [int(x) for x in args.grid.split(",") if x.strip()]:
        tmp_out = out.parent / f"kelly_sweep_mt{mt}.csv"
        trades = run_walkforward(
            start=start,
            end=end,
            out_path=str(tmp_out),
            provider_name=args.provider,
            provider_root=args.provider_root,
            strategy="B",
            symbols=symbols,
            holding_days=10,
            train_years=0,
            use_kelly=True,
            kelly_min_trades=mt,
        )
        s = summarize_trade_log(trades)
        rows.append(
            {
                "kelly_min_trades": mt,
                "trades": s["trades"],
                "total_return": s["total_return"],
                "avg_return": s["avg_return"],
                "max_drawdown": s["max_drawdown"],
                "sharpe": s["sharpe"],
                "artifact": str(tmp_out),
            }
        )

    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"kelly sweep done: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
