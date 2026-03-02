import datetime as dt
import unittest

from backtests.providers.lambdaclass_data_v1 import LambdaClassDataV1Provider
from backtests.providers.registry import resolve_provider


class LambdaClassProviderTests(unittest.TestCase):
    def test_mapping_and_methods(self):
        provider = LambdaClassDataV1Provider(root_dir="tests/fixtures/lambdaclass_data_v1")
        px = provider.get_underlying_prices("MOCK", dt.date(2020, 1, 1), dt.date(2020, 1, 10))
        self.assertEqual(len(px), 3)
        self.assertIn("close", px.columns)

        chain = provider.get_options_chain("MOCK", dt.date(2020, 1, 3))
        self.assertEqual(len(chain), 2)
        self.assertIn("option_type", chain.columns)

        cal = provider.get_earnings_calendar(dt.date(2020, 1, 1), dt.date(2020, 12, 31))
        self.assertEqual(len(cal), 1)

    def test_registry_resolves_lambdaclass(self):
        p = resolve_provider("lambdaclass", root_dir="tests/fixtures/lambdaclass_data_v1")
        self.assertIsInstance(p, LambdaClassDataV1Provider)


if __name__ == '__main__':
    unittest.main()
