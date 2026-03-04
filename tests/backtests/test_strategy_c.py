import datetime as dt
import unittest

import pandas as pd

from backtests.providers.base import BaseDataProvider
from backtests.strategy_c import simulate_strategy_c


class TinyProviderC(BaseDataProvider):
    def __init__(self, mode: str = "rich"):
        self.mode = mode
        self.price_df = pd.DataFrame(
            {
                "date": pd.to_datetime([
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-06",
                    "2020-01-07",
                    "2020-01-08",
                    "2020-01-09",
                    "2020-01-10",
                ]).date,
                "symbol": ["SPY"] * 7,
                "close": [100, 101, 102, 103, 104, 103, 102],
            }
        )

    def get_underlying_prices(self, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
        return self.price_df[(self.price_df["date"] >= start) & (self.price_df["date"] <= end)].copy()

    def get_options_chain(self, symbol: str, date: dt.date) -> pd.DataFrame:
        exp = dt.date(2020, 2, 7)

        # flatten skew when requested
        if self.mode == "flat":
            put_95_iv = 0.30
        else:
            put_95_iv = 0.44

        # force spread blowout on day 2 to trigger stop-loss
        if self.mode == "stop" and date >= dt.date(2020, 1, 6):
            p95_mid, p90_mid = 4.20, 0.20
        else:
            p95_mid, p90_mid = 2.00, 0.70

        rows = [
            {"expiration": exp, "strike": 90, "option_type": "put", "implied_volatility": 0.34, "bid": p90_mid - 0.05, "ask": p90_mid + 0.05},
            {"expiration": exp, "strike": 95, "option_type": "put", "implied_volatility": put_95_iv, "bid": p95_mid - 0.05, "ask": p95_mid + 0.05},
            {"expiration": exp, "strike": 100, "option_type": "put", "implied_volatility": 0.30, "bid": 1.20, "ask": 1.30},
            {"expiration": exp, "strike": 100, "option_type": "call", "implied_volatility": 0.30, "bid": 1.10, "ask": 1.20},
            {"expiration": exp, "strike": 105, "option_type": "call", "implied_volatility": 0.34, "bid": 0.80, "ask": 0.90},
            {"expiration": exp, "strike": 110, "option_type": "call", "implied_volatility": 0.38, "bid": 0.60, "ask": 0.70},
        ]
        return pd.DataFrame(rows)

    def get_earnings_calendar(self, start: dt.date, end: dt.date) -> pd.DataFrame:
        return pd.DataFrame(columns=["symbol", "earnings_date"])


class StrategyCTests(unittest.TestCase):
    def test_expected_columns_and_trade_when_skew_rich(self):
        trades = simulate_strategy_c(
            TinyProviderC("rich"),
            "SPY",
            dt.date(2020, 1, 2),
            dt.date(2020, 1, 10),
            holding_days=2,
            rv_edge_min=0.0,
        )
        self.assertGreaterEqual(len(trades), 1)
        for col in [
            "symbol",
            "entry_date",
            "exit_date",
            "short_strike",
            "long_strike",
            "entry_credit",
            "exit_cost",
            "max_loss",
            "entry_price",
            "exit_price",
            "return_pct",
            "alloc",
            "portfolio_return",
            "capital",
            "put_skew",
            "rv_edge",
            "stopped_out",
        ]:
            self.assertIn(col, trades.columns)

    def test_zero_trades_when_skew_flat(self):
        trades = simulate_strategy_c(
            TinyProviderC("flat"),
            "SPY",
            dt.date(2020, 1, 2),
            dt.date(2020, 1, 10),
            holding_days=2,
            rv_edge_min=0.0,
        )
        self.assertEqual(len(trades), 0)

    def test_stopped_out_true_when_spread_blows_out(self):
        trades = simulate_strategy_c(
            TinyProviderC("stop"),
            "SPY",
            dt.date(2020, 1, 2),
            dt.date(2020, 1, 10),
            holding_days=3,
            stop_loss_pct=-0.10,
        )
        self.assertGreaterEqual(len(trades), 1)
        self.assertTrue(bool(trades.iloc[0]["stopped_out"]))


if __name__ == "__main__":
    unittest.main()
