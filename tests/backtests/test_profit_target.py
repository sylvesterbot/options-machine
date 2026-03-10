import datetime as dt
import unittest

import pandas as pd

from backtests.strategy_b import simulate_strategy_b
from backtests.strategy_c import simulate_strategy_c


class MockProvider:
    def get_underlying_prices(self, symbol, start, end):
        dates = pd.date_range(start, end, freq="B")
        return pd.DataFrame({"date": dates, "close": [100 + i * 0.1 for i in range(len(dates))]})

    def get_options_chain(self, symbol, date):
        exp = pd.Timestamp(date).date() + dt.timedelta(days=30)
        return pd.DataFrame(
            {
                "expiration": [exp] * 6,
                "strike": [95, 90, 85, 95, 90, 85],
                "option_type": ["put"] * 6,
                "implied_volatility": [0.40, 0.45, 0.50, 0.40, 0.45, 0.50],
                "delta": [-0.30, -0.25, -0.15, -0.30, -0.25, -0.15],
                "bid": [2.0, 3.0, 1.5, 2.0, 3.0, 1.5],
                "ask": [2.2, 3.2, 1.7, 2.2, 3.2, 1.7],
                "volume": [100] * 6,
                "open_interest": [500] * 6,
            }
        )


class TestProfitTarget(unittest.TestCase):
    def test_strategy_c_exit_reason_column_exists(self):
        p = MockProvider()
        df = simulate_strategy_c(
            p,
            "TEST",
            dt.date(2024, 1, 1),
            dt.date(2024, 3, 1),
            target_profit_pct=0.50,
        )
        self.assertIn("exit_reason", df.columns)
        if not df.empty:
            for reason in df["exit_reason"]:
                self.assertIn(reason, ["profit_target", "stop_loss", "expiry"])

    def test_strategy_b_accepts_target_profit_pct_param(self):
        p = MockProvider()
        df = simulate_strategy_b(
            p,
            "TEST",
            dt.date(2024, 1, 1),
            dt.date(2024, 1, 31),
            target_profit_pct=0.20,
        )
        self.assertIsInstance(df, pd.DataFrame)
