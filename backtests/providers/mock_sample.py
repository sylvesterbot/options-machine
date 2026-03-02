from __future__ import annotations

import datetime as dt
import pandas as pd

from backtests.providers.base import BaseDataProvider


class MockSampleProvider(BaseDataProvider):
    def get_underlying_prices(self, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
        dates = pd.date_range(start, end, freq="B")
        return pd.DataFrame({"date": dates.date, "close": [100 + i * 0.1 for i in range(len(dates))]})

    def get_options_chain(self, symbol: str, date: dt.date) -> pd.DataFrame:
        expiries = [date + dt.timedelta(days=28), date + dt.timedelta(days=42), date + dt.timedelta(days=70)]
        rows = []
        for exp in expiries:
            for strike in (95, 100, 105):
                rows.append({"expiration": exp, "strike": strike, "option_type": "call", "bid": 2.0, "ask": 2.3})
                rows.append({"expiration": exp, "strike": strike, "option_type": "put", "bid": 2.1, "ask": 2.4})
        return pd.DataFrame(rows)

    def get_earnings_calendar(self, start: dt.date, end: dt.date) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"symbol": "MOCK", "earnings_date": start + dt.timedelta(days=20)},
                {"symbol": "MOCK", "earnings_date": start + dt.timedelta(days=80)},
            ]
        )
