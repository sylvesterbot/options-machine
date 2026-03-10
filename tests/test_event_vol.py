import math
import unittest

from scanner.event_vol import decompose_event_vol


class TestEventVol(unittest.TestCase):
    def test_basic_decomposition(self):
        result = decompose_event_vol(iv30=0.40, rv30=0.25, dte=5)
        self.assertFalse(math.isnan(result["event_vol"]))
        self.assertGreater(result["event_vol"], 0)

    def test_event_vol_higher_when_iv_much_higher_than_rv(self):
        low = decompose_event_vol(iv30=0.30, rv30=0.25, dte=5)
        high = decompose_event_vol(iv30=0.50, rv30=0.25, dte=5)
        self.assertGreater(high["event_vol"], low["event_vol"])

    def test_nan_inputs(self):
        result = decompose_event_vol(float("nan"), 0.25, 5)
        self.assertTrue(math.isnan(result["event_vol"]))

    def test_zero_dte(self):
        result = decompose_event_vol(0.40, 0.25, 0)
        self.assertTrue(math.isnan(result["event_vol"]))

    def test_event_premium_positive_when_iv_exceeds_rv(self):
        result = decompose_event_vol(iv30=0.45, rv30=0.20, dte=3)
        self.assertGreater(result["event_premium_pct"], 0)


if __name__ == "__main__":
    unittest.main()
