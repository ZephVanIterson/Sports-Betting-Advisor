import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import requests

import main


class OddsTests(unittest.TestCase):
    def setUp(self):
        self.odds = pd.DataFrame(
            [
                {
                    "game_id": "game-1",
                    "home_team": "Home",
                    "away_team": "Away",
                    "bookmaker": "book-a",
                    "outcome": "Home",
                    "american_odds": 110,
                    "decimal_odds": 2.10,
                    "implied_prob": 1 / 2.10,
                },
                {
                    "game_id": "game-1",
                    "home_team": "Home",
                    "away_team": "Away",
                    "bookmaker": "book-b",
                    "outcome": "Home",
                    "american_odds": 120,
                    "decimal_odds": 2.20,
                    "implied_prob": 1 / 2.20,
                },
                {
                    "game_id": "game-1",
                    "home_team": "Home",
                    "away_team": "Away",
                    "bookmaker": "book-a",
                    "outcome": "Away",
                    "american_odds": -105,
                    "decimal_odds": 1.95,
                    "implied_prob": 1 / 1.95,
                },
                {
                    "game_id": "game-1",
                    "home_team": "Home",
                    "away_team": "Away",
                    "bookmaker": "book-b",
                    "outcome": "Away",
                    "american_odds": 105,
                    "decimal_odds": 2.05,
                    "implied_prob": 1 / 2.05,
                },
            ]
        )

    def test_better_odds_are_always_formatted_strings(self):
        results = main.find_better_than_average_odds(self.odds)
        self.assertTrue(all(isinstance(value, str) for value in results["american_odds"]))
        self.assertTrue(all(value.startswith(("+", "-")) for value in results["american_odds"]))

    def test_arbitrage_margin_uses_best_decimal_prices(self):
        results = main.compare_best_odds(self.odds)
        expected = (1 - ((1 / 2.20) + (1 / 2.05))) * 100
        self.assertAlmostEqual(
            results.iloc[0]["arbitrage_margin_percent"], round(expected, 2)
        )

    def test_request_errors_do_not_expose_the_api_key(self):
        secret = "never-print-this-secret"
        error = requests.RequestException(f"failed URL containing {secret}")
        with patch.object(main, "API_KEY", secret), patch.object(
            main.requests, "get", side_effect=error
        ):
            with self.assertRaises(RuntimeError) as context:
                main.access_api("nhl")
        self.assertNotIn(secret, str(context.exception))

    def test_fetch_failure_does_not_replace_existing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web_data = root / "static" / "data"
            web_data.mkdir(parents=True)
            existing = web_data / "nhl_results.json"
            existing.write_text('[{"existing":true}]', encoding="utf-8")

            with patch.object(main, "WEB_DATA_DIR", web_data), patch.object(
                main, "SAVED_ODDS_DIR", root / "saved_odds"
            ), patch.object(main, "process_sport", side_effect=RuntimeError("API failed")):
                with self.assertRaises(RuntimeError):
                    main.update_all_sports()

            self.assertEqual(existing.read_text(encoding="utf-8"), '[{"existing":true}]')


if __name__ == "__main__":
    unittest.main()
