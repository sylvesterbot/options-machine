import datetime as dt
import unittest

import pandas as pd

from backtests.providers.base import BaseDataProvider
from backtests.strategy_b import simulate_strategy_b


class StopLossProvider(BaseDataProvider):
    def __init__(self):
        self.price_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"]).date,
                "symbol": ["SPY"] * 4,
                "close": [100, 100, 100, 100],
            }
        )

    def get_underlying_prices(self, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
        return self.price_df[(self.price_df["date"] >= start) & (self.price_df["date"] <= end)].copy()

    def get_options_chain(self, symbol: str, date: dt.date) -> pd.DataFrame:
        front = dt.date(2020, 2, 14)
        back = dt.date(2020, 3, 20)

        # Entry debit = 2.0
        if date == dt.date(2020, 1, 2):
            mids = {(front, 100): 2.0, (back, 100): 4.0}
        # Next day crash to debit = 1.0 => -50% stop hit
        elif date == dt.date(2020, 1, 3):
            mids = {(front, 100): 2.0, (back, 100): 3.0}
        else:
            mids = {(front, 100): 2.0, (back, 100): 3.0}

        rows = []
        for (exp, strike), mid in mids.items():
            rows.append(
                {
                    "date": date,
                    "symbol": symbol,
                    "expiration": exp,
                    "strike": strike,
                    "option_type": "call",
                    "bid": mid - 0.05,
                    "ask": mid + 0.05,
                    "implied_volatility": 0.30 if exp == front else 0.20,
                }
            )

        # add a third expiry so FF pair logic has choices
        rows.append(
            {
                "date": date,
                "symbol": symbol,
                "expiration": dt.date(2020, 4, 17),
                "strike": 100,
                "option_type": "call",
                "bid": 1.0,
                "ask": 1.1,
                "implied_volatility": 0.15,
            }
        )
        return pd.DataFrame(rows)

    def get_earnings_calendar(self, start: dt.date, end: dt.date) -> pd.DataFrame:
        return pd.DataFrame(columns=["symbol", "earnings_date"])


class StopLossTests(unittest.TestCase):
    def test_intra_trade_stop_loss_marks_trade(self):
        trades = simulate_strategy_b(
            provider=StopLossProvider(),
            symbol="SPY",
            start=dt.date(2020, 1, 2),
            end=dt.date(2020, 1, 7),
            ff_threshold=0.0,
            holding_days=3,
            stop_loss_pct=-0.20,
        )
        self.assertGreaterEqual(len(trades), 1)
        self.assertTrue(bool(trades.iloc[0]["stopped_out"]))
        self.assertLessEqual(float(trades.iloc[0]["return_pct"]), -0.20)


if __name__ == "__main__":
    unittest.main()
