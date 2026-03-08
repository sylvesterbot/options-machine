import unittest
import datetime as dt
import pandas as pd
from scanner.iron_fly import calculate_iron_fly


class TestIronFly(unittest.TestCase):
    def _make_chain(self, spot=100.0, exp_days=7):
        today = dt.date.today()
        exp = today + dt.timedelta(days=exp_days)
        strikes = list(range(80, 121, 5))
        rows = []
        for s in strikes:
            iv = 0.30 + 0.01 * abs(s - spot) / 5
            c_mid = max(0.1, spot - s + 5) if s < spot else max(0.1, 5 - (s - spot))
            p_mid = max(0.1, s - spot + 5) if s > spot else max(0.1, 5 - (spot - s))
            rows.append({"expiration": exp, "strike": s, "option_type": "call",
                         "implied_volatility": iv, "bid": c_mid * 0.95, "ask": c_mid * 1.05,
                         "delta": 0.5 if s == 100 else (0.7 if s < 100 else 0.3),
                         "volume": 100, "open_interest": 500})
            rows.append({"expiration": exp, "strike": s, "option_type": "put",
                         "implied_volatility": iv, "bid": p_mid * 0.95, "ask": p_mid * 1.05,
                         "delta": -0.5 if s == 100 else (-0.7 if s > 100 else -0.3),
                         "volume": 100, "open_interest": 500})
        return pd.DataFrame(rows)

    def test_basic_iron_fly(self):
        chain = self._make_chain()
        result = calculate_iron_fly(chain, spot=100.0)
        self.assertEqual(result["error"], "")
        self.assertGreater(result["net_credit"], 0)
        self.assertGreater(result["max_loss"], 0)
        self.assertLess(result["lower_breakeven"], 100)
        self.assertGreater(result["upper_breakeven"], 100)

    def test_empty_chain(self):
        result = calculate_iron_fly(pd.DataFrame(), spot=100.0)
        self.assertIn("Empty", result["error"])

    def test_wing_width_relationship(self):
        chain = self._make_chain()
        result = calculate_iron_fly(chain, spot=100.0, wing_multiplier=3.0)
        self.assertEqual(result["error"], "")
        self.assertGreater(result["long_call_strike"], result["short_call_strike"])
        self.assertLess(result["long_put_strike"], result["short_put_strike"])

    def test_risk_reward_positive(self):
        chain = self._make_chain()
        result = calculate_iron_fly(chain, spot=100.0)
        if not result["error"]:
            self.assertGreater(result["risk_reward_ratio"], 0)
