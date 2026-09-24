import datetime
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
SAVED_ODDS_DIR = BASE_DIR / "saved_odds"
WEB_DATA_DIR = BASE_DIR / "static" / "data"

load_dotenv(BASE_DIR / ".env")
API_KEY = os.getenv("API_KEY")

SPORTS_CONFIG = {
    "nhl": {
        "api_key": "icehockey_nhl",
        "name": "NHL",
        "season_months": [10, 11, 12, 1, 2, 3, 4, 5, 6],
    },
    "nba": {
        "api_key": "basketball_nba",
        "name": "NBA",
        "season_months": [10, 11, 12, 1, 2, 3, 4, 5, 6],
    },
    "nfl": {
        "api_key": "americanfootball_nfl",
        "name": "NFL",
        "season_months": [9, 10, 11, 12, 1, 2],
    },
}


def get_sport_url(sport_key):
    """Return the odds endpoint without putting the secret in the URL."""
    api_sport_key = SPORTS_CONFIG[sport_key]["api_key"]
    return f"https://api.the-odds-api.com/v4/sports/{api_sport_key}/odds/"


def is_sport_in_season(sport_key):
    current_month = datetime.datetime.now().month
    return current_month in SPORTS_CONFIG[sport_key]["season_months"]


def access_api(sport_key):
    """Fetch and validate odds data for one sport."""
    if not API_KEY:
        raise RuntimeError("API_KEY is not configured")

    sport_name = SPORTS_CONFIG[sport_key]["name"]
    try:
        response = requests.get(
            get_sport_url(sport_key),
            params={"apiKey": API_KEY, "regions": "us", "markets": "h2h"},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(exc.response, "status_code", "unavailable")
        # Do not print the exception: requests may include the API key in its URL.
        raise RuntimeError(
            f"Failed to fetch {sport_name} odds (HTTP status: {status})"
        ) from None

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"The {sport_name} API response was not valid JSON") from None

    if not isinstance(data, list):
        raise RuntimeError(f"The {sport_name} API response had an unexpected format")

    if not data:
        print(f"No {sport_name} games found (possibly off-season)")
        return pd.DataFrame()

    games = []
    try:
        for game in data:
            for bookmaker in game.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market.get("key") != "h2h":
                        continue
                    for outcome in market.get("outcomes", []):
                        decimal_odds = float(outcome["price"])
                        games.append(
                            {
                                "game_id": game["id"],
                                "sport_key": game["sport_key"],
                                "home_team": game["home_team"],
                                "away_team": game["away_team"],
                                "bookmaker": bookmaker["key"],
                                "outcome": outcome["name"],
                                "american_odds": int(
                                    round(convert_odds(decimal_odds, "decimal", "american"))
                                ),
                                "decimal_odds": decimal_odds,
                                "implied_prob": convert_odds(
                                    decimal_odds, "decimal", "implied_prob"
                                ),
                            }
                        )
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise RuntimeError(
            f"The {sport_name} API response contained invalid odds data: {type(exc).__name__}"
        ) from None

    print(f"Retrieved {len(games)} betting lines for {sport_name}")
    return pd.DataFrame(games)


def convert_odds(odds, current_format, desired_format):
    """Convert odds between American, decimal, and implied probability formats."""
    if current_format == "american":
        if odds == 0:
            raise ValueError("American odds cannot be zero")
        decimal_odds = (odds / 100) + 1 if odds > 0 else (100 / abs(odds)) + 1
    elif current_format == "decimal":
        if odds <= 1:
            raise ValueError("Decimal odds must be greater than one")
        decimal_odds = odds
    elif current_format == "implied_prob":
        if not 0 < odds < 1:
            raise ValueError("Implied probability must be between zero and one")
        decimal_odds = 1 / odds
    else:
        raise ValueError("Invalid current odds format")

    if desired_format == "american":
        if decimal_odds >= 2:
            return (decimal_odds - 1) * 100
        return -(100 / (decimal_odds - 1))
    if desired_format == "decimal":
        return decimal_odds
    if desired_format == "implied_prob":
        return 1 / decimal_odds
    raise ValueError("Invalid desired odds format")


def format_american_odds(odds):
    odds = int(round(float(odds)))
    return f"+{odds}" if odds > 0 else str(odds)


def compare_best_odds(df):
    """Return each game's best lines and their theoretical arbitrage margin."""
    if df.empty:
        return pd.DataFrame()

    results = []
    for game_id, game_data in df.groupby("game_id"):
        home_team = game_data["home_team"].iloc[0]
        away_team = game_data["away_team"].iloc[0]
        home_odds = game_data[game_data["outcome"] == home_team]
        away_odds = game_data[game_data["outcome"] == away_team]

        if home_odds.empty or away_odds.empty:
            continue

        best_home = home_odds.loc[home_odds["decimal_odds"].idxmax()]
        best_away = away_odds.loc[away_odds["decimal_odds"].idxmax()]
        average_home_probability = home_odds["implied_prob"].mean()
        average_away_probability = away_odds["implied_prob"].mean()
        arbitrage_margin = 1 - (
            best_home["implied_prob"] + best_away["implied_prob"]
        )

        results.append(
            {
                "game_id": game_id,
                "home_team": home_team,
                "max_home_bookmaker": best_home["bookmaker"],
                "max_home_odds": format_american_odds(best_home["american_odds"]),
                "mean_home_odds": format_american_odds(
                    convert_odds(average_home_probability, "implied_prob", "american")
                ),
                "away_team": away_team,
                "max_away_bookmaker": best_away["bookmaker"],
                "max_away_odds": format_american_odds(best_away["american_odds"]),
                "mean_away_odds": format_american_odds(
                    convert_odds(average_away_probability, "implied_prob", "american")
                ),
                "arbitrage_margin_percent": round(arbitrage_margin * 100, 2),
            }
        )

    return pd.DataFrame(
        sorted(results, key=lambda row: row["arbitrage_margin_percent"], reverse=True)
    )


def find_better_than_average_odds(df):
    """Return the single best above-average line for each game and outcome."""
    if df.empty:
        return pd.DataFrame()

    results = []
    for game_id, game_data in df.groupby("game_id"):
        for outcome, outcome_data in game_data.groupby("outcome"):
            average_probability = outcome_data["implied_prob"].mean()
            average_american_odds = convert_odds(
                average_probability, "implied_prob", "american"
            )
            better_rows = outcome_data[
                outcome_data["american_odds"] > average_american_odds
            ]
            if better_rows.empty:
                continue

            best = better_rows.loc[better_rows["decimal_odds"].idxmax()]
            results.append(
                {
                    "game_id": game_id,
                    "home_team": best["home_team"],
                    "away_team": best["away_team"],
                    "outcome": outcome,
                    "bookmaker": best["bookmaker"],
                    "american_odds": format_american_odds(best["american_odds"]),
                    "average_american_odds": format_american_odds(
                        average_american_odds
                    ),
                    "price_improvement_percent": round(
                        ((best["decimal_odds"] * average_probability) - 1) * 100,
                        2,
                    ),
                    "implied_prob": best["implied_prob"],
                    "average_implied_prob": average_probability,
                    "implied_prob_difference": average_probability
                    - best["implied_prob"],
                }
            )

    return pd.DataFrame(
        sorted(results, key=lambda row: row["implied_prob_difference"], reverse=True)
    )


def print_frame(df, sport_name, label):
    if df.empty:
        print(f"No {label.lower()} available for {sport_name}")
        return
    print(f"\n{sport_name} {label}:")
    print(df.drop(columns=["game_id"], errors="ignore").to_string(index=False))


def process_sport(sport_key):
    sport_name = SPORTS_CONFIG[sport_key]["name"]
    print(f"\nProcessing {sport_name}...")
    if not is_sport_in_season(sport_key):
        print(f"{sport_name} is currently off-season; checking for games anyway.")

    odds = access_api(sport_key)
    better_odds = find_better_than_average_odds(odds)
    results = compare_best_odds(odds)
    print_frame(better_odds, sport_name, "better odds")
    print_frame(results, sport_name, "best odds")
    return odds, better_odds, results


def atomic_json_write(dataframe, path):
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    dataframe.to_json(temporary_path, orient="records")
    os.replace(temporary_path, path)


def atomic_csv_write(dataframe, path):
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    dataframe.to_csv(temporary_path, index=False)
    os.replace(temporary_path, path)


def atomic_text_write(text, path):
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(text, encoding="utf-8")
    os.replace(temporary_path, path)


def update_all_sports():
    """Fetch every sport first, then publish only after every request succeeds."""
    print("Starting multi-sport odds update...")
    processed = {}
    for sport_key in SPORTS_CONFIG:
        processed[sport_key] = process_sport(sport_key)

    SAVED_ODDS_DIR.mkdir(exist_ok=True)
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    sports_with_data = []

    for sport_key, (odds, better_odds, results) in processed.items():
        if not odds.empty:
            atomic_csv_write(odds, SAVED_ODDS_DIR / f"{sport_key}_odds.csv")
            sports_with_data.append(SPORTS_CONFIG[sport_key]["name"])
        atomic_json_write(
            better_odds, WEB_DATA_DIR / f"{sport_key}_better_odds.json"
        )
        atomic_json_write(results, WEB_DATA_DIR / f"{sport_key}_results.json")

    current_time = (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    atomic_text_write(current_time, WEB_DATA_DIR / "last_updated.txt")

    print(f"\nUpdate completed at {current_time}")
    print(
        f"Sports with data: {', '.join(sports_with_data)}"
        if sports_with_data
        else "No sports currently have games available"
    )


def main():
    try:
        update_all_sports()
    except Exception as exc:
        print(f"Update failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
