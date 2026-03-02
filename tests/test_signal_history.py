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
                {"timestamp_utc": "2026-01-01", "symbol": "AAPL", "iv_rv_ratio": 1.1, "ff_best": 0.2, "put_skew": 1.2, "expected_move_pct": 0.05},
                {"timestamp_utc": "2026-01-02", "symbol": "AAPL", "iv_rv_ratio": 1.3, "ff_best": 0.3, "put_skew": 1.4, "expected_move_pct": 0.06},
                {"timestamp_utc": "2026-01-03", "symbol": "AAPL", "iv_rv_ratio": 1.5, "ff_best": 0.4, "put_skew": 1.1, "expected_move_pct": 0.07},
                {"timestamp_utc": "2026-01-04", "symbol": "AAPL", "iv_rv_ratio": 1.2, "ff_best": 0.1, "put_skew": 1.0, "expected_move_pct": 0.04},
                {"timestamp_utc": "2026-01-05", "symbol": "AAPL", "iv_rv_ratio": 1.4, "ff_best": 0.35, "put_skew": 1.3, "expected_move_pct": 0.08},
            ]
            append_signals(recs, path=path)
            h = load_history(path)
            self.assertEqual(len(h), 5)
            z = get_ticker_zscore("AAPL", "ff_best", 0.3, path=path)
            self.assertTrue(z == z)
            pct = get_cross_sectional_percentile("ff_best", 0.3, path=path)
            self.assertGreaterEqual(pct, 0)
            ivp = get_iv_percentile("AAPL", 1.3, path=path)
            self.assertGreaterEqual(ivp, 0)


if __name__ == "__main__":
    unittest.main()
