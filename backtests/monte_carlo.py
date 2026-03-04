from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def monte_carlo_equity(
    trade_returns,
    n_simulations: int = 10000,
    n_trades_forward: int = 100,
    initial_capital: float = 100000.0,
    kelly_fraction: float = 0.04,
    seed: int = 42,
):
    r = np.array(list(trade_returns), dtype=float)
    if r.size == 0:
        terminal = np.full(n_simulations, float(initial_capital), dtype=float)
        fan = {k: [float(initial_capital)] * (n_trades_forward + 1) for k in ["5", "25", "50", "75", "95"]}
        return {
            "terminal_wealth": terminal.tolist(),
            "median_return": 0.0,
            "p5_return": 0.0,
            "p95_return": 0.0,
            "prob_ruin": 0.0,
            "prob_double": 0.0,
            "median_max_dd": 0.0,
            "p5_max_dd": 0.0,
            "fan_chart": fan,
        }

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(r), size=(n_simulations, n_trades_forward))
    sampled = r[idx]
    scaled = kelly_fraction * sampled

    growth = np.cumprod(1.0 + scaled, axis=1)
    equity = initial_capital * growth
    equity = np.concatenate([np.full((n_simulations, 1), initial_capital), equity], axis=1)

    terminal = equity[:, -1]
    ret = terminal / initial_capital - 1.0

    peaks = np.maximum.accumulate(equity, axis=1)
    drawdowns = equity / peaks - 1.0
    max_dd = drawdowns.min(axis=1)

    fan = {
        "5": np.percentile(equity, 5, axis=0).tolist(),
        "25": np.percentile(equity, 25, axis=0).tolist(),
        "50": np.percentile(equity, 50, axis=0).tolist(),
        "75": np.percentile(equity, 75, axis=0).tolist(),
        "95": np.percentile(equity, 95, axis=0).tolist(),
    }

    return {
        "terminal_wealth": terminal.tolist(),
        "median_return": float(np.median(ret)),
        "p5_return": float(np.percentile(ret, 5)),
        "p95_return": float(np.percentile(ret, 95)),
        "prob_ruin": float(np.mean(terminal <= 0.5 * initial_capital)),
        "prob_double": float(np.mean(terminal >= 2.0 * initial_capital)),
        "median_max_dd": float(np.median(max_dd)),
        "p5_max_dd": float(np.percentile(max_dd, 5)),
        "fan_chart": fan,
    }


def _load_returns(trades_csv: str) -> list[float]:
    df = pd.read_csv(trades_csv)
    if "portfolio_return" in df.columns:
        col = "portfolio_return"
    elif "return_pct" in df.columns:
        col = "return_pct"
    else:
        return []
    return pd.to_numeric(df[col], errors="coerce").dropna().tolist()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Monte Carlo equity simulation for options-machine")
    parser.add_argument("--trades-csv", required=True)
    parser.add_argument("--n-simulations", type=int, default=10000)
    parser.add_argument("--n-trades-forward", type=int, default=100)
    parser.add_argument("--initial-capital", type=float, default=100000.0)
    parser.add_argument("--kelly-fraction", type=float, default=0.04)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="outputs/monte_carlo.json")
    args = parser.parse_args(argv)

    returns = _load_returns(args.trades_csv)
    res = monte_carlo_equity(
        trade_returns=returns,
        n_simulations=args.n_simulations,
        n_trades_forward=args.n_trades_forward,
        initial_capital=args.initial_capital,
        kelly_fraction=args.kelly_fraction,
        seed=args.seed,
    )

    payload = {k: v for k, v in res.items() if k != "terminal_wealth"}
    payload["n_returns_input"] = len(returns)
    payload["n_simulations"] = int(args.n_simulations)
    payload["n_trades_forward"] = int(args.n_trades_forward)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
