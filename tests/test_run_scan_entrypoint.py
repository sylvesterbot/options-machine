import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import run_scan


class RunScanEntrypointTests(unittest.TestCase):
    def test_run_scan_pipeline_writes_outputs_tracker_watchlist_and_alert(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "symbol": "AAPL",
                    "earnings_date": "2026-03-20",
                    "spot": 200.0,
                    "iv30_proxy": 0.4,
                    "rv30": 0.3,
                    "iv_rv_ratio": 1.33,
                    "expected_move_pct": 0.05,
                    "option_volume": 1000,
                    "open_interest": 2000,
                    "avg_hist_move": 0.04,
                    "max_hist_move": 0.06,
                    "num_earnings": 5,
                    "move_ratio": 1.25,
                    "forward_factor": 0.2,
                    "ff_signal": "STRONG",
                    "put_skew": 0.1,
                    "call_skew": 0.0,
                    "skew_signal": "NONE",
                    "momentum_pct": 0.01,
                    "momentum_dir": "BULLISH",
                    "strategies": "A",
                    "suggested_allocation_pct": 0.04,
                    "suggested_allocation_usd": 4000.0,
                }
            ]
        )

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            args = Namespace(
                window_days=45,
                top_n=25,
                min_oi=0,
                min_vol=0,
                debug=True,
                alert=True,
                out_csv=str(base / "outputs" / "openbb_earnings_iv_scan.csv"),
                out_md=str(base / "outputs" / "openbb_earnings_iv_scan.md"),
                tracker_jsonl=str(base / "outputs" / "backtest_tracker.jsonl"),
                watchlist_jsonl=str(base / "data" / "watchlist.jsonl"),
                capital=100000.0,
                default_alloc=0.04,
                portfolio_dd=0.0,
                analyze="",
            )

            with (
                patch("run_scan.scan", return_value=df),
                patch("run_scan.format_daily_alert", return_value="ALERT") as fmt_mock,
                patch("builtins.print") as print_mock,
            ):
                run_scan.run_pipeline(args)

            self.assertTrue(Path(args.out_csv).exists())
            self.assertTrue(Path(args.out_md).exists())
            self.assertTrue(Path(args.tracker_jsonl).exists())
            self.assertTrue(Path(args.watchlist_jsonl).exists())

            md_text = Path(args.out_md).read_text(encoding="utf-8")
            self.assertIn("OpenBB Earnings IV Scanner Report", md_text)

            tracker_line = Path(args.tracker_jsonl).read_text(encoding="utf-8").strip().splitlines()[-1]
            event = json.loads(tracker_line)
            self.assertEqual(event["result_count"], 1)

            fmt_mock.assert_called_once()
            print_mock.assert_any_call("ALERT")


    def test_analyze_mode_uses_single_ticker_path(self) -> None:
        df = pd.DataFrame([{"symbol": "SPY", "strategies": "", "earnings_date": "2026-03-20"}])
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            args = Namespace(
                window_days=14,
                top_n=25,
                min_oi=0,
                min_vol=0,
                debug=True,
                alert=False,
                out_csv=str(base / "outputs" / "scan.csv"),
                out_md=str(base / "outputs" / "scan.md"),
                tracker_jsonl=str(base / "outputs" / "tracker.jsonl"),
                watchlist_jsonl=str(base / "data" / "watchlist.jsonl"),
                capital=None,
                default_alloc=0.04,
                portfolio_dd=0.0,
                analyze="SPY",
            )
            with patch("run_scan.analyze_single_ticker", return_value=df) as a_mock, patch("run_scan.scan") as scan_mock:
                run_scan.run_pipeline(args)
            a_mock.assert_called_once()
            scan_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
