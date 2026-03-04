import unittest
from unittest.mock import patch, Mock

from alerts import format_trade_alert, send_discord_webhook


class DiscordAlertTests(unittest.TestCase):
    def test_format_trade_alert(self):
        row = {
            "symbol": "SPY",
            "strategies": "A,B",
            "iv_rv_ratio": 1.5,
            "ff_best": 0.4,
            "earnings_date": "2026-03-10",
            "suggested_allocation_pct": 0.05,
        }
        text = format_trade_alert(row)
        self.assertIn("SPY", text)
        self.assertIn("IV/RV", text)
        self.assertIn("allocation", text.lower())

    @patch("alerts.requests.post")
    def test_send_discord_webhook(self, mpost):
        mpost.return_value = Mock(status_code=204)
        ok = send_discord_webhook("hello", "https://discord.test/webhook")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
