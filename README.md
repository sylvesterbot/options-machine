# Options Machine

Automated options scanner that identifies overpriced implied volatility using three quantitative strategies.

## Features

- **Strategy A — Earnings IV Crush:** Finds setups where implied volatility is rich versus realized volatility before earnings.
- **Strategy B — Forward Factor Calendar:** Detects term-structure dislocations and flags potential long calendar opportunities.
- **Strategy C — Skew Verticals:** Scores skew richness in OTM options with momentum confirmation for directional spreads.
- **Historical move comparison:** Compares current expected move to recent post-earnings realized moves.
- **Forward testing suite:** Logs scan candidates and supports post-earnings outcome tracking.

## How It Works

For an upcoming earnings window, the scanner:

1. Builds a symbol universe and fetches upcoming earnings dates.
2. Computes **IV/RV** (implied vs realized volatility) around ~30D tenor.
3. Computes **Forward Factor** from front/back expiry variance term structure.
4. Computes **skew metrics** and combines with momentum filters.
5. Computes **historical earnings move stats** and a **move ratio** versus current expected move.
6. Writes outputs (CSV + Markdown + tracker), watchlist entries, and optional alert text.

## Installation

```bash
git clone https://github.com/sylvesterbot/options-machine.git
cd options-machine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Required environment variable:

```bash
export FMP_API_KEY="your_key_here"
```

## Usage

Daily scan (primary entrypoint):

```bash
python run_scan.py --window-days 14 --debug --alert
```

Outcome reconciliation (post-earnings):

```bash
python run_outcome_check.py --debug
```

Weekly rollup report:

```bash
python run_weekly_report.py
```

## Output Example

Generated Markdown report includes a table like:

| Symbol | Earnings | Spot | IV/RV | MvRatio | FF | Skew | Mom | Strategies |
|--------|----------|------|-------|---------|----|------|-----|------------|
| NKE    | 2026-03-20 | 79.12 | 1.65 | 1.24 | 0.76 | 1.11 | BULL | A,B |

## Project Structure

- `run_scan.py` — unified entry point (scan + outputs + tracker + watchlist + alert)
- `openbb_earnings_iv_scanner.py` — core scan logic and report/tracker helpers
- `scanner/forward_factor.py` — Strategy B logic
- `scanner/skew_score.py` — Strategy C skew scoring
- `scanner/momentum.py` — momentum filter
- `scanner/historical_moves.py` — historical earnings move comparison
- `watchlist.py` — forward-testing watchlist append
- `alerts.py` — alert text formatting
- `run_outcome_check.py` — post-earnings outcome checks
- `run_weekly_report.py` — weekly rollup reporting
- `tests/` — unit tests
- `docs/scanner-spec.md` — scanner design/spec notes

## Strategy Notes

### A) Earnings IV Crush
Compares ATM implied volatility to 30-day realized volatility. Elevated IV/RV may indicate overpriced premium before earnings, suitable for premium-selling structures under disciplined risk management.

### B) Forward Factor Calendar
Backs out forward variance from front/back maturities and compares it with front IV. A high forward-factor signal indicates front-month richness relative to the curve, often supportive of calendar structures.

### C) Skew Verticals
Measures OTM put/call implied vol relative to ATM and combines with momentum direction. Rich skew plus directional confirmation can support defined-risk vertical spread ideas.

## Academic References

- Carr, P., & Wu, L. (2009). *Variance Risk Premiums*. **Review of Financial Studies**.
- Goyal, A., & Saretto, A. (2009). *Cross-Section of Option Returns and Volatility*. **Journal of Financial Economics**.
- Gao, P., Xing, Y., & Zhang, L. (2018). *Anticipating Uncertainty: Straddle Around Earnings Announcements*. **Journal of Financial Economics**.
- Bollen, N. P. B., & Whaley, R. E. (2004). *Does Net Buying Pressure Affect the Shape of Implied Volatility Functions?* **Journal of Finance**.



## Backtest Providers (Plugin Architecture)

Walk-forward backtests now use a pluggable provider registry.

Supported provider names:
- `lambdaclass` (implemented)
- `mock` (implemented)
- `polygon` (stub)
- `thetadata` (stub)
- `eodhd` (stub)

### Lambdaclass data-v1 setup

Use one local folder containing extracted CSVs. In this repo, both of these roots are commonly used:
- `data/lambdaclass-data-v1`
- `data/lambdaclass_data_v1/extracted_spy_2020_2024`

Example:

```bash
mkdir -p data/lambdaclass_data_v1/extracted_spy_2020_2024
# copy extracted CSVs into that folder
```

Expected files under `--provider-root`:
- `underlying_prices.csv` (required)
- `options_eod.csv` (required)
- `earnings_calendar.csv` (optional)

Run walk-forward with provider=lambdaclass:

```bash
python backtests/run_walkforward.py \
  --provider lambdaclass \
  --provider-root data/lambdaclass_data_v1/extracted_spy_2020_2024 \
  --start 2018-01-01 \
  --end 2024-12-31 \
  --out outputs/walkforward_trades.csv
```



### Strategy B backtest (ETF-friendly, no earnings dependency)

For SPY/IWM/QQQ style datasets, run Strategy B directly:

```bash
python backtests/run_walkforward.py   --provider lambdaclass   --provider-root data/lambdaclass-data-v1   --strategy B   --symbols SPY,IWM,QQQ   --start 2020-01-01   --end 2024-12-31   --ff-threshold 0.2   --holding-days 10   --exit-mode fixed   --out outputs/walkforward_strategy_b.csv
```

Note: A1 earnings strategy may produce zero trades for ETFs due to no earnings events.

### Known dataset limitations

- Coverage and date range depend on the extracted data-v1 bundle.
- Earnings calendar may be partial or missing (adapter returns empty when absent).
- Source schemas can differ; adapter applies strict normalization and will raise friendly errors if required columns are missing.

## License

MIT

## Disclaimer

This project is for research and educational purposes only and is **not financial advice**. Trading options involves substantial risk.
