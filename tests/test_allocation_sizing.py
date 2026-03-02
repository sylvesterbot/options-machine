import unittest
from argparse import Namespace

import pandas as pd

import run_scan
from alerts import format_daily_alert
from openbb_earnings_iv_scanner import compute_suggested_allocation, to_markdown


class AllocationSizingTests(unittest.TestCase):
    def test_compute_suggested_allocation_rules_and_clamp(self) -> None:
        pct, usd = compute_suggested_allocation(
            strategies="A,B,C",
            ff_signal="STRONG",
            earnings_distortion_flag=False,
            momentum_dir="BULLISH",
            skew_signal="RICH_PUT_SKEW",
            capital=100000,
            default_alloc=0.04,
        )
        # 0.04 +0.01 -0.01 +0.005 = 0.045
        self.assertAlmostEqual(pct, 0.045, places=6)
        self.assertAlmostEqual(usd, 4500.0, places=4)

        pct2, _ = compute_suggested_allocation(
            strategies="A",
            ff_signal="NONE",
            earnings_distortion_flag=False,
            momentum_dir="NEUTRAL",
            skew_signal="NONE",
            capital=None,
            default_alloc=0.01,
        )
        self.assertEqual(pct2, 0.02)

    def test_markdown_has_alloc_columns(self) -> None:
        args = Namespace(window_days=14, min_oi=0, min_vol=0, capital=100000)
        df = pd.DataFrame([
            {
                "symbol": "AAPL",
                "earnings_date": "2026-03-20",
                "spot": 200.0,
                "iv30_proxy": 0.4,
                "rv30": 0.3,
                "iv_rv_ratio": 1.33,
                "expected_move_pct": 0.05,
                "option_volume": 1000,
                "open_interest": 2000,
                "avg_hist_move": 0.04,
                "max_hist_move": 0.06,
                "move_ratio": 1.25,
                "ff_best": 0.22,
                "ff_best_pair": "60-90",
                "ff_note": "X_EARN",
                "earnings_distortion_flag": False,
                "put_skew": 0.1,
                "momentum_dir": "BULLISH",
                "strategies": "B",
                "suggested_allocation_pct": 0.05,
                "suggested_allocation_usd": 5000.0,
            }
        ])
        md = to_markdown(df, args)
        self.assertIn("Alloc%", md)
        self.assertIn("Alloc$", md)
        self.assertIn("5.0%", md)

    def test_alert_includes_alloc(self) -> None:
        df = pd.DataFrame([
            {
                "symbol": "AAPL",
                "strategies": "B",
                "iv_rv_ratio": 1.2,
                "ff_best": 0.22,
                "earnings_date": "2026-03-20",
                "advice": "test",
                "suggested_allocation_pct": 0.05,
            }
        ])
        alert = format_daily_alert(df)
        self.assertIn("Alloc: 5.0%", alert)


if __name__ == "__main__":
    unittest.main()
