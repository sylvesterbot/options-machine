from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
import pandas as pd


class BaseDataProvider(ABC):
    @abstractmethod
    def get_underlying_prices(self, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame: ...

    @abstractmethod
    def get_options_chain(self, symbol: str, date: dt.date) -> pd.DataFrame: ...

    @abstractmethod
    def get_earnings_calendar(self, start: dt.date, end: dt.date) -> pd.DataFrame: ...
