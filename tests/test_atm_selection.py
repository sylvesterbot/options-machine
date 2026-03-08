import datetime as dt
import unittest

import pandas as pd

from openbb_earnings_iv_scanner import select_30d_atm


class ATMSelectionTests(unittest.TestCase):
    def test_prefers_delta_based_atm_when_available(self):
        today = dt.date.today()
        exp = today + dt.timedelta(days=30)
        chain = pd.DataFrame([
            {"expiration": exp, "strike": 95, "delta": -0.30},
            {"expiration": exp, "strike": 100, "delta": -0.50},
            {"expiration": exp, "strike": 105, "delta": -0.70},
        ])
        atm, _ = select_30d_atm(chain, spot=102)
        self.assertTrue((atm["strike"] == 100).any())

    def test_falls_back_to_strike_distance_without_delta(self):
        today = dt.date.today()
        exp = today + dt.timedelta(days=30)
        chain = pd.DataFrame([
            {"expiration": exp, "strike": 95},
            {"expiration": exp, "strike": 100},
            {"expiration": exp, "strike": 105},
        ])
        atm, _ = select_30d_atm(chain, spot=103)
        self.assertTrue((atm["strike"] == 105).any())


if __name__ == "__main__":
    unittest.main()
