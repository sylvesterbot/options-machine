import unittest

from scanner.greeks import bsm_price, bsm_greeks


class GreeksTests(unittest.TestCase):
    def test_bsm_reference_values(self):
        S, K, T, r, sigma = 100.0, 100.0, 0.25, 0.05, 0.2
        call = bsm_price(S, K, T, r, sigma, "call")
        put = bsm_price(S, K, T, r, sigma, "put")
        self.assertAlmostEqual(call, 4.615, places=2)
        self.assertAlmostEqual(put, 3.373, places=2)

        g = bsm_greeks(S, K, T, r, sigma, "call")
        self.assertAlmostEqual(g["delta"], 0.57, places=2)
        self.assertAlmostEqual(g["gamma"], 0.039, places=2)


if __name__ == "__main__":
    unittest.main()
