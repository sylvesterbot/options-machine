import unittest

from backtests.kelly import (
    apply_drawdown_governor,
    compute_kelly_discrete,
    compute_kelly_empirical,
    compute_kelly_fraction,
)


class KellyV2Tests(unittest.TestCase):
    def test_discrete_and_empirical(self):
        k1 = compute_kelly_discrete(0.6, 0.1, 0.05)
        self.assertGreater(k1, 0)
        k2 = compute_kelly_empirical([0.05, -0.02, 0.03, 0.04, -0.01] * 20)
        self.assertGreaterEqual(k2, 0)

    def test_governor(self):
        self.assertLess(apply_drawdown_governor(0.08, -0.2), 0.08)

    def test_fraction_dispatch(self):
        f = compute_kelly_fraction(
            returns=[0.02, -0.01, 0.03] * 30,
            strategy="A",
            win_rate=0.55,
            avg_win=0.08,
            avg_loss=0.05,
            portfolio_dd=-0.12,
        )
        self.assertGreaterEqual(f, 0.02)
        self.assertLessEqual(f, 0.08)


if __name__ == "__main__":
    unittest.main()
