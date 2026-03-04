import unittest

from backtests.monte_carlo import bootstrap_equity_paths, summarize_paths


class MonteCarloTests(unittest.TestCase):
    def test_bootstrap_shape_and_summary(self):
        paths = bootstrap_equity_paths([0.1, -0.05, 0.02], n_paths=200, horizon=20, seed=1)
        self.assertEqual(paths.shape, (200, 21))
        s = summarize_paths(paths)
        self.assertIn("p5", s)
        self.assertIn("prob_loss", s)
        self.assertGreaterEqual(s["p95"], s["p5"])


if __name__ == "__main__":
    unittest.main()
