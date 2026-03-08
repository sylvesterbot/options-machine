import datetime as dt
import unittest

import pandas as pd

from scanner.forward_factor import compute_forward_factor


class ForwardIVTests(unittest.TestCase):
    def test_forward_iv_not_nan_with_valid_chain(self):
        today = dt.date(2024, 1, 2)
        expiries = [today + dt.timedelta(days=30), today + dt.timedelta(days=60), today + dt.timedelta(days=90)]
        rows = []
        for exp, iv in zip(expiries, [0.30, 0.28, 0.27]):
            for strike in [95, 100, 105]:
                rows.append({
                    "expiration": exp,
                    "strike": strike,
                    "option_type": "call",
                    "implied_volatility": iv,
                })
        chain = pd.DataFrame(rows)
        out = compute_forward_factor(chain, spot=100, as_of_date=today)
        self.assertIn("forward_iv", out)
        self.assertFalse(pd.isna(out["forward_iv"]))


if __name__ == "__main__":
    unittest.main()
