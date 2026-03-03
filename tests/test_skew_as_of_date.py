import datetime as dt
import unittest

import pandas as pd

from scanner.skew_score import compute_skew_score


class SkewAsOfDateTests(unittest.TestCase):
    def test_as_of_date_controls_target_expiry(self):
        as_of = dt.date(2020, 1, 1)
        exp_30 = as_of + dt.timedelta(days=30)
        exp_120 = as_of + dt.timedelta(days=120)

        chain = pd.DataFrame(
            [
                {"expiration": exp_30, "strike": 100, "option_type": "call", "implied_volatility": 0.30},
                {"expiration": exp_30, "strike": 100, "option_type": "put", "implied_volatility": 0.30},
                {"expiration": exp_30, "strike": 90, "option_type": "put", "implied_volatility": 0.45},
                {"expiration": exp_30, "strike": 110, "option_type": "call", "implied_volatility": 0.40},
                {"expiration": exp_120, "strike": 100, "option_type": "call", "implied_volatility": 0.10},
                {"expiration": exp_120, "strike": 100, "option_type": "put", "implied_volatility": 0.10},
                {"expiration": exp_120, "strike": 90, "option_type": "put", "implied_volatility": 0.12},
                {"expiration": exp_120, "strike": 110, "option_type": "call", "implied_volatility": 0.12},
            ]
        )

        out = compute_skew_score(chain, spot=100, rv30=0.25, as_of_date=as_of)
        # should use near-30D expiry rather than near today's date
        self.assertGreater(float(out["atm_iv"]), 0.2)


if __name__ == "__main__":
    unittest.main()
