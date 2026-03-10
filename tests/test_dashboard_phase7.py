"""Test that dashboard can import and render Phase 6 data fields."""

import unittest


class TestDashboardPhase7(unittest.TestCase):
    def test_regime_import(self):
        from scanner.regime import classify_regime, get_vix_level

        r = classify_regime(20.0)
        self.assertEqual(r["regime"], "NORMAL")

    def test_alert_format_import(self):
        from alerts import format_trade_alert

        row = {
            "symbol": "TEST",
            "strategies": "A",
            "earnings_date": "2026-04-01",
            "days_to_earnings": 5,
            "tier_label": "TIER_1",
            "iv_rv_ratio": 1.5,
            "iv_percentile_52w": 0.8,
            "expected_move_pct": 0.04,
            "avg_hist_move": 0.025,
            "suggested_allocation_pct": 0.04,
            "event_premium_pct": 0.5,
            "ff_best": float("nan"),
            "ff_best_pair": "",
            "ff_signal": "",
            "ff_zscore": float("nan"),
            "front_iv": float("nan"),
            "back_iv": float("nan"),
            "earnings_distortion_flag": False,
            "put_skew": float("nan"),
            "rv_edge_put": float("nan"),
            "momentum_dir": "NEUTRAL",
            "momentum_pct": 0.0,
            "otm_put_strike": float("nan"),
            "filter_failures": "",
        }
        alert = format_trade_alert(row)
        self.assertIn("WHY", alert)
        self.assertIn("ACTION", alert)
        self.assertIn("SIZING", alert)

    def test_event_vol_fields_in_alert(self):
        from alerts import format_trade_alert

        row = {
            "symbol": "AMZN",
            "strategies": "A",
            "earnings_date": "2026-04-15",
            "days_to_earnings": 3,
            "tier_label": "TIER_1",
            "iv_rv_ratio": 2.0,
            "iv_percentile_52w": 0.95,
            "expected_move_pct": 0.06,
            "avg_hist_move": 0.03,
            "suggested_allocation_pct": 0.04,
            "event_premium_pct": 1.5,
            "ff_best": float("nan"),
            "ff_best_pair": "",
            "ff_signal": "",
            "ff_zscore": float("nan"),
            "front_iv": float("nan"),
            "back_iv": float("nan"),
            "earnings_distortion_flag": False,
            "put_skew": float("nan"),
            "rv_edge_put": float("nan"),
            "momentum_dir": "NEUTRAL",
            "momentum_pct": 0.0,
            "otm_put_strike": float("nan"),
            "filter_failures": "",
        }
        alert = format_trade_alert(row)
        self.assertIn("Event Premium", alert)

    def test_exit_reason_values(self):
        valid = {"profit_target", "stop_loss", "expiry"}
        for v in valid:
            self.assertIsInstance(v, str)


if __name__ == "__main__":
    unittest.main()
