import unittest

from scanner.regime import classify_regime


class TestRegime(unittest.TestCase):
    def test_calm(self):
        r = classify_regime(12.0)
        self.assertEqual(r["regime"], "CALM")
        self.assertEqual(r["allocation_multiplier"], 1.0)

    def test_normal(self):
        r = classify_regime(18.0)
        self.assertEqual(r["regime"], "NORMAL")

    def test_elevated(self):
        r = classify_regime(28.0)
        self.assertEqual(r["regime"], "ELEVATED")
        self.assertEqual(r["allocation_multiplier"], 0.5)

    def test_crisis(self):
        r = classify_regime(40.0)
        self.assertEqual(r["regime"], "CRISIS")
        self.assertEqual(r["allocation_multiplier"], 0.0)

    def test_boundary_15(self):
        r = classify_regime(15.0)
        self.assertEqual(r["regime"], "NORMAL")

    def test_boundary_25(self):
        r = classify_regime(25.0)
        self.assertEqual(r["regime"], "ELEVATED")


if __name__ == "__main__":
    unittest.main()
