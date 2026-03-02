import datetime as dt
import tempfile
import unittest
from pathlib import Path

from backtests.run_walkforward import run_walkforward


class WalkforwardLambdaClassSmokeTest(unittest.TestCase):
    def test_smoke(self):
        with tempfile.TemporaryDirectory() as td:
            out = str(Path(td) / "trades.csv")
            df = run_walkforward(
                start=dt.date(2018, 1, 1),
                end=dt.date(2024, 12, 31),
                out_path=out,
                provider_name="lambdaclass",
                provider_root="tests/fixtures/lambdaclass_data_v1",
                strategy="B",
                symbols=["SPY"],
            )
            self.assertTrue(Path(out).exists())
            self.assertIsNotNone(df)


if __name__ == '__main__':
    unittest.main()
