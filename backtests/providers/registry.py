from __future__ import annotations

from backtests.providers.base import BaseDataProvider
from backtests.providers.mock_sample import MockSampleProvider
from backtests.providers.lambdaclass_data_v1 import LambdaClassDataV1Provider


class _NotImplementedProvider(BaseDataProvider):
    def __init__(self, name: str) -> None:
        self.name = name

    def _err(self):
        raise NotImplementedError(f"Provider '{self.name}' stub exists but adapter is not implemented yet")

    def get_underlying_prices(self, symbol, start, end):
        self._err()

    def get_options_chain(self, symbol, date):
        self._err()

    def get_earnings_calendar(self, start, end):
        self._err()


def resolve_provider(name: str, **config) -> BaseDataProvider:
    key = (name or "").strip().lower()
    if key == "mock":
        return MockSampleProvider()
    if key == "lambdaclass":
        return LambdaClassDataV1Provider(**config)
    if key in {"polygon", "thetadata", "eodhd"}:
        return _NotImplementedProvider(key)
    raise ValueError(f"Unsupported provider '{name}'. Supported: lambdaclass, mock, polygon, thetadata, eodhd")
