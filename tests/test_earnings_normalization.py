import datetime as dt
import unittest

import pandas as pd

from openbb_earnings_iv_scanner import normalize_earnings_calendar_df


class EarningsNormalizationTests(unittest.TestCase):
    def test_handles_earnings_date_column_with_space_and_header_row_noise(self):
        df = pd.DataFrame(
            {
                "Symbol": ["Earnings Date", "ORCL", "AAPL"],
                "Earnings Date": ["Earnings Date", "2026-03-10", "2026-03-15"],
            }
        )
        out = normalize_earnings_calendar_df(df, start=dt.date(2026, 3, 1), end=dt.date(2026, 3, 31))
        self.assertEqual(set(out["symbol"].tolist()), {"ORCL", "AAPL"})


if __name__ == "__main__":
    unittest.main()
