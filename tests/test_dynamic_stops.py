import unittest

from scanner.regime import classify_regime


class TestDynamicStops(unittest.TestCase):
    def test_calm_has_tighter_stops(self):
        r = classify_regime(12.0)
        self.assertIn("stop_loss_multiplier", r)
        self.assertLess(r["stop_loss_multiplier"], 1.0)

    def test_normal_has_standard_stops(self):
        r = classify_regime(20.0)
        self.assertEqual(r["stop_loss_multiplier"], 1.0)

    def test_elevated_has_wider_stops(self):
        r = classify_regime(28.0)
        self.assertGreater(r["stop_loss_multiplier"], 1.0)

    def test_crisis_halts(self):
        r = classify_regime(40.0)
        self.assertEqual(r["stop_loss_multiplier"], 0.0)

    def test_stop_multiplier_scales_correctly(self):
        calm = classify_regime(12.0)
        elev = classify_regime(28.0)
        base_stop = -0.50
        self.assertAlmostEqual(base_stop * calm["stop_loss_multiplier"], -0.40)
        self.assertAlmostEqual(base_stop * elev["stop_loss_multiplier"], -0.65)


if __name__ == "__main__":
    unittest.main()
