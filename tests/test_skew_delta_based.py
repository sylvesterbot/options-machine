import datetime as dt
import unittest

import pandas as pd

from scanner.skew_score import compute_skew_score


class SkewDeltaBasedTests(unittest.TestCase):
    def test_returns_delta_and_strike_fields(self):
        exp = dt.date.today() + dt.timedelta(days=30)
        chain = pd.DataFrame([
            {"expiration": exp, "strike": 90, "option_type": "put", "implied_volatility": 0.45},
            {"expiration": exp, "strike": 95, "option_type": "put", "implied_volatility": 0.40},
            {"expiration": exp, "strike": 100, "option_type": "put", "implied_volatility": 0.30},
            {"expiration": exp, "strike": 100, "option_type": "call", "implied_volatility": 0.30},
            {"expiration": exp, "strike": 105, "option_type": "call", "implied_volatility": 0.42},
            {"expiration": exp, "strike": 110, "option_type": "call", "implied_volatility": 0.50},
        ])
        out = compute_skew_score(chain, spot=100, rv30=0.25)
        self.assertIn("otm_put_strike", out)
        self.assertIn("otm_call_strike", out)
        self.assertIn("otm_put_delta", out)
        self.assertIn("otm_call_delta", out)
        self.assertIn("rv_edge_put", out)
        self.assertIn("rv_edge_call", out)


if __name__ == "__main__":
    unittest.main()
