import datetime as dt
import unittest

from backtests.run_walkforward import build_walkforward_windows


class TestWalkforwardOptimize(unittest.TestCase):
    def test_windows_have_train_and_test(self):
        windows = build_walkforward_windows(
            dt.date(2018, 1, 1),
            dt.date(2024, 12, 31),
            train_years=2,
            test_years=2,
            step_years=1,
        )
        self.assertGreater(len(windows), 0)
        for w in windows:
            self.assertIn("train_start", w)
            self.assertIn("test_start", w)
            self.assertLess(w["train_end"], w["test_start"])

    def test_zero_train_returns_single_window(self):
        windows = build_walkforward_windows(
            dt.date(2020, 1, 1),
            dt.date(2024, 12, 31),
            train_years=0,
            test_years=4,
        )
        self.assertEqual(len(windows), 1)


if __name__ == "__main__":
    unittest.main()
