"""
Check older games (Dec 14-26) to see if they have data now
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder
from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials
import requests
import time


def get_team_abbr(name):
    teams = {
        'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
        'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
        'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
        'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
        'LA Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
        'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
        'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
        'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
        'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
        'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
    }
    return teams.get(name, name[:3].upper())


print("Checking games from Dec 14-26, 2025 (older games)")
print("="*80)

gamefinder = leaguegamefinder.LeagueGameFinder(
    date_from_nullable='12/14/2025',
    date_to_nullable='12/26/2025',
    season_nullable='2025-26'
)

games = gamefinder.get_data_frames()[0]
games = games.drop_duplicates(subset=['GAME_ID'])
games = games.sort_values('GAME_DATE')

print(f"\nFound {len(games)} games on Dec 14-26")

# Connect to Kalshi
api_key, private_key = load_kalshi_credentials()
kalshi = KalshiAPIClient(api_key, private_key)

downloaded = 0
no_market = 0
no_data = 0
already_have = 0

for idx, game in games.iterrows():
    matchup = game['MATCHUP']
    
    if ' @ ' in matchup:
        away, home = matchup.split(' @ ')
    elif ' vs. ' in matchup:
        home, away = matchup.split(' vs. ')
    else:
        continue
    
    away = get_team_abbr(away)
    home = get_team_abbr(home)
    date = pd.to_datetime(game['GAME_DATE']).strftime('%Y-%m-%d')
    date_str = pd.to_datetime(game['GAME_DATE']).strftime('%y%b%d').upper()
    
    # Search markets
    markets = kalshi.find_nba_markets(away, home)
    
    if not markets:
        no_market += 1
        continue
    
    # Check each market
    for market in markets:
        ticker = market['ticker']
        
        # Match date
        if date_str not in ticker:
            continue
        
        # Already have?
        if os.path.exists(f"kalshi_data/jan_dec_2025_games/{ticker}.csv"):
            already_have += 1
            continue
        
        # Try to fetch
        try:
            path = f"/markets/{ticker}/candlesticks?period_interval=1"
            headers = kalshi._get_auth_headers("GET", path)
            resp = requests.get(f"{kalshi.base_url}{path}", headers=headers, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json().get('candlesticks', [])
                if data:
                    # Save it!
                    df = pd.DataFrame(data)
                    df = df.rename(columns={
                        'open_price': 'open', 'high_price': 'high',
                        'low_price': 'low', 'close_price': 'close',
                        'start_period_time': 'datetime'
                    })
                    df['ticker'] = ticker
                    df['game_id'] = game['GAME_ID']
                    df['away_team'] = away
                    df['home_team'] = home
                    df['game_date'] = date
                    
                    df.to_csv(f"kalshi_data/jan_dec_2025_games/{ticker}.csv", index=False)
                    print(f"[{downloaded+1}] {date}: {ticker} ({len(df)} rows)")
                    downloaded += 1
                else:
                    no_data += 1
            else:
                no_data += 1
        except:
            no_data += 1
        
        time.sleep(0.3)

print("\n" + "="*80)
print(f"Downloaded: {downloaded} new games")
print(f"Already had: {already_have} games")
print(f"No market: {no_market} games")
print(f"No data: {no_data} games")
print("="*80)


