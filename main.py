import requests
import pandas as pd
import datetime
import os
import sys
from dotenv import load_dotenv

diff_threshold = 0.1
folder = 'saved_odds/'

load_dotenv()
API_KEY = os.getenv('API_KEY')

# API endpoints for different sports
SPORTS_CONFIG = {
    'nhl': {
        'api_key': 'icehockey_nhl',
        'name': 'NHL',
        'season_months': [10, 11, 12, 1, 2, 3, 4, 5, 6]  # Oct-June
    },
    'nba': {
        'api_key': 'basketball_nba',
        'name': 'NBA',
        'season_months': [10, 11, 12, 1, 2, 3, 4, 5, 6]  # Oct-June
    },
    'nfl': {
        'api_key': 'americanfootball_nfl',
        'name': 'NFL',
        'season_months': [9, 10, 11, 12, 1, 2]  # Sep-Feb
    }
}

def get_sport_url(sport_key):
    """Generate API URL for a specific sport"""
    api_sport_key = SPORTS_CONFIG[sport_key]['api_key']
    return f"https://api.the-odds-api.com/v4/sports/{api_sport_key}/odds/?apiKey={API_KEY}&regions=us&markets=h2h"

def is_sport_in_season(sport_key):
    """Check if a sport is currently in season"""
    current_month = datetime.datetime.now().month
    season_months = SPORTS_CONFIG[sport_key]['season_months']
    return current_month in season_months

def access_api(url, sport_name):
    """Fetch odds data from the API and return a DataFrame."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print(f"No {sport_name} games found (possibly off-season)")
            return pd.DataFrame()

        # Convert to a pandas DataFrame for easier analysis
        games = []
        for game in data:
            for bookmaker in game['bookmakers']:
                for market in bookmaker['markets']:
                    for outcome in market['outcomes']:
                        # Convert decimal odds to American odds
                        decimal_odds = outcome['price']
                        american_odds = int(round(convert_odds(decimal_odds, 'decimal', 'american'), 0))
                        implied_prob = convert_odds(decimal_odds, 'decimal', 'implied_prob')
                        games.append({
                            'game_id': game['id'],
                            'sport_key': game['sport_key'],
                            'home_team': game['home_team'],
                            'away_team': game['away_team'],
                            'bookmaker': bookmaker['key'],
                            'outcome': outcome['name'],
                            'american_odds': american_odds,
                            'decimal_odds': decimal_odds,
                            'implied_prob': implied_prob
                        })

        df = pd.DataFrame(games)
        print(f"Retrieved {len(df)} betting lines for {sport_name}")
        return df
        
    except requests.RequestException as e:
        print(f"Error fetching {sport_name} data: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error processing {sport_name} data: {e}")
        return pd.DataFrame()

def read_csv(file):
    """Read odds data from a CSV file and return a DataFrame."""
    if not os.path.exists(file):
        print(f"Error: File '{file}' not found.")
        sys.exit()
    
    df = pd.read_csv(file)
    return df

def convert_odds(odds, current_format, desired_format):
    """
    Convert odds between American, Decimal, and Implied Probability formats.

    Parameters:
        odds (float): The odds to convert.
        current_format (str): The current format of the odds ('american', 'decimal', 'implied_prob').
        desired_format (str): The desired format to convert to ('american', 'decimal', 'implied_prob').

    Returns:
        float: The converted odds.
    """
    # Convert input odds to decimal format first (for easier intermediate calculations)
    if current_format == 'american':
        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1
    elif current_format == 'decimal':
        decimal_odds = odds
    elif current_format == 'implied_prob':
        decimal_odds = 1 / odds
    else:
        raise ValueError("Invalid current_format. Use 'american', 'decimal', or 'implied_prob'.")

    # Convert decimal odds to the desired format
    if desired_format == 'american':
        if decimal_odds >= 2.0:
            return (decimal_odds - 1) * 100
        else:
            return -(100 / (decimal_odds - 1))
    elif desired_format == 'decimal':
        return decimal_odds
    elif desired_format == 'implied_prob':
        return 1 / decimal_odds
    else:
        raise ValueError("Invalid desired_format. Use 'american', 'decimal', or 'implied_prob'.")

def format_american_odds(odds):
    """Format American odds to include a + sign for positive values."""
    if isinstance(odds, str):
        return odds

    odds = int(round(odds, 0))

    if odds > 0:
        return f"+{odds}"
    else:
        return str(odds)

def compare_highest_positive_to_lowest_negative(df):
    """
    Compare the highest positive odds to the lowest negative odds for each game across bookmakers.
    Returns a DataFrame with the results.
    """
    if df.empty:
        return pd.DataFrame()
        
    results = []
    for game_id, game_data in df.groupby('game_id'):
        # Get home and away team
        home_team = game_data['home_team'].iloc[0]
        away_team = game_data['away_team'].iloc[0]

        # Separate home and away teams
        home_odds = game_data[game_data['outcome'] == home_team]
        away_odds = game_data[game_data['outcome'] == away_team]

        if not home_odds.empty and not away_odds.empty:
            max_home = home_odds.loc[home_odds['american_odds'].idxmax()]
            max_away = away_odds.loc[away_odds['american_odds'].idxmax()]

            # Calculate difference
            if max_home['american_odds'] > 0 and max_away['american_odds'] > 0:
                difference = (max_home['american_odds']-100) + (max_away['american_odds']-100)
            elif max_home['american_odds'] < 0 and max_away['american_odds'] < 0:
                difference = (max_home['american_odds'] + 100) + (max_away['american_odds'] + 100)
            elif max_home['american_odds'] > 0 and max_away['american_odds'] < 0:
                difference = abs(max_home['american_odds']) - abs(max_away['american_odds'])
            elif max_home['american_odds'] < 0 and max_away['american_odds'] > 0:
                difference = abs(max_away['american_odds']) - abs(max_home['american_odds'])
            else:
                difference = 0

            # Get implied prob for each team
            home_implied_prob = home_odds['implied_prob']
            away_implied_prob = away_odds['implied_prob']

            # Get avg implied prob for each team
            avg_home_implied_prob = home_implied_prob.mean()
            avg_away_implied_prob = away_implied_prob.mean()

            # Convert implied prob to american odds
            avg_home_american_odds = convert_odds(avg_home_implied_prob, 'implied_prob', 'american')
            avg_away_american_odds = convert_odds(avg_away_implied_prob, 'implied_prob', 'american')

            results.append({
                'game_id': game_id,
                'home_team': max_home['home_team'],
                'max_home_bookmaker': max_home['bookmaker'],
                'max_home_odds': format_american_odds(max_home['american_odds']),
                'mean_home_odds': format_american_odds(avg_home_american_odds),
                'away_team': max_home['away_team'],
                'max_away_bookmaker': max_away['bookmaker'],
                'max_away_odds': format_american_odds(max_away['american_odds']),
                'mean_away_odds': format_american_odds(avg_away_american_odds),
                'difference': round(difference, 2),
            })

    # Sort by difference
    results = sorted(results, key=lambda x: x['difference'], reverse=True)
    return pd.DataFrame(results)

def find_better_than_average_odds(df):
    """
    Find bookmakers offering better odds than the average for each game and outcome.
    Returns a DataFrame with the results.
    """
    if df.empty:
        return pd.DataFrame()
        
    results = []
    for game_id, game_data in df.groupby('game_id'):
        for outcome, outcome_data in game_data.groupby('outcome'):
            # Calculate the average odds for this outcome using implied probability
            implied_prob = outcome_data['implied_prob']
            avg_implied_prob = implied_prob.mean()
            avg_american_odds = convert_odds(avg_implied_prob, 'implied_prob', 'american')

            # Compare each bookmaker's odds to the average
            for _, row in outcome_data.iterrows():
                if row['american_odds'] > avg_american_odds:
                    # Calculate difference
                    if row['american_odds'] > 0 and avg_american_odds > 0:
                        difference = row['american_odds'] - avg_american_odds
                    elif row['american_odds'] < 0 and avg_american_odds < 0:
                        difference = row['american_odds'] - avg_american_odds
                    elif row['american_odds'] > 0 and avg_american_odds < 0:
                        difference = (abs(row['american_odds']) - 100) + (abs(avg_american_odds) - 100)
                    elif row['american_odds'] < 0 and avg_american_odds > 0:
                        difference = (abs(avg_american_odds) - 100) + (abs(row['american_odds']) - 100)
                    else:
                        difference = 0

                    # Check if game id and outcome is already in results
                    existing_result = None
                    for d in results:
                        if d['game_id'] == game_id and d['outcome'] == outcome:
                            existing_result = d
                            break

                    if existing_result:
                        # Check if the current bookmaker has better odds
                        # Handle both formatted strings and raw numbers
                        existing_odds = existing_result['american_odds']
                        if isinstance(existing_odds, str):
                            existing_odds_numeric = pd.to_numeric(existing_odds.replace('+', ''))
                        else:
                            existing_odds_numeric = existing_odds
                            
                        if row['american_odds'] > existing_odds_numeric:
                            existing_result.update({
                                'bookmaker': row['bookmaker'],
                                'american_odds': row['american_odds'],
                                'difference': round(difference, 2),
                                'implied_prob': row['implied_prob'],
                                'implied_prob_difference': avg_implied_prob - row['implied_prob']
                            })
                    else:
                        results.append({
                            'game_id': game_id,
                            'home_team': row['home_team'],
                            'away_team': row['away_team'],
                            'outcome': row['outcome'],
                            'bookmaker': row['bookmaker'],
                            'american_odds': format_american_odds(row['american_odds']),
                            'average_american_odds': format_american_odds(avg_american_odds),
                            'difference': round(difference, 2),
                            'implied_prob': row['implied_prob'],
                            'average_implied_prob': avg_implied_prob,
                            'implied_prob_difference': (avg_implied_prob - row['implied_prob'])
                        })

    # Sort by implied probability difference
    results = sorted(results, key=lambda x: x['implied_prob_difference'], reverse=True)
    return pd.DataFrame(results)

def print_frame(df, sport_name):
    """Print DataFrame with proper formatting"""
    if df.empty:
        print(f"No data available for {sport_name}")
        return
        
    df_copy = df.copy()
    
    # Convert implied prob to percentage
    if 'implied_prob' in df_copy.columns:
        df_copy['implied_prob'] = df_copy['implied_prob'].apply(lambda x: x*100)
        df_copy['average_implied_prob'] = df_copy['average_implied_prob'].apply(lambda x: x*100)
        df_copy['implied_prob_difference'] = df_copy['implied_prob_difference'].apply(lambda x: x*100)
        
        # Round to 2 decimal places
        df_copy['implied_prob'] = round(df_copy['implied_prob'], 2)
        df_copy['average_implied_prob'] = round(df_copy['average_implied_prob'], 2)
        df_copy['implied_prob_difference'] = round(df_copy['implied_prob_difference'], 2)

        # Add % sign
        df_copy['implied_prob'] = df_copy['implied_prob'].apply(lambda x: str(x) + '%')
        df_copy['average_implied_prob'] = df_copy['average_implied_prob'].apply(lambda x: str(x) + '%')
        df_copy['implied_prob_difference'] = df_copy['implied_prob_difference'].apply(lambda x: str(x) + '%')

    # Round difference to 2 decimal places
    if 'difference' in df_copy.columns:
        df_copy['difference'] = round(df_copy['difference'], 2)

    if 'american_odds' in df_copy.columns:
        df_copy['american_odds'] = df_copy['american_odds'].apply(format_american_odds)
        df_copy['average_american_odds'] = df_copy['average_american_odds'].apply(format_american_odds)

    print(f"\n{sport_name} Data:")
    print(df_copy.drop(columns=['game_id'] if 'game_id' in df_copy.columns else []))

def update_sport_info(sport_key):
    """Update information for a specific sport"""
    sport_name = SPORTS_CONFIG[sport_key]['name']
    url = get_sport_url(sport_key)
    
    print(f"\nProcessing {sport_name}...")
    
    # Check if sport is in season
    if not is_sport_in_season(sport_key):
        print(f"{sport_name} is currently off-season, but checking for games anyway...")
    
    df = access_api(url, sport_name)
    
    if df.empty:
        print(f"No {sport_name} data available")
        # Create empty DataFrames for consistency
        better_odds = pd.DataFrame()
        results = pd.DataFrame()
    else:
        # Ensure the 'american_odds' column is numeric
        df['american_odds'] = pd.to_numeric(df['american_odds'])
        df['american_odds'] = round(df['american_odds'], 0)

        better_odds = find_better_than_average_odds(df)
        results = compare_highest_positive_to_lowest_negative(df)
        
        print(f"{sport_name} Better odds:")
        print_frame(better_odds, sport_name)
        
        print(f"{sport_name} Results:")
        print_frame(results, sport_name)

    # Save data
    save_folder = 'saved_odds/'
    os.makedirs(save_folder, exist_ok=True)
    
    if not df.empty:
        df.to_csv(f'{save_folder}{sport_key}_odds.csv', index=False)

    # Save to JSON for website
    web_folder = 'static/data/'
    os.makedirs(web_folder, exist_ok=True)
    
    # Save JSON files (empty DataFrames will create empty JSON arrays)
    better_odds.to_json(f'{web_folder}{sport_key}_better_odds.json', orient='records')
    results.to_json(f'{web_folder}{sport_key}_results.json', orient='records')
    
    return len(df) > 0  # Return True if data was found

def update_all_sports():
    """Update information for all sports"""
    print("Starting multi-sport odds update...")
    
    sports_with_data = []
    
    for sport_key in SPORTS_CONFIG.keys():
        has_data = update_sport_info(sport_key)
        if has_data:
            sports_with_data.append(SPORTS_CONFIG[sport_key]['name'])
    
    # Update timestamp
    web_folder = 'static/data/'
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(f'{web_folder}last_updated.txt', 'w') as f:
        f.write(current_time)
    
    print(f"\nUpdate completed at {current_time}")
    if sports_with_data:
        print(f"Sports with data: {', '.join(sports_with_data)}")
    else:
        print("No sports data found (all leagues may be off-season)")

def main():
    update_all_sports()

if __name__ == '__main__':
    main()