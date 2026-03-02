import datetime as dt
import unittest

import pandas as pd

from backtests.strategy_b import simulate_strategy_b, summarize_trade_log
from backtests.providers.base import BaseDataProvider


class TinyProvider(BaseDataProvider):
    def __init__(self):
        self.price_df = pd.DataFrame(
            {
                "date": pd.to_datetime([
                    "2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07", "2020-01-08",
                    "2020-01-09", "2020-01-10", "2020-01-13", "2020-01-14", "2020-01-15",
                    "2020-01-16", "2020-01-17", "2020-01-21",
                ]).date,
                "symbol": ["SPY"] * 13,
                "close": [100, 101, 102, 103, 104, 105, 106, 104, 103, 102, 101, 100, 99],
            }
        )

    def get_underlying_prices(self, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
        return self.price_df[(self.price_df["date"] >= start) & (self.price_df["date"] <= end)].copy()

    def get_options_chain(self, symbol: str, date: dt.date) -> pd.DataFrame:
        # front very rich at entry to trigger FF, then normalizes by day 6
        iv_front = 0.45 if date <= dt.date(2020, 1, 3) else 0.20
        iv_back = 0.35
        rows = []
        for exp, iv in [(dt.date(2020, 2, 14), iv_front), (dt.date(2020, 3, 20), iv_back), (dt.date(2020, 4, 17), 0.18)]:
            for strike in [100, 105]:
                dte = (exp - date).days
                mid = 1.0 + iv * 2.0 + dte * 0.10 + (0.2 if strike == 100 else 0.4)
                rows.append({
                    "date": date,
                    "symbol": symbol,
                    "expiration": exp,
                    "strike": strike,
                    "option_type": "call",
                    "bid": mid - 0.1,
                    "ask": mid + 0.1,
                    "implied_volatility": iv,
                })
        return pd.DataFrame(rows)

    def get_earnings_calendar(self, start: dt.date, end: dt.date) -> pd.DataFrame:
        return pd.DataFrame(columns=["symbol", "earnings_date"])


class StrategyBSimTests(unittest.TestCase):
    def test_generates_trades_and_returns(self):
        trades = simulate_strategy_b(
            provider=TinyProvider(),
            symbol="SPY",
            start=dt.date(2020, 1, 2),
            end=dt.date(2020, 1, 21),
            ff_threshold=0.2,
            holding_days=10,
            exit_mode="fixed",
        )
        self.assertGreaterEqual(len(trades), 1)
        self.assertIn("entry_date", trades.columns)
        self.assertIn("exit_date", trades.columns)
        self.assertIn("entry_price", trades.columns)
        self.assertIn("exit_price", trades.columns)
        self.assertIn("return_pct", trades.columns)

    def test_summary_metrics_shape(self):
        trades = pd.DataFrame({"return_pct": [0.1, -0.05, 0.03, 0.02]})
        summary = summarize_trade_log(trades)
        self.assertIn("total_return", summary)
        self.assertIn("avg_return", summary)
        self.assertIn("volatility", summary)
        self.assertIn("max_drawdown", summary)


if __name__ == "__main__":
    unittest.main()
