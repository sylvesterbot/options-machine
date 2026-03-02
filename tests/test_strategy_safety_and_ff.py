import datetime as dt
import unittest

import numpy as np
import pandas as pd

from alerts import format_daily_alert
from openbb_earnings_iv_scanner import build_advice, to_markdown
from scanner.forward_factor import compute_forward_factor


class StrategySafetyAndFFTests(unittest.TestCase):
    def _chain(self) -> pd.DataFrame:
        today = dt.date.today()
        expiries = [today + dt.timedelta(days=30), today + dt.timedelta(days=60), today + dt.timedelta(days=90)]
        rows = []
        # make front IV rich vs later vols
        iv_map = {30: 0.55, 60: 0.38, 90: 0.32}
        for exp in expiries:
            dte = (exp - today).days
            for otype in ("call", "put"):
                rows.append(
                    {
                        "expiration": exp,
                        "strike": 100.0,
                        "option_type": otype,
                        "implied_volatility": iv_map[dte],
                    }
                )
        return pd.DataFrame(rows)

    def test_forward_factor_returns_multi_pair_keys(self) -> None:
        ff = compute_forward_factor(self._chain(), spot=100.0)
        self.assertIn("ff_30_60", ff)
        self.assertIn("ff_60_90", ff)
        self.assertIn("ff_30_90", ff)
        self.assertIn("ff_best", ff)
        self.assertIn("ff_best_pair", ff)
        self.assertIn("ff_signal", ff)
        self.assertTrue(ff["ff_best_pair"] in {"30-60", "60-90", "30-90", "NONE"})

    def test_build_advice_avoids_naked_straddle_language(self) -> None:
        advice = build_advice(strategies="A,B", ff_note="EARNINGS_IN_WINDOW")
        self.assertIn("defined-risk", advice)
        self.assertIn("Long calendar", advice)
        self.assertNotIn("Sell straddle", advice)

    def test_markdown_includes_ff_columns_and_safe_strategy_wording(self) -> None:
        df = pd.DataFrame([
            {
                "symbol": "AAPL",
                "earnings_date": "2026-03-20",
                "spot": 200.0,
                "iv30_proxy": 0.4,
                "rv30": 0.3,
                "iv_rv_ratio": 1.4,
                "expected_move_pct": 0.05,
                "option_volume": 1000,
                "open_interest": 2000,
                "avg_hist_move": 0.04,
                "max_hist_move": 0.06,
                "num_earnings": 5,
                "move_ratio": 1.25,
                "forward_factor": 0.2,
                "ff_best": 0.22,
                "ff_best_pair": "60-90",
                "ff_note": "EARNINGS_IN_WINDOW",
                "earnings_distortion_flag": True,
                "put_skew": 0.1,
                "call_skew": 0.0,
                "momentum_dir": "BULLISH",
                "strategies": "A,B",
                "advice": "Long calendar spread for hold-through-earnings.",
            }
        ])
        class Args:
            window_days = 14
            min_oi = 0
            min_vol = 0
        md = to_markdown(df, Args())
        self.assertIn("FFbest", md)
        self.assertIn("FFpair", md)
        self.assertIn("FFnote", md)
        self.assertIn("Distorted?", md)
        self.assertIn("defined-risk only", md)

    def test_alert_mentions_defined_risk_for_strategy_a(self) -> None:
        df = pd.DataFrame([
            {
                "symbol": "AAPL",
                "strategies": "A",
                "iv_rv_ratio": 1.33,
                "forward_factor": np.nan,
                "earnings_date": "2026-03-20",
                "advice": "Use defined-risk only.",
            }
        ])
        alert = format_daily_alert(df)
        self.assertIn("defined-risk", alert)


if __name__ == "__main__":
    unittest.main()
