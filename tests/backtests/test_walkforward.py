import datetime as dt
import unittest

from backtests.run_walkforward import build_walkforward_windows


class WalkForwardSplitTests(unittest.TestCase):
    def test_window_generation(self):
        windows = build_walkforward_windows(
            start=dt.date(2018, 1, 1),
            end=dt.date(2024, 12, 31),
            train_years=2,
            test_years=2,
            step_years=1,
        )
        self.assertGreaterEqual(len(windows), 2)
        first = windows[0]
        self.assertEqual(first['train_start'], dt.date(2018, 1, 1))
        self.assertEqual(first['train_end'], dt.date(2019, 12, 31))


if __name__ == '__main__':
    unittest.main()
