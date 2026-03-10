import unittest
import pandas as pd
from alerts import format_trade_alert, format_daily_alert


class TestConciseAlerts(unittest.TestCase):
    def _make_row(self, **overrides):
        base = {
            "symbol": "NVDA", "earnings_date": "2026-03-12", "days_to_earnings": 2,
            "strategies": "A,B", "tier": 1, "tier_label": "TIER_1",
            "iv_rv_ratio": 1.87, "iv_percentile_52w": 0.92,
            "expected_move_pct": 0.052, "avg_hist_move": 0.031,
            "ff_best": 0.34, "ff_best_pair": "60-90", "ff_signal": "STRONG",
            "ff_zscore": 1.8, "front_iv": 0.321, "back_iv": 0.240,
            "earnings_distortion_flag": False,
            "put_skew": 1.1, "rv_edge_put": 0.05,
            "momentum_dir": "BULLISH", "momentum_pct": 0.042,
            "suggested_allocation_pct": 0.04, "filter_failures": "",
            "otm_put_strike": 340.0, "otm_put_delta": -0.25,
        }
        base.update(overrides)
        return base

    def test_trade_alert_contains_why_action_sizing(self):
        alert = format_trade_alert(self._make_row())
        self.assertIn("WHY", alert)
        self.assertIn("ACTION", alert)
        self.assertIn("SIZING", alert)

    def test_trade_alert_strategy_a_mentions_iron(self):
        alert = format_trade_alert(self._make_row(strategies="A", iv_rv_ratio=1.87))
        self.assertIn("IRON", alert.upper())

    def test_trade_alert_strategy_b_mentions_calendar(self):
        alert = format_trade_alert(self._make_row(strategies="B"))
        self.assertIn("CALENDAR", alert.upper())

    def test_trade_alert_strategy_c_mentions_put_credit(self):
        alert = format_trade_alert(self._make_row(strategies="C", put_skew=1.38, rv_edge_put=0.12, momentum_dir="BULLISH"))
        self.assertIn("PUT CREDIT", alert.upper())

    def test_daily_alert_has_tier_sections(self):
        df = pd.DataFrame([
            self._make_row(symbol="NVDA", tier=1, tier_label="TIER_1"),
            self._make_row(symbol="AMD", tier=2, tier_label="TIER_2"),
        ])
        alert = format_daily_alert(df)
        self.assertIn("TIER 1", alert)
        self.assertIn("TIER 2", alert)
        self.assertIn("NVDA", alert)
        self.assertIn("AMD", alert)

    def test_daily_alert_empty(self):
        alert = format_daily_alert(pd.DataFrame())
        self.assertIn("No candidates", alert)

    def test_sizing_shows_dollar_amount(self):
        alert = format_trade_alert(self._make_row(), capital=100000)
        self.assertIn("$", alert)

    def test_strategy_a_high_iv_recommends_iron_fly(self):
        alert = format_trade_alert(self._make_row(strategies="A", iv_rv_ratio=1.87))
        self.assertIn("IRON FLY", alert)

    def test_strategy_a_moderate_iv_recommends_iron_condor(self):
        alert = format_trade_alert(self._make_row(strategies="A", iv_rv_ratio=1.30))
        self.assertIn("IRON CONDOR", alert)


if __name__ == "__main__":
    unittest.main()
