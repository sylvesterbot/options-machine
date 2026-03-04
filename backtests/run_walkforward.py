from __future__ import annotations

import argparse
import sys
import datetime as dt
from pathlib import Path
import pandas as pd

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from backtests.providers.registry import resolve_provider
from backtests.strategy_b import simulate_strategy_b, summarize_trade_log
from backtests.strategy_c import simulate_strategy_c


def _add_years(d: dt.date, years: int) -> dt.date:
    return dt.date(d.year + years, d.month, d.day)


def build_walkforward_windows(start: dt.date, end: dt.date, train_years: int = 2, test_years: int = 2, step_years: int = 1) -> list[dict]:
    if train_years <= 0:
        return [{"train_start": start, "train_end": start - dt.timedelta(days=1), "test_start": start, "test_end": end}]
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
    strategy: str = "B",
    symbols: list[str] | None = None,
    ff_threshold: float = 0.2,
    holding_days: int = 10,
    exit_mode: str = "fixed",
    train_years: int = 2,
    test_years: int = 2,
    step_years: int = 1,
    iv_rv_max: float = 2.0,
    use_kelly: bool = False,
    stop_loss: float = -0.20,
    slippage: float = 0.0,
    kelly_min_trades: int = 50,
) -> pd.DataFrame:
    provider = resolve_provider(provider_name, root_dir=provider_root)
    windows = build_walkforward_windows(start, end, train_years=train_years, test_years=test_years, step_years=step_years)
    all_trades = []
    symbols = symbols or ["SPY"]

    for i, w in enumerate(windows, start=1):
        for sym in symbols:
            if strategy == "B":
                tdf = simulate_strategy_b(
                    provider=provider,
                    symbol=sym,
                    start=w["test_start"],
                    end=w["test_end"],
                    ff_threshold=ff_threshold,
                    holding_days=holding_days,
                    exit_mode=exit_mode,
                    iv_rv_max=iv_rv_max,
                    use_kelly=use_kelly,
                    stop_loss_pct=stop_loss,
                    slippage_pct=slippage,
                    kelly_min_trades=kelly_min_trades,
                )
                if not tdf.empty:
                    tdf = tdf.copy()
                    tdf["window_id"] = i
                    tdf["strategy"] = "B"
                    tdf["provider"] = provider_name
                    all_trades.append(tdf)
            elif strategy == "C":
                tdf = simulate_strategy_c(
                    provider=provider,
                    symbol=sym,
                    start=w["test_start"],
                    end=w["test_end"],
                    holding_days=holding_days,
                    use_kelly=use_kelly,
                    stop_loss_pct=stop_loss,
                    slippage_pct=slippage,
                    kelly_min_trades=kelly_min_trades,
                )
                if not tdf.empty:
                    tdf = tdf.copy()
                    tdf["window_id"] = i
                    tdf["strategy"] = "C"
                    tdf["provider"] = provider_name
                    all_trades.append(tdf)

    out_df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame(
        columns=["symbol", "entry_date", "exit_date", "entry_price", "exit_price", "return_pct", "ff_entry", "ff_exit", "ff_pair", "window_id", "strategy", "provider"]
    )
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    return out_df


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--out", default="outputs/walkforward_trades.csv")
    parser.add_argument("--provider", default="mock", choices=["mock", "lambdaclass", "polygon", "thetadata", "eodhd"])
    parser.add_argument("--provider-root", default="data/lambdaclass-data-v1")
    parser.add_argument("--strategy", default="B", choices=["B", "C"])
    parser.add_argument("--symbols", default="SPY", help="Comma-separated symbols. VID-4 strategy designed for SPY. IWM/QQQ are out-of-sample.")
    parser.add_argument("--ff-threshold", type=float, default=0.2)
    parser.add_argument("--holding-days", type=int, default=10)
    parser.add_argument("--exit-mode", default="fixed", choices=["fixed", "mean_revert"])
    parser.add_argument("--train-years", type=int, default=2)
    parser.add_argument("--test-years", type=int, default=2)
    parser.add_argument("--step-years", type=int, default=1)
    parser.add_argument("--iv-rv-max", type=float, default=2.0, help="Skip trades when IV/RV exceeds this (regime filter)")
    parser.add_argument("--use-kelly", action="store_true", help="Enable Kelly position sizing")
    parser.add_argument("--stop-loss", type=float, default=-0.20, help="Intra-trade stop loss threshold (return), e.g. -0.20")
    parser.add_argument("--slippage", type=float, default=0.0, help="Slippage applied at entry/exit pricing")
    parser.add_argument("--kelly-min-trades", type=int, default=50, help="Minimum trade history before empirical Kelly sizing")
    args = parser.parse_args()

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    for sym in symbols:
        if sym != "SPY":
            print(f"WARNING: {sym} is out-of-sample for VID-4 strategy — results may not match SPY performance characteristics")
    df = run_walkforward(
        start,
        end,
        args.out,
        provider_name=args.provider,
        provider_root=args.provider_root,
        strategy=args.strategy,
        symbols=symbols,
        ff_threshold=args.ff_threshold,
        holding_days=args.holding_days,
        exit_mode=args.exit_mode,
        train_years=args.train_years,
        test_years=args.test_years,
        step_years=args.step_years,
        iv_rv_max=args.iv_rv_max,
        use_kelly=args.use_kelly,
        stop_loss=args.stop_loss,
        slippage=args.slippage,
        kelly_min_trades=args.kelly_min_trades,
    )
    summary = summarize_trade_log(df)
    print(f"walkforward done. provider={args.provider} strategy={args.strategy} trades={len(df)} out={args.out}")
    print(f"summary: total_return={summary['total_return']:.4f} avg_return={summary['avg_return']:.4f} vol={summary['volatility']:.4f} max_dd={summary['max_drawdown']:.4f} sharpe={summary['sharpe']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
