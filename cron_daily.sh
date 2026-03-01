#!/bin/bash
# Daily pre-market scan + outcome check
cd ~/projects/options-machine || exit 1
source .venv/bin/activate
export FMP_API_KEY="$(cat ~/.fmp_api_key 2>/dev/null || echo $FMP_API_KEY)"

echo "=== Daily Scan $(date -u) ==="
python run_scan.py --window-days 14 --min-oi 100 --min-vol 50 --alert 2>&1

echo "=== Outcome Check ==="
python run_outcome_check.py --debug 2>&1
