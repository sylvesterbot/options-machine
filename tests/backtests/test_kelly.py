import unittest

from backtests.kelly import compute_kelly_fraction


class KellyTests(unittest.TestCase):
    def test_min_sample_uses_default(self):
        alloc = compute_kelly_fraction([0.1] * 10)
        self.assertEqual(alloc, 0.04)

    def test_clamp_range(self):
        returns = [0.2, 0.25, 0.15, 0.18, -0.02] * 20
        alloc = compute_kelly_fraction(returns)
        self.assertGreaterEqual(alloc, 0.02)
        self.assertLessEqual(alloc, 0.08)


if __name__ == '__main__':
    unittest.main()
