import os
import tempfile
import unittest
from pathlib import Path

import scanner.trade_journal as tj
from scanner.trade_journal import JOURNAL_COLUMNS, compute_hit_rate, log_signal


class TestTradeJournal(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.journal_path = Path(self.tmpdir) / "trade_journal.csv"
        self._orig = tj.JOURNAL_PATH
        tj.JOURNAL_PATH = self.journal_path

    def tearDown(self):
        tj.JOURNAL_PATH = self._orig
        if self.journal_path.exists():
            os.remove(self.journal_path)
        os.rmdir(self.tmpdir)

    def test_log_signal_creates_file(self):
        log_signal({"symbol": "NVDA", "strategies": "A,B", "tier_label": "TIER_1"})
        self.assertTrue(self.journal_path.exists())
        with open(self.journal_path, encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)

    def test_compute_hit_rate_empty(self):
        result = compute_hit_rate([])
        self.assertEqual(result["total_signals"], 0)
        self.assertEqual(result["hit_rate"], 0.0)

    def test_compute_hit_rate_with_data(self):
        entries = [
            {"realized_pnl_pct": "5.0", "symbol": "A"},
            {"realized_pnl_pct": "-3.0", "symbol": "B"},
            {"realized_pnl_pct": "2.0", "symbol": "C"},
        ]
        result = compute_hit_rate(entries)
        self.assertEqual(result["completed"], 3)
        self.assertEqual(result["win_count"], 2)
        self.assertEqual(result["loss_count"], 1)
        self.assertAlmostEqual(result["hit_rate"], 2 / 3)

    def test_journal_columns_defined(self):
        self.assertIn("symbol", JOURNAL_COLUMNS)
        self.assertIn("strategies", JOURNAL_COLUMNS)
        self.assertIn("realized_pnl_pct", JOURNAL_COLUMNS)
        self.assertIn("exit_reason", JOURNAL_COLUMNS)


if __name__ == "__main__":
    unittest.main()
