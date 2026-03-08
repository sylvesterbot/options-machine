import json
import tempfile
import unittest
from pathlib import Path

from scanner.config import load_config


class ScannerConfigTests(unittest.TestCase):
    def test_defaults_when_missing(self):
        cfg = load_config('/tmp/nonexistent_scanner_config.json')
        self.assertIn('strategy_b', cfg)
        self.assertIn('hard_filters', cfg)

    def test_json_override_merge(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'scanner_config.json'
            p.write_text(json.dumps({'strategy_b': {'ff_strong_threshold': 0.25}, 'hard_filters': {'min_open_interest': 100}}), encoding='utf-8')
            cfg = load_config(str(p))
            self.assertEqual(cfg['strategy_b']['ff_strong_threshold'], 0.25)
            self.assertIn('ff_moderate_threshold', cfg['strategy_b'])
            self.assertEqual(cfg['hard_filters']['min_open_interest'], 100)
            self.assertIn('min_price', cfg['hard_filters'])


if __name__ == '__main__':
    unittest.main()
