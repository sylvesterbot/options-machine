import unittest

from scanner.config import load_config


class TestAllocationCap(unittest.TestCase):
    def test_max_ticker_allocation_in_defaults(self):
        cfg = load_config()
        hard = cfg.get("hard_filters", {})
        self.assertIn("max_ticker_allocation_pct", hard)
        self.assertLessEqual(hard["max_ticker_allocation_pct"], 0.10)

    def test_allocation_cap_value(self):
        cfg = load_config()
        cap = cfg["hard_filters"]["max_ticker_allocation_pct"]
        self.assertEqual(cap, 0.05)


if __name__ == "__main__":
    unittest.main()
