import unittest

from alerts import format_daily_alert, format_trade_alert
from scanner.event_vol import decompose_event_vol
from scanner.regime import classify_regime


class TestPhase6Integration(unittest.TestCase):
    def test_full_alert_pipeline(self):
        row = {
            "symbol": "NVDA",
            "earnings_date": "2026-03-12",
            "days_to_earnings": 2,
            "strategies": "A,B",
            "tier": 1,
            "tier_label": "TIER_1",
            "iv_rv_ratio": 1.87,
            "iv_percentile_52w": 0.92,
            "expected_move_pct": 0.052,
            "avg_hist_move": 0.031,
            "ff_best": 0.34,
            "ff_best_pair": "60-90",
            "ff_signal": "STRONG",
            "ff_zscore": 1.8,
            "front_iv": 0.321,
            "back_iv": 0.240,
            "earnings_distortion_flag": False,
            "suggested_allocation_pct": 0.04,
            "event_vol": 0.55,
            "event_premium_pct": 1.2,
            "put_skew": float("nan"),
            "rv_edge_put": float("nan"),
            "momentum_dir": "NEUTRAL",
            "momentum_pct": 0.01,
            "otm_put_strike": float("nan"),
            "otm_put_delta": float("nan"),
            "filter_failures": "",
        }
        alert = format_trade_alert(row, capital=100000)
        self.assertIn("NVDA", alert)
        self.assertIn("IV CRUSH", alert)
        self.assertIn("FORWARD FACTOR", alert)
        self.assertIn("WHY", alert)
        self.assertIn("ACTION", alert)
        self.assertIn("SIZING", alert)
        self.assertIn("IRON", alert)
        self.assertIn("CALENDAR", alert)

    def test_regime_classification_complete(self):
        for vix in [10, 15, 20, 25, 30, 35, 40, 50, 80]:
            r = classify_regime(float(vix))
            self.assertIn(r["regime"], ["CALM", "NORMAL", "ELEVATED", "CRISIS"])
            self.assertIn("allocation_multiplier", r)

    def test_event_vol_in_alert(self):
        ev = decompose_event_vol(iv30=0.45, rv30=0.20, dte=3)
        row = {
            "symbol": "TEST",
            "earnings_date": "2026-04-01",
            "days_to_earnings": 5,
            "strategies": "A",
            "tier": 1,
            "tier_label": "TIER_1",
            "iv_rv_ratio": 1.50,
            "iv_percentile_52w": 0.80,
            "expected_move_pct": 0.04,
            "avg_hist_move": 0.025,
            "event_vol": ev["event_vol"],
            "event_premium_pct": ev["event_premium_pct"],
            "suggested_allocation_pct": 0.04,
            "ff_best": float("nan"),
            "ff_best_pair": "NONE",
            "put_skew": float("nan"),
            "rv_edge_put": float("nan"),
            "momentum_dir": "NEUTRAL",
            "momentum_pct": 0.0,
            "otm_put_strike": float("nan"),
            "otm_put_delta": float("nan"),
            "filter_failures": "",
            "front_iv": float("nan"),
            "back_iv": float("nan"),
            "ff_signal": "NONE",
            "ff_zscore": float("nan"),
            "earnings_distortion_flag": False,
        }
        alert = format_trade_alert(row)
        self.assertIn("Event Premium", alert)


if __name__ == "__main__":
    unittest.main()
