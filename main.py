import requests
import pandas as pd
import datetime
import os
import sys
from dotenv import load_dotenv

diff_threshold = 0.1
folder = 'saved_odds/'

load_dotenv()
API_KEY =os.getenv('API_KEY')

# API endpoint for NHL odds
url = f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds/?apiKey={API_KEY}&regions=us&markets=h2h"



def access_api(url):
    """Fetch odds data from the API and return a DataFrame."""
    response = requests.get(url)
    data = response.json()

    # Convert to a pandas DataFrame for easier analysis
    games = []
    for game in data:
        for bookmaker in game['bookmakers']:
            for market in bookmaker['markets']:
                for outcome in market['outcomes']:
                    # Convert decimal odds to American odds
                    decimal_odds = outcome['price']
                    american_odds = int(round(convert_odds(decimal_odds, 'decimal', 'american'),0))
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
    return df

def read_csv(file):
    """Read odds data from a CSV file and return a DataFrame."""
    if not os.path.exists(file):
        print(f"Error: File '{file}' not found.")
        sys.exit()

    #make sure to open csv if multiple files have same name

    
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

    #if not string
    if isinstance(odds, str):
        return odds


    #round to 0 decimal places
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
    results = []
    for game_id, game_data in df.groupby('game_id'): #for each game

        # Separate positive and negative odds
        positive_odds = game_data[game_data['american_odds'] > 0]
        negative_odds = game_data[game_data['american_odds'] < 0]

        #find highest positive and lowest negative odds

        if not positive_odds.empty and not negative_odds.empty:
            # Find the highest positive odds
            max_positive = positive_odds.loc[positive_odds['american_odds'].idxmax()]
            # Find the lowest negative odds
            max_negative = negative_odds.loc[negative_odds['american_odds'].idxmax()]

            # Compare absolute values
            if abs(max_positive['american_odds']) > abs(max_negative['american_odds']):
                free_profit = True
            else:
                free_profit = False
            results.append({
                'game_id': game_id,
                'home_team': max_positive['home_team'],
                'away_team': max_positive['away_team'],
                'max_positive_bookmaker': max_positive['bookmaker'],
                'positive_outcome': max_positive['outcome'],
                'max_positive_odds': format_american_odds(max_positive['american_odds']),
                'average_positive_odds': format_american_odds(positive_odds['american_odds'].mean()),
                'max_negative_bookmaker': max_negative['bookmaker'],
                'negative_outcome': max_negative['outcome'],
                'max_negative_odds': format_american_odds(max_negative['american_odds']),
                'average_negative_odds': format_american_odds(negative_odds['american_odds'].mean()),
                'difference': round(abs(max_positive['american_odds']) - abs(max_negative['american_odds']),2),
            })

    #sort by difference
    results = sorted(results, key=lambda x: x['difference'], reverse=True)

    return pd.DataFrame(results)

def find_better_than_average_odds(df):
    """
    Find bookmakers offering better odds than the average for each game and outcome.
    Returns a DataFrame with the results.
    """
    results = []
    for game_id, game_data in df.groupby('game_id'):  # for each game
        for outcome, outcome_data in game_data.groupby('outcome'):  # for each outcome
            # Calculate the average odds for this outcome
            avg_american_odds = outcome_data['american_odds'].mean()

            implied_prob = outcome_data['implied_prob']
            avg_implied_prob = implied_prob.mean()

            # Compare each bookmaker's odds to the average
            for _, row in outcome_data.iterrows():
                if row['american_odds'] > avg_american_odds:

                    #check if game id and outcomne is already in results
                    if any(d['game_id'] == game_id and d['outcome'] == outcome for d in results):
                        #check if the current bookmaker has better odds than the one in the results
                        for d in results:
                            if d['game_id'] == game_id and d['outcome'] == outcome:
                                if row['american_odds'] > pd.to_numeric(d['american_odds']):
                                    d['bookmaker'] = row['bookmaker']
                                    d['american_odds'] = row['american_odds']
                                    d['difference'] = row['american_odds'] - avg_american_odds
                                    d['implied_prob'] = row['implied_prob']
                                    d['implied_prob_difference'] = avg_implied_prob - row['implied_prob']

                    else:

                   
                        results.append({
                            'game_id': game_id,
                            'home_team': row['home_team'],
                            'away_team': row['away_team'],
                            'outcome': row['outcome'],
                            'bookmaker': row['bookmaker'],
                            'american_odds': format_american_odds(row['american_odds']),
                            'average_american_odds': format_american_odds(avg_american_odds),
                            'difference': round(row['american_odds'] - avg_american_odds, 2),
                            'implied_prob': row['implied_prob'],
                            'average_implied_prob': avg_implied_prob,
                            'implied_prob_difference': ( avg_implied_prob - row['implied_prob'])

                        })


    #sort by difference
    #results = sorted(results, key=lambda x: x['difference'], reverse=True)
    results = sorted(results, key=lambda x: x['implied_prob_difference'], reverse=True)

    return pd.DataFrame(results)

def print_frame(df):
    #without game id

    #convert implied prob to percentage
    if 'implied_prob' in df.columns:

        #round to 2 decimal places

        df['implied_prob'] = df['implied_prob'].apply(lambda x: x*100)
        df['average_implied_prob'] = df['average_implied_prob'].apply(lambda x: x*100)
        df['implied_prob_difference'] = df['implied_prob_difference'].apply(lambda x: x*100)

        
        #round  to 2 decimal places
        df['implied_prob'] = round(df['implied_prob'], 2)
        df['average_implied_prob'] = round(df['average_implied_prob'], 2)
        df['implied_prob_difference'] = round(df['implied_prob_difference'], 2)

        #add % sign\
        df['implied_prob'] = df['implied_prob'].apply(lambda x: str(x) + '%')
        df['average_implied_prob'] = df['average_implied_prob'].apply(lambda x: str(x) + '%')
        df['implied_prob_difference'] = df['implied_prob_difference'].apply(lambda x: str(x) + '%')


    #round difference to 2 decimal places
    if 'difference' in df.columns:
        df['difference'] = round(df['difference'], 2)

    if 'american_odds' in df.columns:
        df['american_odds'] = df['american_odds'].apply(format_american_odds)
        df['average_american_odds'] = df['average_american_odds'].apply(format_american_odds)

    print(df.drop(columns=['game_id']))


def update_info():
    df = access_api(url)


    # Ensure the 'american_odds' column is numeric
    df['american_odds'] = pd.to_numeric(df['american_odds'])

    #round american odds to 0 decimal places
    df['american_odds'] = round(df['american_odds'], 0)

    better_odds = find_better_than_average_odds(df)
    print("Better odds:")
    print_frame(better_odds)

    #highest and lowest odds for wach game
    results = compare_highest_positive_to_lowest_negative(df)
    print("Results:")
    print_frame(results)


    folder = 'saved_odds/'
    os.makedirs(folder, exist_ok=True)

    df.to_csv(folder+'nhl_odds.csv', index=False)


    folder = 'static/data/'
    os.makedirs(folder, exist_ok=True)

    # Save to JSON
    better_odds.to_json(folder+'better_odds.json', orient='records')
    results.to_json(folder+'results.json', orient='records')

    #get current time
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(folder+'last_updated.txt', 'w') as f:
        f.write(current_time)
        f.close()






# # Ask user if they want to read from CSV or API
# print("Do you want to read from csv or api?")
# print("1. csv")
# print("2. api")
# choice = input("Enter your choice: ")

# if choice == '1' or choice == 'csv':
#     # Open most recent file
#     file = 'nhl_odds.csv'

#     #gET MOST RECENT FILe (saved time is in title)
#     files = os.listdir(folder)


#     if files:
#         files = [folder + f for f in files]
#         file = max(files, key=os.path.getctime)

#     print(f"Reading data from '{file}'")

#     df = read_csv(file)
# elif choice == '2' or choice == 'api':
#     update_info()

# else:
#     print("Invalid input")
#     sys.exit()

# # Ensure the 'american_odds' column is numeric
# df['american_odds'] = pd.to_numeric(df['american_odds'])

# #round american odds to 0 decimal places
# df['american_odds'] = round(df['american_odds'], 0)

# better_odds = find_better_than_average_odds(df)
# print("Better odds:")
# print_frame(better_odds)

# #highest and lowest odds for wach game
# results = compare_highest_positive_to_lowest_negative(df)
# print("Results:")
# print_frame(results)

# #todo
# #run pyython code daily (use windows task scheduler?)
# #then commit daily to update sit
# #this will flood repo with commits... 
# #maybe make secondary branch or repo for site,
# #one to write code for and one for the site
# #then merge code to site repo when ready


def main():
    update_info()

if __name__ == '__main__':
    main()