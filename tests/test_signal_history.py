import tempfile
import unittest

from scanner.signal_history import (
    append_signals,
    get_cross_sectional_percentile,
    get_iv_percentile,
    get_ticker_zscore,
    load_history,
)


class SignalHistoryTests(unittest.TestCase):
    def test_append_and_stats(self):
        with tempfile.TemporaryDirectory() as td:
            path = f"{td}/hist.csv"
            recs = [
                {"timestamp_utc": f"2026-01-{i:02d}", "symbol": "AAPL", "iv_rv_ratio": 1.0 + i*0.01, "ff_best": 0.1 + i*0.01, "put_skew": 1.1 + (i%3)*0.01, "expected_move_pct": 0.04 + i*0.001}
                for i in range(1, 26)
            ]
            append_signals(recs, path=path)
            h = load_history(path)
            self.assertEqual(len(h), 25)
            z = get_ticker_zscore("AAPL", "ff_best", 0.3, path=path)
            self.assertTrue(z == z)
            pct = get_cross_sectional_percentile("ff_best", 0.3, path=path)
            self.assertGreaterEqual(pct, 0)
            ivp = get_iv_percentile("AAPL", 1.3, path=path)
            self.assertGreaterEqual(ivp, 0)


    def test_zscore_cold_start_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            path = f"{td}/hist.csv"
            recs = [
                {"timestamp_utc": f"2026-01-{i:02d}", "symbol": "AAPL", "iv_rv_ratio": 1.0 + i*0.01, "ff_best": 0.1 + i*0.01, "put_skew": 1.0, "expected_move_pct": 0.05}
                for i in range(1, 20)
            ]
            append_signals(recs, path=path)
            z = get_ticker_zscore("AAPL", "ff_best", 0.3, path=path)
            self.assertTrue(z != z)  # NaN before 20 obs


if __name__ == "__main__":
    unittest.main()
