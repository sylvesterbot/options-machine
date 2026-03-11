import inspect
import unittest

from backtests.strategy_b import _select_legs, simulate_strategy_b


class TestSkewedCalendar(unittest.TestCase):
    def test_strike_offset_parameter_exists(self):
        sig = inspect.signature(simulate_strategy_b)
        self.assertIn("strike_offset", sig.parameters)

    def test_select_legs_accepts_offset(self):
        sig = inspect.signature(_select_legs)
        self.assertIn("strike_offset", sig.parameters)

    def test_default_offset_is_zero(self):
        sig = inspect.signature(simulate_strategy_b)
        default = sig.parameters["strike_offset"].default
        self.assertEqual(default, 0.0)


if __name__ == "__main__":
    unittest.main()
