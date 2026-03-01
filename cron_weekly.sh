#!/bin/bash
# Weekly summary report
cd ~/projects/options-machine || exit 1
source .venv/bin/activate
export FMP_API_KEY="$(cat ~/.fmp_api_key 2>/dev/null || echo $FMP_API_KEY)"

echo "=== Weekly Report $(date -u) ==="
python run_weekly_report.py 2>&1
