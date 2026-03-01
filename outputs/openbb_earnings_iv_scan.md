# OpenBB Earnings IV Scanner Report

- Generated: 2026-03-01 07:59 UTC
- Agent: Devin
- Universe: S&P 500 (fallback list if unavailable)
- Earnings window: next 45 days
- Filters: min OI=0, min Volume=0
- Ranking: IV30/RV30 proxy (desc), then IV30 proxy

## Top Candidates

| Symbol | Earnings | Spot | IV/RV | FF | Skew | Mom | Strategies |
|--------|----------|------|-------|-----|------|-----|------------|
| JD | 2026-03-13 | 26.53 | 1.96 | 0.09 | 0.92 | BEAR | A |
| NKE | 2026-03-20 | 62.18 | 1.65 | 0.76 | 0.97 | NEUT | A,B |
| FDX | 2026-03-18 | 387.00 | 1.58 | 0.38 | 1.02 | BULL | A,B |
| AVGO | 2026-03-06 | 319.55 | 1.52 | 0.21 | 1.02 | BEAR | A,B |
| COST | 2026-03-06 | 1010.79 | 1.40 | 0.30 | 0.97 | BULL | A,B |
| ADBE | 2026-03-12 | 262.41 | 1.39 | 0.23 | 1.00 | BEAR | A,B |
| KR | 2026-03-06 | 68.24 | 1.29 | 0.47 | 0.98 | BULL | A,B |
| DOCU | 2026-03-13 | 45.07 | 1.26 | 0.19 | 1.00 | BEAR | A |
| ORCL | 2026-03-10 | 145.40 | 1.26 | 0.26 | 1.02 | BEAR | A,B |

## Strategy Key
- **A** = Earnings IV Crush (IV/RV ≥ 1.25) → Sell straddle/iron condor
- **B** = Forward Factor (FF ≥ 0.2) → Long calendar spread
- **C** = Rich Skew + Momentum → Vertical spread


## Notes
- IV30 is approximated from nearest-30D ATM options available from the chain.
- RV30 is annualized realized volatility from 30 daily log returns.
- Use for research only (not financial advice).