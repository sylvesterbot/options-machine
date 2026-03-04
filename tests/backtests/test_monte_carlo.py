import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from backtests.monte_carlo import monte_carlo_equity, main


class MonteCarloTests(unittest.TestCase):
    def test_basic_positive_returns(self):
        out = monte_carlo_equity(
            trade_returns=[0.01, 0.02, 0.015],
            n_simulations=500,
            n_trades_forward=50,
            initial_capital=100000.0,
            kelly_fraction=0.04,
            seed=7,
        )
        self.assertGreater(out["median_return"], 0)
        self.assertGreaterEqual(out["p95_return"], out["p5_return"])
        self.assertIn("fan_chart", out)

    def test_mixed_returns(self):
        out = monte_carlo_equity(
            trade_returns=[-0.03, 0.01, -0.01, 0.02],
            n_simulations=500,
            n_trades_forward=60,
            initial_capital=100000.0,
            kelly_fraction=0.05,
            seed=11,
        )
        self.assertGreaterEqual(out["prob_ruin"], 0.0)
        self.assertLessEqual(out["prob_ruin"], 1.0)
        self.assertGreaterEqual(out["prob_double"], 0.0)
        self.assertLessEqual(out["prob_double"], 1.0)

    def test_empty_returns(self):
        out = monte_carlo_equity(
            trade_returns=[],
            n_simulations=100,
            n_trades_forward=20,
            initial_capital=100000.0,
            kelly_fraction=0.04,
            seed=42,
        )
        self.assertEqual(len(out["terminal_wealth"]), 100)
        self.assertEqual(out["median_return"], 0.0)
        self.assertEqual(out["prob_ruin"], 0.0)
        self.assertEqual(len(out["fan_chart"]["50"]), 21)

    def test_fan_chart_monotonic_percentiles(self):
        out = monte_carlo_equity(
            trade_returns=[-0.02, 0.01, 0.03, -0.01],
            n_simulations=300,
            n_trades_forward=40,
            initial_capital=100000.0,
            kelly_fraction=0.03,
            seed=19,
        )
        fan = out["fan_chart"]
        for i in range(len(fan["50"])):
            self.assertLessEqual(fan["5"][i], fan["25"][i])
            self.assertLessEqual(fan["25"][i], fan["50"][i])
            self.assertLessEqual(fan["50"][i], fan["75"][i])
            self.assertLessEqual(fan["75"][i], fan["95"][i])

    def test_cli_writes_json(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            trades_csv = tdp / "trades.csv"
            out_json = tdp / "mc.json"
            pd.DataFrame({"return_pct": [0.01, -0.01, 0.02]}).to_csv(trades_csv, index=False)

            rc = main([
                "--trades-csv", str(trades_csv),
                "--n-simulations", "200",
                "--n-trades-forward", "30",
                "--initial-capital", "100000",
                "--kelly-fraction", "0.04",
                "--seed", "5",
                "--out", str(out_json),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(out_json.exists())
            data = json.loads(out_json.read_text())
            self.assertNotIn("terminal_wealth", data)
            self.assertEqual(data["n_returns_input"], 3)
            self.assertEqual(data["n_simulations"], 200)
            self.assertEqual(data["n_trades_forward"], 30)


if __name__ == "__main__":
    unittest.main()
