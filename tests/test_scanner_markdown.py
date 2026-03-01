import unittest
from argparse import Namespace

import pandas as pd

from openbb_earnings_iv_scanner import ScanRow, to_markdown


class ScannerMarkdownTests(unittest.TestCase):
    def test_scanrow_has_historical_move_fields(self) -> None:
        fields = ScanRow.__dataclass_fields__
        self.assertIn("avg_hist_move", fields)
        self.assertIn("max_hist_move", fields)
        self.assertIn("move_ratio", fields)

    def test_markdown_contains_move_ratio_column(self) -> None:
        args = Namespace(window_days=14, min_oi=0, min_vol=0)
        df = pd.DataFrame(
            [
                {
                    "symbol": "AAPL",
                    "earnings_date": "2026-03-20",
                    "spot": 200.0,
                    "iv30_proxy": 0.4,
                    "rv30": 0.3,
                    "iv_rv_ratio": 1.33,
                    "expected_move_pct": 0.05,
                    "option_volume": 1000,
                    "open_interest": 2000,
                    "forward_factor": 0.2,
                    "ff_signal": "LONG_CAL",
                    "put_skew": 0.1,
                    "call_skew": 0.0,
                    "skew_signal": "NONE",
                    "momentum_pct": 0.01,
                    "momentum_dir": "UP",
                    "strategies": "A",
                    "avg_hist_move": 0.04,
                    "max_hist_move": 0.06,
                    "move_ratio": 1.25,
                }
            ]
        )

        md = to_markdown(df, args)

        self.assertIn("MvRatio", md)
        self.assertIn("1.25", md)


if __name__ == "__main__":
    unittest.main()
