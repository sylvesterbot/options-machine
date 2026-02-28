# OpenBB Earnings IV Scanner

## What this builds
A runnable scanner that ranks earnings candidates by a volatility-premium proxy:
- Universe: S&P 500 (falls back to built-in liquid symbols if index constituents unavailable)
- Window: next 14 days by default
- Ranking: `IV30 proxy / RV30`
- Filters: minimum options liquidity (OI and volume)

## Files
- `openbb_earnings_iv_scanner.py` — scanner script
- `outputs/openbb_earnings_iv_scan.csv` — tabular output
- `outputs/openbb_earnings_iv_scan.md` — markdown report output
- `outputs/backtest_tracker.jsonl` — append-only tracker for each run

## Install
```bash
python3 -m pip install --upgrade pip
python3 -m pip install openbb pandas numpy
```

## Run (defaults)
```bash
python3 openbb_earnings_iv_scanner.py
```

## Run (custom)
```bash
python3 openbb_earnings_iv_scanner.py \
  --window-days 14 \
  --top-n 30 \
  --min-oi 1000 \
  --min-vol 200
```

## Debug mode
```bash
python3 openbb_earnings_iv_scanner.py --window-days 45 --min-oi 0 --min-vol 0 --top-n 100 --debug
```
Shows:
- universe size
- earnings rows returned
- skip counters (`price_empty`, `no_atm`, `low_liquidity`, `exception`)

## Notes
- OpenBB endpoint names can vary by version/provider; this script tries multiple endpoint paths.
- If OpenBB is unavailable/misconfigured, install/openbb-login first.
- For research only; not financial advice.
