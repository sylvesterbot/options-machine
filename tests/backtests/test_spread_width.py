import datetime as dt
import inspect
import unittest

import pandas as pd

from backtests.strategy_b import _select_legs
from backtests.strategy_c import simulate_strategy_c


class TestSpreadWidth(unittest.TestCase):
    def test_spread_width_parameter_accepted(self):
        sig = inspect.signature(simulate_strategy_c)
        self.assertIn("spread_width", sig.parameters)

    def test_select_legs_prefers_delta_based_atm(self):
        d = dt.date(2026, 1, 2)
        f = d + dt.timedelta(days=30)
        b = d + dt.timedelta(days=60)
        chain = pd.DataFrame(
            {
                "expiration": [f, f, f, b, b, b],
                "strike": [95, 100, 105, 95, 100, 105],
                "option_type": ["call"] * 6,
                "delta": [0.20, 0.48, 0.65, 0.20, 0.48, 0.65],
                "bid": [1, 2, 3, 2, 3, 4],
                "ask": [1.2, 2.2, 3.2, 2.2, 3.2, 4.2],
            }
        )
        front, back = _select_legs(chain, entry_spot=102, ff_pair="30-60", pair_expiries={"30-60": (f, b)})
        self.assertEqual(front.strike, 100.0)
        self.assertEqual(back.strike, 100.0)


if __name__ == "__main__":
    unittest.main()
