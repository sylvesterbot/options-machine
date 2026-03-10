# Options Machine

A research-first options signal and backtesting platform focused on earnings-volatility dislocations, term-structure anomalies, and skew-rich setups.

> **Status:** Phase 6 integrated on `main` (actionable alerts, profit-target exits, regime filter, event-vol decomposition, walk-forward optimization, integration tests).

---

## Table of Contents

1. [What this project does](#what-this-project-does)
2. [System architecture](#system-architecture)
3. [Strategies](#strategies)
4. [Phase 6 highlights](#phase-6-highlights)
5. [Repository structure](#repository-structure)
6. [Installation](#installation)
7. [Configuration](#configuration)
8. [Running scans and reports](#running-scans-and-reports)
9. [Backtesting](#backtesting)
10. [API + Dashboard](#api--dashboard)
11. [Testing and quality gates](#testing-and-quality-gates)
12. [Risk controls and disclaimers](#risk-controls-and-disclaimers)
13. [Troubleshooting](#troubleshooting)
14. [Roadmap](#roadmap)
15. [Contribution workflow](#contribution-workflow)

---

## What this project does

Options Machine scans an earnings-focused universe, computes quantitative volatility/skew features, ranks candidates, generates actionable alerts, and supports walk-forward + Monte Carlo analysis.

Core outcomes:
- **Daily candidate scan** (CSV + Markdown + tracker/watchlist)
- **Actionable trade alerts** (WHY / ACTION / SIZING)
- **Backtests** for Strategy B and Strategy C
- **Walk-forward validation** with optional train-window optimization
- **Dashboard/API** for review and operations

---

## System architecture

### 1) Data + scan layer
- `openbb_earnings_iv_scanner.py`
  - universe + earnings retrieval
  - options chain normalization
  - feature engineering (IV/RV, forward factor, skew, momentum, historical move stats)
  - tiering and ranking

### 2) Strategy analytics layer
- `scanner/forward_factor.py` (Strategy B signal)
- `scanner/skew_score.py` (Strategy C signal)
- `scanner/historical_moves.py` (implied vs realized earnings-move context)
- `scanner/signal_history.py` (z-scores / percentiles)
- `scanner/regime.py` (VIX regime filter)
- `scanner/event_vol.py` (event-vol decomposition)
- `scanner/iron_fly.py` (defined-risk structure helper for Strategy A messaging)

### 3) Alerting + reporting layer
- `alerts.py`
  - concise detailed alerts
  - tier-grouped daily digest
  - optional webhook support

### 4) Backtest layer
- `backtests/strategy_b.py` (calendar spread simulator)
- `backtests/strategy_c.py` (put-credit spread simulator)
- `backtests/run_walkforward.py` (window generation + optional train optimization)
- `backtests/monte_carlo.py` (distribution stress testing)

### 5) UI / service layer
- `dashboard.py` (Streamlit operations dashboard)
- `api_server.py` (FastAPI backend endpoints)

---

## Strategies

## Strategy A — Earnings IV Crush
**Signal intent:** implied vol elevated vs realized vol pre-earnings (IV/RV context).  
**Trade intent (alerts):** defined-risk structures (Iron Condor / Iron Fly) with sizing guidance.  
**Backtest status:** **deferred** (historical options data dependency not yet solved in this repo).

## Strategy B — Forward Factor Calendar
**Signal:** term-structure dislocation (front/back variance relationship) + quality filters.  
**Trade form:** ATM call calendar (sell front, buy back).  
**Backtest:** supported via `backtests/strategy_b.py`.

## Strategy C — Rich Skew Vertical
**Signal:** skew richness + momentum confirmation.  
**Trade form:** defined-risk put credit spread.  
**Backtest:** supported via `backtests/strategy_c.py`.

---

## Phase 6 highlights

Phase 6 brought the system from “good scanner” to stronger production-grade research tooling:

1. **Alert overhaul**
   - Detailed WHY / ACTION / SIZING sections
   - Strategy-specific message generation
   - Tier-grouped daily alert digest

2. **Profit-target exits in simulators**
   - Strategy C: `target_profit_pct` with `exit_reason`
   - Strategy B: optional `target_profit_pct` with `exit_reason`

3. **VIX regime awareness**
   - `CALM`, `NORMAL`, `ELEVATED`, `CRISIS`
   - allocation multiplier applied in scanner output
   - crisis regime can halt new-signal scan output

4. **Event-vol decomposition**
   - separates implied volatility into ambient vs event component
   - stores `event_vol` and `event_premium_pct`

5. **Walk-forward improvement**
   - train-window parameter optimization (`--optimize`) before test-window simulation

6. **Execution improvements**
   - Strategy C configurable `spread_width`
   - Strategy B delta-aware strike selection fallback logic

7. **Integration wiring/tests**
   - event premium in alerts
   - regime context in daily alert header
   - integration tests for full Phase 6 pipeline

---

## Repository structure

```text
options-machine/
├── openbb_earnings_iv_scanner.py
├── run_scan.py
├── run_outcome_check.py
├── run_weekly_report.py
├── alerts.py
├── api_server.py
├── dashboard.py
├── scanner/
│   ├── config.py
│   ├── forward_factor.py
│   ├── skew_score.py
│   ├── momentum.py
│   ├── historical_moves.py
│   ├── signal_history.py
│   ├── regime.py
│   ├── event_vol.py
│   └── iron_fly.py
├── backtests/
│   ├── strategy_b.py
│   ├── strategy_c.py
│   ├── run_walkforward.py
│   ├── monte_carlo.py
│   └── providers/
├── tests/
├── scanner_config.json
└── outputs/
```

---

## Installation

### Prereqs
- Python 3.11+ recommended
- Git
- API/data credentials as needed by your configured data path

### Setup
```bash
git clone https://github.com/sylvesterbot/options-machine.git
cd options-machine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Environment example:
```bash
export FMP_API_KEY="your_key_here"
```

---

## Configuration

Primary runtime config:
- `scanner_config.json`

Typical sections:
- `strategy_a` thresholds (IV/RV etc.)
- `strategy_b` forward-factor thresholds
- `strategy_c` skew thresholds
- `hard_filters` liquidity/price constraints
- `tiering` pass/fail/tier assignment thresholds

Principle: prefer config values over hardcoded constants.

---

## Running scans and reports

## Daily scan
```bash
python run_scan.py --window-days 14 --debug --alert
```

## Single-ticker analyze mode
```bash
python run_scan.py --analyze --ticker SPY
```

## Outcome reconciliation
```bash
python run_outcome_check.py --debug
```

## Weekly report
```bash
python run_weekly_report.py
```

Outputs typically include:
- `outputs/openbb_earnings_iv_scan.csv`
- markdown summaries
- signal history / watchlist updates

---

## Backtesting

## Walk-forward (Strategy B)
```bash
python backtests/run_walkforward.py \
  --provider lambdaclass \
  --provider-root data/lambdaclass_data_v1/extracted_spy_2020_2024 \
  --strategy B \
  --symbols SPY \
  --start 2018-01-01 \
  --end 2024-12-31 \
  --ff-threshold 0.2 \
  --holding-days 10 \
  --exit-mode fixed \
  --optimize \
  --out outputs/walkforward_strategy_b.csv
```

## Walk-forward (Strategy C)
```bash
python backtests/run_walkforward.py \
  --provider lambdaclass \
  --provider-root data/lambdaclass_data_v1/extracted_spy_2020_2024 \
  --strategy C \
  --symbols SPY \
  --start 2018-01-01 \
  --end 2024-12-31 \
  --holding-days 10 \
  --optimize \
  --out outputs/walkforward_strategy_c.csv
```

## Monte Carlo
```bash
python -m backtests.monte_carlo --help
```

---

## API + Dashboard

## FastAPI backend
```bash
python api_server.py
```

## Streamlit dashboard
```bash
streamlit run dashboard.py --server.headless true
```

Dashboard includes:
- overview KPIs
- interactive backtest runner
- interactive Monte Carlo runner
- enhanced alerts views
- config editing tab

---

## Testing and quality gates

Run full suite:
```bash
python -m unittest discover -s tests -v
```

Phase-6 critical suites:
```bash
python -m unittest tests.test_concise_alerts -v
python -m unittest tests.backtests.test_profit_target -v
python -m unittest tests.test_regime -v
python -m unittest tests.test_event_vol -v
python -m unittest tests.backtests.test_walkforward_optimize -v
python -m unittest tests.backtests.test_spread_width -v
python -m unittest tests.test_integration_phase6 -v
```

---

## Risk controls and disclaimers

This repository is for **research and educational use**.

- Not investment advice.
- Options trading carries significant risk, including total loss.
- Backtests are model-dependent and sensitive to data quality, slippage, and assumptions.
- Strategy A backtest remains deferred pending suitable historical options dataset coverage.

Always perform independent validation before live deployment.

---

## Troubleshooting

### `pytest` missing
Some environments use `unittest` only; run:
```bash
python -m unittest discover -s tests -v
```

### Empty scan results
Check:
- earnings window
- liquidity filters in config
- data provider availability
- regime filter behavior (VIX crisis mode)

### Backtest has zero trades
Check:
- symbol/date coverage in provider-root
- threshold strictness (`ff_threshold`, skew threshold, filters)
- strategy-specific assumptions and session data quality

### Dashboard starts but shows no tables
Ensure expected output CSV/JSON files exist under `outputs/` or update sidebar paths.

---

## Roadmap

- Strategy A full backtest simulator once reliable historical options data pipeline is finalized
- richer execution-cost modeling and scenario stress tests
- expanded API endpoints and CI automation for gated validation
- provider adapters hardening (polygon/thetadata/eodhd)

---

## Contribution workflow

1. Create a feature branch.
2. Implement with tests first where possible.
3. Run full test suite locally.
4. Commit with descriptive messages.
5. Open PR with:
   - summary of behavioral changes
   - test evidence (`Ran N tests ... OK`)
   - any config/migration notes

Suggested commit style:
- `phaseX stepY: <clear outcome>`
- `fix: <specific bug + scope>`
- `docs: <exact section changed>`

---

## License

MIT
