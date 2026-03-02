import datetime as dt
import unittest

import pandas as pd

from backtests.strategies import select_a1_contract


class A1SelectionTests(unittest.TestCase):
    def test_select_atm_expiry_between_21_45_dte(self):
        entry = dt.date(2026, 1, 10)
        options = pd.DataFrame([
            {"expiration": dt.date(2026, 1, 25), "strike": 95, "option_type": "call", "bid": 1, "ask": 1.2},
            {"expiration": dt.date(2026, 2, 5), "strike": 100, "option_type": "call", "bid": 2, "ask": 2.4},
            {"expiration": dt.date(2026, 2, 5), "strike": 100, "option_type": "put", "bid": 2.1, "ask": 2.5},
            {"expiration": dt.date(2026, 3, 15), "strike": 100, "option_type": "call", "bid": 3, "ask": 3.5},
        ])
        picked = select_a1_contract(options, spot=101, entry_date=entry, exit_date=dt.date(2026, 1, 30))
        self.assertEqual(picked['expiration'], dt.date(2026, 2, 5))
        self.assertEqual(picked['strike'], 100)


if __name__ == '__main__':
    unittest.main()
