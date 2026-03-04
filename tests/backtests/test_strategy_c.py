import datetime as dt
import unittest

import pandas as pd

from backtests.providers.base import BaseDataProvider
from backtests.strategy_c import simulate_strategy_c
from backtests.run_walkforward import run_walkforward


class TinyProviderC(BaseDataProvider):
    def __init__(self):
        self.price_df = pd.DataFrame(
            {
                "date": pd.to_datetime([
                    "2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07", "2020-01-08", "2020-01-09"
                ]).date,
                "symbol": ["SPY"] * 6,
                "close": [100, 101, 102, 103, 104, 105],
            }
        )

    def get_underlying_prices(self, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
        return self.price_df[(self.price_df["date"] >= start) & (self.price_df["date"] <= end)].copy()

    def get_options_chain(self, symbol: str, date: dt.date) -> pd.DataFrame:
        exp = date + dt.timedelta(days=30)
        return pd.DataFrame([
            {"expiration": exp, "strike": 90, "option_type": "put", "implied_volatility": 0.46},
            {"expiration": exp, "strike": 95, "option_type": "put", "implied_volatility": 0.40},
            {"expiration": exp, "strike": 100, "option_type": "put", "implied_volatility": 0.30},
            {"expiration": exp, "strike": 100, "option_type": "call", "implied_volatility": 0.30},
            {"expiration": exp, "strike": 105, "option_type": "call", "implied_volatility": 0.36},
            {"expiration": exp, "strike": 110, "option_type": "call", "implied_volatility": 0.40},
        ])

    def get_earnings_calendar(self, start: dt.date, end: dt.date) -> pd.DataFrame:
        return pd.DataFrame(columns=["symbol", "earnings_date"])


class StrategyCTests(unittest.TestCase):
    def test_simulate_strategy_c_generates_trades(self):
        trades = simulate_strategy_c(TinyProviderC(), "SPY", dt.date(2020, 1, 2), dt.date(2020, 1, 9), holding_days=2)
        self.assertGreaterEqual(len(trades), 1)
        self.assertIn("return_pct", trades.columns)


if __name__ == "__main__":
    unittest.main()
