#!/usr/bin/env python3
"""
OpenBB Earnings IV Scanner

Default behavior:
- Universe: S&P 500 (fallback list when unavailable)
- Earnings window: next 14 days
- Ranking: IV30/RV30 proxy (descending)
- Outputs:
  - CSV scan results
  - Markdown summary
  - JSONL backtest tracker append

Notes:
- Requires `openbb` package for full functionality.
- Some endpoint names vary across OpenBB versions; this script tries multiple paths.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scanner.forward_factor import compute_forward_factor
from scanner.skew_score import compute_skew_score
from scanner.momentum import compute_momentum
from scanner.historical_moves import compute_historical_move_stats


DEFAULT_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AMD", "NFLX", "AVGO",
    "JPM", "BAC", "XOM", "CVX", "UNH", "PFE", "KO", "PEP", "ORCL", "CRM",
    "NKE", "FDX", "DOCU", "KR", "COST", "JD", "ADBE", "NIO", "CCL", "DAL",
]


@dataclass
class ScanRow:
    symbol: str
    earnings_date: str
    spot: float
    iv30_proxy: float
    rv30: float
    iv_rv_ratio: float
    expected_move_pct: float
    option_volume: float
    open_interest: float
    avg_hist_move: float = float("nan")
    max_hist_move: float = float("nan")
    num_earnings: int = 0
    move_ratio: float = float("nan")
    # Strategy B: Forward Factor
    forward_factor: float = float("nan")
    ff_30_60: float = float("nan")
    ff_60_90: float = float("nan")
    ff_30_90: float = float("nan")
    ff_best: float = float("nan")
    ff_best_pair: str = "NONE"
    ff_signal: str = "NONE"
    front_iv: float = float("nan")
    back_iv: float = float("nan")
    days_to_earnings: int = 0
    earnings_distortion_flag: bool = False
    ff_note: str = "X_EARN"
    advice: str = ""
    suggested_allocation_pct: float = 0.04
    suggested_allocation_usd: float = float("nan")
    # Strategy C: Skew
    put_skew: float = float("nan")
    call_skew: float = float("nan")
    skew_signal: str = "NONE"
    # Momentum
    momentum_pct: float = float("nan")
    momentum_dir: str = "NEUTRAL"
    # Combined
    strategies: str = ""


class OpenBBClient:
    def __init__(self) -> None:
        try:
            from openbb import obb  # type: ignore
        except Exception as exc:
            raise RuntimeError("openbb package not installed. Install with: pip install openbb") from exc
        self.obb = obb

    def _call_paths(self, paths: Iterable[str], **kwargs: Any) -> Any:
        errors: list[str] = []
        for path in paths:
            try:
                obj = self.obb
                for token in path.split("."):
                    obj = getattr(obj, token)
                res = obj(**kwargs)
                if hasattr(res, "to_df"):
                    return res.to_df()
                return res
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{path}: {exc}")
        raise RuntimeError(f"All OpenBB endpoint paths failed. Tried={list(paths)}; errors={errors}")

    def get_sp500_universe(self) -> list[str]:
        try:
            df = self._call_paths(
                [
                    "equity.profile.indices_constituents",
                    "equity.search.indices_constituents",
                    "equity.discovery.indices_constituents",
                ],
                symbol="SPX",
            )
            if isinstance(df, pd.DataFrame):
                col = "symbol" if "symbol" in df.columns else df.columns[0]
                tickers = sorted(set(df[col].astype(str).str.upper()))
                return [t for t in tickers if t.isalpha()]
        except Exception:
            pass
        return DEFAULT_TICKERS

    def get_earnings_calendar(self, symbols: list[str], start: dt.date, end: dt.date) -> pd.DataFrame:
        paths = [
            "equity.calendar.earnings",
            "equity.fundamental.earnings_calendar",
        ]

        attempts: list[tuple[dict[str, Any], str]] = [
            ({"symbol": symbols, "start_date": start.isoformat(), "end_date": end.isoformat()}, "symbol=list + date range"),
            ({"symbols": symbols, "start_date": start.isoformat(), "end_date": end.isoformat()}, "symbols=list + date range"),
            ({"symbol": symbols}, "symbol=list"),
            ({"symbols": symbols}, "symbols=list"),
        ]

        def _normalize(df: pd.DataFrame) -> pd.DataFrame:
            cols = {c.lower(): c for c in df.columns}
            sym_col = cols.get("symbol") or cols.get("ticker")
            date_col = cols.get("date") or cols.get("earnings_date") or cols.get("report_date")
            if not sym_col or not date_col:
                raise RuntimeError(f"Earnings calendar missing required columns; got {list(df.columns)}")
            out_df = df.rename(columns={sym_col: "symbol", date_col: "earnings_date"}).copy()
            out_df["symbol"] = out_df["symbol"].astype(str).str.upper()
            out_df["earnings_date"] = pd.to_datetime(out_df["earnings_date"], errors="coerce").dt.date
            out_df = out_df[["symbol", "earnings_date"]].dropna().drop_duplicates()
            out_df = out_df[(out_df["earnings_date"] >= start) & (out_df["earnings_date"] <= end)]
            return out_df

        # 1) bulk attempts
        for kwargs, _label in attempts:
            try:
                out = self._call_paths(paths, **kwargs)
                if isinstance(out, pd.DataFrame) and not out.empty:
                    n = _normalize(out)
                    if not n.empty:
                        return n
            except Exception:
                pass

        # 2) per-symbol fallback (more compatible across providers)
        rows: list[pd.DataFrame] = []
        for s in symbols:
            try:
                out = self._call_paths(
                    paths,
                    symbol=s,
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                )
            except Exception:
                try:
                    out = self._call_paths(paths, symbol=s)
                except Exception:
                    continue

            if isinstance(out, pd.DataFrame) and not out.empty:
                try:
                    rows.append(_normalize(out))
                except Exception:
                    continue

        if not rows:
            return pd.DataFrame(columns=["symbol", "earnings_date"])
        return pd.concat(rows, ignore_index=True).drop_duplicates()

    def get_earnings_fallback(self, symbols: list[str], start: dt.date, end: dt.date) -> pd.DataFrame:
        """Fallback: scrape Yahoo Finance earnings calendar."""
        import requests
        from io import StringIO
        all_rows = []
        current = start
        while current <= end:
            try:
                url = f"https://finance.yahoo.com/calendar/earnings?day={current.isoformat()}"
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}, timeout=15)
                tables = pd.read_html(StringIO(r.text))
                if tables:
                    df = tables[0]
                    sym_cols = [c for c in df.columns if "symbol" in c.lower() or "ticker" in c.lower()]
                    if sym_cols:
                        for s in df[sym_cols[0]]:
                            su = str(s).upper().strip()
                            if su in symbols:
                                all_rows.append({"symbol": su, "earnings_date": current})
            except Exception:
                pass
            current += dt.timedelta(days=1)
        if all_rows:
            return pd.DataFrame(all_rows).drop_duplicates()
        return pd.DataFrame(columns=["symbol", "earnings_date"])

    def get_price_history(self, symbol: str, days: int = 90) -> pd.DataFrame:
        end = dt.date.today()
        start = end - dt.timedelta(days=days + 10)
        out = self._call_paths(
            ["equity.price.historical"],
            symbol=symbol,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            provider="yfinance",
        )
        if not isinstance(out, pd.DataFrame):
            raise RuntimeError("Unexpected price history response")
        # yfinance returns date as index — reset it to a column
        if out.index.name and out.index.name.lower() == "date":
            out = out.reset_index()
        cols = {c.lower(): c for c in out.columns}
        close_col = cols.get("close") or cols.get("adj_close")
        date_col = cols.get("date") or cols.get("timestamp")
        if not close_col:
            raise RuntimeError(f"No close column in price history for {symbol}")
        df = out.copy()
        if date_col:
            df["date"] = pd.to_datetime(df[date_col], errors="coerce")
        df["close"] = pd.to_numeric(df[close_col], errors="coerce")
        return df[["date", "close"]].dropna().sort_values("date")

    def get_options_chain(self, symbol: str) -> pd.DataFrame:
        out = self._call_paths(
            ["derivatives.options.chains"],
            symbol=symbol,
            provider="yfinance",
        )
        if not isinstance(out, pd.DataFrame):
            raise RuntimeError("Unexpected options chain response")
        df = out.copy()
        rename = {}
        low = {c.lower(): c for c in df.columns}
        for want in ["expiration", "strike", "option_type", "implied_volatility", "volume", "open_interest", "last_price", "last_trade_price"]:
            if want in low:
                rename[low[want]] = want
        # Map last_trade_price to last_price if needed
        if "last_trade_price" in df.columns and "last_price" not in df.columns:
            df = df.rename(columns={"last_trade_price": "last_price"})
        if rename:
            df = df.rename(columns=rename)
        if "expiration" not in df.columns or "strike" not in df.columns:
            raise RuntimeError(f"Options chain missing key columns for {symbol}; cols={list(df.columns)}")
        df["expiration"] = pd.to_datetime(df["expiration"], errors="coerce").dt.date
        for c in ["strike", "implied_volatility", "volume", "open_interest", "last_price"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df.dropna(subset=["expiration", "strike"]) 


def realized_vol_30(price_df: pd.DataFrame) -> float:
    if len(price_df) < 35:
        return float("nan")
    r = np.log(price_df["close"] / price_df["close"].shift(1)).dropna()
    r30 = r.tail(30)
    if len(r30) < 10:
        return float("nan")
    return float(r30.std(ddof=1) * math.sqrt(252))


def select_30d_atm(chain: pd.DataFrame, spot: float) -> tuple[pd.DataFrame, dt.date] | tuple[None, None]:
    today = dt.date.today()
    expiries = sorted([e for e in chain["expiration"].dropna().unique() if e > today])
    if not expiries:
        return None, None
    target = today + dt.timedelta(days=30)
    expiry = min(expiries, key=lambda e: abs((e - target).days))
    e_df = chain[chain["expiration"] == expiry].copy()
    if e_df.empty:
        return None, None
    e_df["dist"] = (e_df["strike"] - spot).abs()
    min_dist = e_df["dist"].min()
    atm = e_df[e_df["dist"] == min_dist].copy()
    return atm, expiry


def implied_move_pct(atm: pd.DataFrame, spot: float) -> float:
    if "option_type" not in atm.columns or "last_price" not in atm.columns:
        return float("nan")
    c = atm[atm["option_type"].astype(str).str.lower().str.startswith("c")]["last_price"]
    p = atm[atm["option_type"].astype(str).str.lower().str.startswith("p")]["last_price"]
    if c.empty or p.empty or not spot:
        return float("nan")
    return float((c.iloc[0] + p.iloc[0]) / spot)




def build_advice(strategies: str, ff_note: str = "") -> str:
    strategy_set = {x.strip() for x in (strategies or "").split(",") if x.strip()}
    advice_parts: list[str] = []
    if "A" in strategy_set:
        advice_parts.append("Hold-through-earnings: Long calendar spread (sell front, buy back month).")
        advice_parts.append("If selling premium, use defined-risk only (iron condor/iron fly) with explicit tail-risk controls.")
        advice_parts.append("Short straddle is only for pre-announcement IV ramp harvesting and should be exited BEFORE earnings.")
    if "B" in strategy_set:
        advice_parts.append("Forward Factor supports calendar structures; prefer X-earn windows.")
    if ff_note == "EARNINGS_IN_WINDOW":
        advice_parts.append("Earnings distortion present: treat FF signal as potentially event-distorted.")
    if "C" in strategy_set:
        advice_parts.append("For skew/momentum setups, prefer defined-risk verticals.")
    return " ".join(advice_parts) if advice_parts else "No high-conviction setup."


def compute_earnings_distortion(earnings_date: dt.date, pair_expiries: dict[str, list[str]], ff_best_pair: str) -> tuple[bool, str]:
    if ff_best_pair not in pair_expiries:
        return False, "X_EARN"
    try:
        front_exp = dt.date.fromisoformat(pair_expiries[ff_best_pair][0])
    except Exception:
        return False, "X_EARN"
    distorted = earnings_date <= front_exp
    return distorted, ("EARNINGS_IN_WINDOW" if distorted else "X_EARN")





def load_kelly_calibration(path: str = "data/kelly_calibration.json") -> dict[str, float]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, float] = {}
    for k, v in data.items():
        try:
            out[str(k)] = float(v)
        except Exception:
            continue
    return out

def compute_suggested_allocation(
    strategies: str,
    ff_signal: str,
    earnings_distortion_flag: bool,
    momentum_dir: str,
    skew_signal: str,
    capital: float | None = None,
    default_alloc: float = 0.04,
) -> tuple[float, float]:
    alloc = float(default_alloc)
    strat_set = {x.strip() for x in (strategies or "").split(",") if x.strip()}

    if "B" in strat_set and ff_signal == "STRONG" and not earnings_distortion_flag:
        alloc += 0.01
    if "A" in strat_set:
        alloc -= 0.01
    if ("C" in strat_set) and (momentum_dir in {"BULLISH", "BEARISH"}) and (skew_signal != "NONE"):
        alloc += 0.005
    if earnings_distortion_flag and "B" in strat_set:
        alloc -= 0.01

    alloc = min(0.08, max(0.02, alloc))
    usd = float("nan") if capital is None else float(capital) * alloc
    return float(alloc), float(usd)

def scan(window_days: int, top_n: int, min_oi: int, min_vol: int, debug: bool = False, capital: float | None = None, default_alloc: float = 0.04) -> pd.DataFrame:
    obb = OpenBBClient()
    tickers = obb.get_sp500_universe()
    start = dt.date.today()
    end = start + dt.timedelta(days=window_days)
    earnings = obb.get_earnings_calendar(tickers, start, end)
    if earnings.empty:
        if hasattr(obb, "get_earnings_fallback"):
            earnings = obb.get_earnings_fallback(tickers, start, end)
    if earnings.empty:
        # Last resort: hardcoded known upcoming earnings for testing
        test_earnings = [
            ("NKE", "2026-03-20"), ("FDX", "2026-03-18"), ("DOCU", "2026-03-13"),
            ("ORCL", "2026-03-10"), ("KR", "2026-03-06"), ("AVGO", "2026-03-06"),
            ("COST", "2026-03-06"), ("JD", "2026-03-13"), ("ADBE", "2026-03-12"),
        ]
        rows_fb = [{"symbol": s, "earnings_date": dt.date.fromisoformat(d)} 
                   for s, d in test_earnings 
                   if start <= dt.date.fromisoformat(d) <= end and s in tickers]
        if rows_fb:
            earnings = pd.DataFrame(rows_fb)

    if debug:
        print(f"[debug] universe_size={len(tickers)}")
        print(f"[debug] earnings_rows={len(earnings)} range={start}..{end}")

    rows: list[ScanRow] = []
    kelly_map = load_kelly_calibration()
    skip: dict[str, int] = {
        "price_empty": 0,
        "no_atm": 0,
        "low_liquidity": 0,
        "exception": 0,
    }
    exception_samples: list[str] = []

    for _, er in earnings.iterrows():
        symbol = er["symbol"]
        edate = er["earnings_date"]
        try:
            px = obb.get_price_history(symbol)
            if px.empty:
                skip["price_empty"] += 1
                continue
            spot = float(px["close"].iloc[-1])
            rv30 = realized_vol_30(px)

            chain = obb.get_options_chain(symbol)
            atm, _expiry = select_30d_atm(chain, spot)
            if atm is None or atm.empty:
                skip["no_atm"] += 1
                continue

            iv_col = "implied_volatility" if "implied_volatility" in atm.columns else None
            iv30 = float(atm[iv_col].dropna().mean()) if iv_col and atm[iv_col].notna().any() else float("nan")

            vol = float(atm["volume"].fillna(0).sum()) if "volume" in atm.columns else 0.0
            oi = float(atm["open_interest"].fillna(0).sum()) if "open_interest" in atm.columns else 0.0
            if oi < min_oi or vol < min_vol:
                skip["low_liquidity"] += 1
                continue

            iv_rv = float(iv30 / rv30) if rv30 and rv30 > 0 and not np.isnan(iv30) else float("nan")
            em = implied_move_pct(atm, spot)
            hist = compute_historical_move_stats(symbol=symbol, current_expected_move=em, obb_client=obb)

            # Strategy B: Forward Factor
            ff_data = compute_forward_factor(chain, spot)
            earnings_dt = edate if isinstance(edate, dt.date) else dt.date.fromisoformat(str(edate))
            days_to_earnings = (earnings_dt - dt.date.today()).days
            distorted, ff_note = compute_earnings_distortion(earnings_dt, ff_data.get("pair_expiries", {}), ff_data.get("ff_best_pair", "NONE"))
            # Strategy C: Skew
            skew_data = compute_skew_score(chain, spot, rv30)
            # Momentum
            mom_data = compute_momentum(px)

            # Determine which strategies apply
            strats = []
            if not np.isnan(iv_rv) and iv_rv >= 1.25:
                strats.append("A")
            if not np.isnan(ff_data.get("ff_best", float("nan"))) and ff_data.get("ff_best", float("nan")) >= 0.2:
                strats.append("B")
            if skew_data["skew_signal"] != "NONE" and mom_data["momentum_dir"] != "NEUTRAL":
                strats.append("C")

            strategies_joined = ",".join(strats) if strats else ""
            strategy_for_alloc = strategies_joined or "NONE"
            mapped_default = default_alloc
            for key in (strategy_for_alloc, *(x for x in strategy_for_alloc.split(",") if x)):
                if key in kelly_map:
                    mapped_default = float(kelly_map[key])
                    break
            alloc_pct, alloc_usd = compute_suggested_allocation(
                strategies=strategies_joined,
                ff_signal=ff_data.get("ff_signal", "NONE"),
                earnings_distortion_flag=distorted,
                momentum_dir=mom_data["momentum_dir"],
                skew_signal=skew_data["skew_signal"],
                capital=capital,
                default_alloc=mapped_default,
            )

            rows.append(
                ScanRow(
                    symbol=symbol,
                    earnings_date=str(edate),
                    spot=spot,
                    iv30_proxy=iv30,
                    rv30=rv30,
                    iv_rv_ratio=iv_rv,
                    expected_move_pct=em,
                    avg_hist_move=float(hist.get("avg_hist_move", float("nan"))),
                    max_hist_move=float(hist.get("max_hist_move", float("nan"))),
                    num_earnings=int(hist.get("num_earnings", 0) or 0),
                    move_ratio=float(hist.get("move_ratio", float("nan"))),
                    option_volume=vol,
                    open_interest=oi,
                    forward_factor=ff_data.get("forward_factor", float("nan")),
                    ff_30_60=ff_data.get("ff_30_60", float("nan")),
                    ff_60_90=ff_data.get("ff_60_90", float("nan")),
                    ff_30_90=ff_data.get("ff_30_90", float("nan")),
                    ff_best=ff_data.get("ff_best", float("nan")),
                    ff_best_pair=ff_data.get("ff_best_pair", "NONE"),
                    ff_signal=ff_data.get("ff_signal", "NONE"),
                    front_iv=ff_data.get("front_iv", float("nan")),
                    back_iv=ff_data.get("back_iv", float("nan")),
                    days_to_earnings=days_to_earnings,
                    earnings_distortion_flag=distorted,
                    ff_note=ff_note,
                    advice=build_advice(strategies_joined, ff_note=ff_note),
                    suggested_allocation_pct=alloc_pct,
                    suggested_allocation_usd=alloc_usd,
                    put_skew=skew_data.get("put_skew", float("nan")),
                    call_skew=skew_data.get("call_skew", float("nan")),
                    skew_signal=skew_data["skew_signal"],
                    momentum_pct=mom_data["momentum_pct"],
                    momentum_dir=mom_data["momentum_dir"],
                    strategies=strategies_joined,
                )
            )
        except Exception as exc:
            skip["exception"] += 1
            if debug and len(exception_samples) < 10:
                exception_samples.append(f"{symbol}: {exc}")
            continue

    if debug:
        print(f"[debug] kept_rows={len(rows)}")
        print(f"[debug] skips={skip}")
        if exception_samples:
            print("[debug] exception_samples:")
            for s in exception_samples:
                print(f"[debug]   {s}")

    if not rows:
        return pd.DataFrame(columns=[f.name for f in ScanRow.__dataclass_fields__.values()])

    df = pd.DataFrame([asdict(r) for r in rows])
    df = df.sort_values(by=["iv_rv_ratio", "iv30_proxy"], ascending=False).head(top_n)
    return df


def append_tracker(df: pd.DataFrame, path: Path, args: argparse.Namespace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "agent": "Devin",
        "strategy": "OpenBB Earnings IV Scanner",
        "params": {
            "window_days": args.window_days,
            "top_n": args.top_n,
            "min_oi": args.min_oi,
            "min_vol": args.min_vol,
        },
        "result_count": int(len(df)),
        "top_symbols": df["symbol"].tolist() if not df.empty else [],
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def to_markdown(df: pd.DataFrame, args: argparse.Namespace) -> str:
    ts = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# OpenBB Earnings IV Scanner Report",
        "",
        f"- Generated: {ts}",
        "- Agent: Devin",
        f"- Universe: S&P 500 (fallback list if unavailable)",
        f"- Earnings window: next {args.window_days} days",
        f"- Filters: min OI={args.min_oi}, min Volume={args.min_vol}",
        "- Ranking: IV30/RV30 proxy (desc), then IV30 proxy",
        "",
    ]
    if df.empty:
        lines += ["No candidates found for current constraints."]
        return "\n".join(lines)

    view = df.copy()
    for c in ["spot", "iv30_proxy", "rv30", "iv_rv_ratio", "expected_move_pct", "avg_hist_move", "max_hist_move", "move_ratio", "forward_factor", "ff_best", "option_volume", "open_interest"]:
        if c in view.columns:
            view[c] = pd.to_numeric(view[c], errors="coerce")

    lines += [
        "## Top Candidates",
        "",
        "| Symbol | Earnings | Spot | IV/RV | MvRatio | FFbest | FFpair | FFnote | Distorted? | Alloc% | Alloc$ | Skew | Mom | Strategies |",
        "|--------|----------|------|-------|---------|--------|--------|--------|------------|--------|--------|------|-----|------------|",
    ]
    for _, r in view.iterrows():
        d = r.to_dict()
        sym = d.get("symbol", "")
        edate = str(d.get("earnings_date", ""))
        spot = f"{d.get('spot', 0):.2f}"
        iv_rv = f"{d.get('iv_rv_ratio', 0):.2f}" if not np.isnan(d.get("iv_rv_ratio", float("nan"))) else "-"
        mv_ratio = f"{d.get('move_ratio', 0):.2f}" if not np.isnan(d.get("move_ratio", float("nan"))) else "-"
        ff = f"{d.get('ff_best', 0):.2f}" if not np.isnan(d.get("ff_best", float("nan"))) else "-"
        ff_pair = d.get("ff_best_pair", "-")
        ff_note = d.get("ff_note", "-")
        distorted = "Y" if bool(d.get("earnings_distortion_flag", False)) else "N"
        alloc_pct_v = d.get("suggested_allocation_pct", float("nan"))
        alloc_pct = f"{alloc_pct_v*100:.1f}%" if not np.isnan(alloc_pct_v) else "-"
        alloc_usd_v = d.get("suggested_allocation_usd", float("nan"))
        alloc_usd = f"${alloc_usd_v:,.0f}" if (hasattr(args, "capital") and getattr(args, "capital", None) is not None and not np.isnan(alloc_usd_v)) else "-"
        ps = f"{d.get('put_skew', 0):.2f}" if not np.isnan(d.get("put_skew", float("nan"))) else "-"
        mom = d.get("momentum_dir", "?")[:4]
        strats = d.get("strategies", "") or "-"
        lines.append(f"| {sym} | {edate} | {spot} | {iv_rv} | {mv_ratio} | {ff} | {ff_pair} | {ff_note} | {distorted} | {alloc_pct} | {alloc_usd} | {ps} | {mom} | {strats} |")

    lines += ["", "## Per-Row Advice", ""]
    for _, r in view.iterrows():
        d = r.to_dict()
        advice = d.get("advice", "") or "No high-conviction setup."
        lines.append(f"- **{d.get('symbol','')}**: {advice}")

    lines += [
        "",
        "## Strategy Key",
        "- **A** = Earnings IV Crush (IV/RV ≥ 1.25) → Hold-through: long calendar; if premium selling, defined-risk only (iron condor/iron fly).",
        "- **B** = Forward Factor (best pair FF ≥ 0.2) → Long calendar spread; tag when earnings sit inside front-leg window.",
        "- **C** = Rich Skew + Momentum → Vertical spread",
        "",
    ]

    lines += [
        "",
        "## Notes",
        "- IV30 is approximated from nearest-30D ATM options available from the chain.",
        "- RV30 is annualized realized volatility from 30 daily log returns.",
        "- Use for research only (not financial advice).",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenBB Earnings IV Scanner")
    parser.add_argument("--window-days", type=int, default=14)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--min-oi", type=int, default=500)
    parser.add_argument("--min-vol", type=int, default=100)
    parser.add_argument("--out-csv", default="outputs/openbb_earnings_iv_scan.csv")
    parser.add_argument("--out-md", default="outputs/openbb_earnings_iv_scan.md")
    parser.add_argument("--tracker-jsonl", default="outputs/backtest_tracker.jsonl")
    parser.add_argument("--debug", action="store_true", help="Print scan diagnostics (counts and skip reasons)")
    parser.add_argument("--capital", type=float, default=None)
    parser.add_argument("--default-alloc", type=float, default=0.04)
    args = parser.parse_args()

    df = scan(args.window_days, args.top_n, args.min_oi, args.min_vol, debug=args.debug, capital=args.capital, default_alloc=args.default_alloc)

    out_csv = Path(args.out_csv)
    out_md = Path(args.out_md)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(out_csv, index=False)
    md = to_markdown(df, args)
    out_md.write_text(md, encoding="utf-8")

    append_tracker(df, Path(args.tracker_jsonl), args)

    print(f"Scan done. rows={len(df)}")
    print(f"CSV: {out_csv}")
    print(f"MD:  {out_md}")
    print(f"Tracker append: {args.tracker_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
