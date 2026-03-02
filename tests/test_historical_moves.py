import datetime as dt
import math
import unittest

import pandas as pd

from scanner.historical_moves import compute_historical_move_stats_from_data


class HistoricalMovesTests(unittest.TestCase):
    def test_compute_historical_move_stats_from_data(self) -> None:
        earnings_dates = [
            dt.datetime(2025, 1, 31),
            dt.datetime(2024, 10, 31),
        ]
        prices = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    [
                        "2024-10-30",
                        "2024-11-01",
                        "2025-01-30",
                        "2025-02-03",
                    ]
                ),
                "close": [100.0, 106.0, 110.0, 99.0],
            }
        )

        stats = compute_historical_move_stats_from_data(
            earnings_dates=earnings_dates,
            price_history=prices,
            current_expected_move=0.08,
        )

        self.assertAlmostEqual(stats["avg_hist_move"], 0.08, places=6)
        self.assertAlmostEqual(stats["max_hist_move"], 0.10, places=6)
        self.assertEqual(stats["num_earnings"], 2)
        self.assertAlmostEqual(stats["move_ratio"], 1.0, places=6)


    def test_handles_unparseable_earnings_dates(self) -> None:
        prices = pd.DataFrame({"date": pd.to_datetime(["2024-10-30", "2024-11-01"]), "close": [100.0, 106.0]})
        stats = compute_historical_move_stats_from_data(earnings_dates=["Earnings Date"], price_history=prices, current_expected_move=0.08)
        self.assertEqual(stats["num_earnings"], 0)


    def test_relative_value_predictors(self) -> None:
        earnings_dates = [dt.datetime(2025, 1, 31), dt.datetime(2024, 10, 31)]
        prices = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-10-30", "2024-11-01", "2025-01-30", "2025-02-03"]),
                "close": [100.0, 106.0, 110.0, 99.0],
            }
        )
        stats = compute_historical_move_stats_from_data(earnings_dates=earnings_dates, price_history=prices, current_expected_move=0.08)
        self.assertTrue(math.isclose(stats["implied_vs_last_implied"], 1.3333333333, rel_tol=1e-6))
        self.assertTrue(math.isclose(stats["implied_vs_last_realized"], 0.02, rel_tol=1e-6))
        self.assertTrue(math.isclose(stats["implied_vs_avg_implied"], 1.0, rel_tol=1e-6))


if __name__ == "__main__":
    unittest.main()
