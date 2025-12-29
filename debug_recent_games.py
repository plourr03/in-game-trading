"""
Debug: Check what's happening with recent games
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import pandas as pd
from datetime import datetime, timedelta
from nba_api.stats.endpoints import leaguegamefinder
from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials
import requests


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


# Get yesterday's and day before games
print("Checking games from Dec 27-28, 2025...")
print("="*80)

gamefinder = leaguegamefinder.LeagueGameFinder(
    date_from_nullable='12/27/2025',
    date_to_nullable='12/28/2025',
    season_nullable='2025-26'
)

games = gamefinder.get_data_frames()[0]
games = games.drop_duplicates(subset=['GAME_ID'])
games = games.sort_values('GAME_DATE')

print(f"\nFound {len(games)} games on Dec 27-28:")
for idx, game in games.iterrows():
    date = pd.to_datetime(game['GAME_DATE']).strftime('%Y-%m-%d')
    print(f"  {date}: {game['MATCHUP']}")

# Connect to Kalshi
print("\n" + "="*80)
print("Checking Kalshi markets for these games...")
print("="*80)

api_key, private_key = load_kalshi_credentials()
kalshi = KalshiAPIClient(api_key, private_key)

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
    
    print(f"\n{date}: {away} @ {home}")
    print(f"  Looking for ticker with: {date_str}")
    
    # Search markets
    markets = kalshi.find_nba_markets(away, home)
    
    if not markets:
        print(f"  [NO MARKETS FOUND]")
        continue
    
    print(f"  Found {len(markets)} markets:")
    
    for market in markets:
        ticker = market['ticker']
        status = market.get('status', 'unknown')
        print(f"    - {ticker} (status: {status})")
        
        # Check if already have
        if os.path.exists(f"kalshi_data/jan_dec_2025_games/{ticker}.csv"):
            print(f"      [ALREADY HAVE]")
            continue
        
        # Try to fetch candlesticks
        print(f"      Fetching candlesticks...")
        try:
            path = f"/markets/{ticker}/candlesticks?period_interval=1"
            headers = kalshi._get_auth_headers("GET", path)
            resp = requests.get(f"{kalshi.base_url}{path}", headers=headers, timeout=30)
            
            print(f"      Response: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                candlesticks = data.get('candlesticks', [])
                print(f"      Candlesticks: {len(candlesticks)} records")
                
                if candlesticks:
                    print(f"      [DATA AVAILABLE - {len(candlesticks)} rows]")
                else:
                    print(f"      [NO DATA IN RESPONSE]")
            else:
                print(f"      Error: {resp.text[:200]}")
        except Exception as e:
            print(f"      Exception: {e}")

print("\n" + "="*80)


