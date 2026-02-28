# Weekly Progress Log — Options Machine

## 2026-W09
- Bootstrapped OpenBB earnings IV scanner script.
- Added outputs: CSV report, Markdown report, JSONL backtest tracker.
- Added debug diagnostics for universe/earnings/skip reasons/exception samples.
- Switched key data calls toward yfinance provider to reduce FMP quota blockage.
- Documented setup and run commands.

## Next Week Plan
- Add provider-mode flag (`auto|fmp|yahoo`) and explicit fallback routing.
- Add Telegram alert formatter for top watchlist names.
- Add cron runner + daily/weekly report job.
- Add forward-testing watchlist state tracker.
