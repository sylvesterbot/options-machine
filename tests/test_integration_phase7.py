import unittest

from alerts import format_trade_alert
from scanner.regime import classify_regime
from scanner.trade_journal import compute_hit_rate


class TestPhase7Integration(unittest.TestCase):
    def test_regime_has_stop_loss_multiplier(self):
        for vix in [10, 20, 30, 40]:
            r = classify_regime(float(vix))
            self.assertIn("stop_loss_multiplier", r)
            self.assertIsInstance(r["stop_loss_multiplier"], float)

    def test_alert_shows_adjusted_stop(self):
        row = {
            "symbol": "SPY",
            "strategies": "C",
            "earnings_date": "2026-05-01",
            "days_to_earnings": 10,
            "tier_label": "TIER_1",
            "put_skew": 1.45,
            "rv_edge_put": 0.08,
            "momentum_dir": "BULLISH",
            "momentum_pct": 0.03,
            "suggested_allocation_pct": 0.04,
            "otm_put_strike": 520.0,
            "stop_loss_multiplier": 1.3,
            "iv_rv_ratio": float("nan"),
            "iv_percentile_52w": float("nan"),
            "expected_move_pct": float("nan"),
            "avg_hist_move": float("nan"),
            "event_premium_pct": float("nan"),
            "ff_best": float("nan"),
            "ff_best_pair": "",
            "ff_signal": "",
            "ff_zscore": float("nan"),
            "front_iv": float("nan"),
            "back_iv": float("nan"),
            "earnings_distortion_flag": False,
            "filter_failures": "",
        }
        alert = format_trade_alert(row)
        self.assertIn("PUT CREDIT", alert)
        self.assertIn("SELL", alert)

    def test_journal_hitrate_math(self):
        entries = [
            {"realized_pnl_pct": "10.0"},
            {"realized_pnl_pct": "-5.0"},
            {"realized_pnl_pct": "3.0"},
            {"realized_pnl_pct": "-1.0"},
            {"symbol": "X"},
        ]
        result = compute_hit_rate(entries)
        self.assertEqual(result["total_signals"], 5)
        self.assertEqual(result["completed"], 4)
        self.assertAlmostEqual(result["hit_rate"], 0.50)

    def test_full_pipeline_no_crash(self):
        for strat in ["A", "B", "C", "A,B", "A,C", "B,C", "A,B,C"]:
            row = {
                "symbol": "TEST",
                "strategies": strat,
                "earnings_date": "2026-06-01",
                "days_to_earnings": 5,
                "tier_label": "TIER_1",
                "iv_rv_ratio": 1.5,
                "iv_percentile_52w": 0.75,
                "expected_move_pct": 0.04,
                "avg_hist_move": 0.03,
                "suggested_allocation_pct": 0.04,
                "event_premium_pct": 0.6,
                "ff_best": 0.25,
                "ff_best_pair": "30-60",
                "ff_signal": "STRONG",
                "ff_zscore": 1.5,
                "front_iv": 0.30,
                "back_iv": 0.22,
                "earnings_distortion_flag": False,
                "put_skew": 1.35,
                "rv_edge_put": 0.05,
                "momentum_dir": "BULLISH",
                "momentum_pct": 0.03,
                "otm_put_strike": 95.0,
                "filter_failures": "",
                "stop_loss_multiplier": 1.0,
            }
            alert = format_trade_alert(row)
            self.assertIn("WHY", alert)
            self.assertIn("ACTION", alert)
            self.assertIn("SIZING", alert)


if __name__ == "__main__":
    unittest.main()
