import unittest
import json
import tempfile
from scanner.config import load_config


class TestConfig(unittest.TestCase):
    def test_defaults_loaded(self):
        cfg = load_config("nonexistent.json")
        self.assertEqual(cfg["strategy_b"]["ff_strong_threshold"], 0.20)
        self.assertEqual(cfg["hard_filters"]["min_price"], 10.0)

    def test_override_merges(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"strategy_b": {"ff_strong_threshold": 0.30}}, f)
            f.flush()
            cfg = load_config(f.name)
        self.assertEqual(cfg["strategy_b"]["ff_strong_threshold"], 0.30)
        self.assertEqual(cfg["hard_filters"]["min_price"], 10.0)

    def test_forward_iv_not_nan(self):
        """forward_iv must not be NaN when valid IVs are available."""
        import datetime as dt
        import math
        import pandas as pd
        from scanner.forward_factor import compute_forward_factor

        today = dt.date(2024, 1, 15)
        chain = pd.DataFrame({
            "expiration": [today + dt.timedelta(days=30)] * 4 + [today + dt.timedelta(days=60)] * 4,
            "strike": [100, 100, 105, 105] * 2,
            "option_type": ["call", "put"] * 4,
            "implied_volatility": [0.25, 0.25, 0.26, 0.26, 0.22, 0.22, 0.23, 0.23],
            "bid": [3.0, 2.5, 2.0, 3.5, 4.0, 3.0, 3.0, 4.0],
            "ask": [3.2, 2.7, 2.2, 3.7, 4.2, 3.2, 3.2, 4.2],
            "volume": [100] * 8,
            "open_interest": [500] * 8,
        })
        chain["expiration"] = pd.to_datetime(chain["expiration"]).dt.date
        result = compute_forward_factor(chain, spot=102.0, as_of_date=today)
        self.assertFalse(math.isnan(result["forward_iv"]),
                         f"forward_iv should not be NaN, got {result['forward_iv']}")
