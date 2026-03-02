from __future__ import annotations

import datetime as dt
from pathlib import Path
import pandas as pd

from backtests.providers.base import BaseDataProvider


class LambdaClassDataV1Provider(BaseDataProvider):
    """Adapter for lambdaclass/options_portfolio_backtester data-v1 style local extracts.

    Expected folder layout (config root_dir):
      root_dir/
        underlying_prices.csv   required
        options_eod.csv         required
        earnings_calendar.csv   optional

    Canonical normalized fields returned:
      underlying_prices: [date, symbol, close]
      options_chain: [date, symbol, expiration, strike, option_type, bid, ask]
      earnings_calendar: [symbol, earnings_date]
    """

    def __init__(self, root_dir: str = "data/lambdaclass-data-v1") -> None:
        self.root_dir = Path(root_dir)
        self._underlying = self._load_underlying()
        self._options = self._load_options()
        self._earnings = self._load_earnings()

    def _require_cols(self, df: pd.DataFrame, required: list[str], source: str) -> None:
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"{source} missing required columns: {missing}. Found={list(df.columns)}")

    def _load_underlying(self) -> pd.DataFrame:
        p = self.root_dir / "underlying_prices.csv"
        if not p.exists():
            raise FileNotFoundError(f"Missing underlying file: {p}")
        raw = pd.read_csv(p)
        colmap = {c.lower(): c for c in raw.columns}
        ren = {}
        if "date" in colmap:
            ren[colmap["date"]] = "date"
        if "symbol" in colmap:
            ren[colmap["symbol"]] = "symbol"
        if "close" in colmap:
            ren[colmap["close"]] = "close"
        elif "underlying_close" in colmap:
            ren[colmap["underlying_close"]] = "close"
        df = raw.rename(columns=ren)
        self._require_cols(df, ["date", "symbol", "close"], str(p))
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["symbol"] = df["symbol"].astype(str).str.upper()
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        return df.dropna(subset=["date", "symbol", "close"]).copy()

    def _load_options(self) -> pd.DataFrame:
        p = self.root_dir / "options_eod.csv"
        if not p.exists():
            raise FileNotFoundError(f"Missing options file: {p}")
        raw = pd.read_csv(p)
        colmap = {c.lower(): c for c in raw.columns}
        ren = {}
        for source, target in [
            ("date", "date"),
            ("symbol", "symbol"),
            ("expiration", "expiration"),
            ("expiry", "expiration"),
            ("strike", "strike"),
            ("option_type", "option_type"),
            ("type", "option_type"),
            ("bid", "bid"),
            ("ask", "ask"),
            ("implied_volatility", "implied_volatility"),
            ("iv", "implied_volatility"),
        ]:
            if source in colmap:
                ren[colmap[source]] = target
        df = raw.rename(columns=ren)
        self._require_cols(df, ["date", "symbol", "expiration", "strike", "option_type", "bid", "ask"], str(p))
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["expiration"] = pd.to_datetime(df["expiration"], errors="coerce").dt.date
        df["symbol"] = df["symbol"].astype(str).str.upper()
        df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
        df["bid"] = pd.to_numeric(df["bid"], errors="coerce")
        df["ask"] = pd.to_numeric(df["ask"], errors="coerce")
        df["option_type"] = df["option_type"].astype(str).str.lower().str[0].map({"c": "call", "p": "put"})
        if "implied_volatility" in df.columns:
            df["implied_volatility"] = pd.to_numeric(df["implied_volatility"], errors="coerce")
        return df.dropna(subset=["date", "symbol", "expiration", "strike", "option_type", "bid", "ask"]).copy()

    def _load_earnings(self) -> pd.DataFrame:
        p = self.root_dir / "earnings_calendar.csv"
        if not p.exists():
            return pd.DataFrame(columns=["symbol", "earnings_date"])
        raw = pd.read_csv(p)
        colmap = {c.lower(): c for c in raw.columns}
        ren = {}
        if "symbol" in colmap:
            ren[colmap["symbol"]] = "symbol"
        if "earnings_date" in colmap:
            ren[colmap["earnings_date"]] = "earnings_date"
        elif "date" in colmap:
            ren[colmap["date"]] = "earnings_date"
        df = raw.rename(columns=ren)
        self._require_cols(df, ["symbol", "earnings_date"], str(p))
        df["symbol"] = df["symbol"].astype(str).str.upper()
        df["earnings_date"] = pd.to_datetime(df["earnings_date"], errors="coerce").dt.date
        return df.dropna(subset=["symbol", "earnings_date"]).copy()

    def get_underlying_prices(self, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
        s = symbol.upper()
        df = self._underlying[(self._underlying["symbol"] == s) & (self._underlying["date"] >= start) & (self._underlying["date"] <= end)]
        return df[["date", "symbol", "close"]].sort_values("date").reset_index(drop=True)

    def get_options_chain(self, symbol: str, date: dt.date) -> pd.DataFrame:
        s = symbol.upper()
        df = self._options[(self._options["symbol"] == s) & (self._options["date"] == date)]
        cols = ["date", "symbol", "expiration", "strike", "option_type", "bid", "ask"]
        if "implied_volatility" in df.columns:
            cols.append("implied_volatility")
        return df[cols].sort_values(["expiration", "strike"]).reset_index(drop=True)

    def get_earnings_calendar(self, start: dt.date, end: dt.date) -> pd.DataFrame:
        if self._earnings.empty:
            return self._earnings.copy()
        df = self._earnings[(self._earnings["earnings_date"] >= start) & (self._earnings["earnings_date"] <= end)]
        return df[["symbol", "earnings_date"]].sort_values("earnings_date").reset_index(drop=True)
