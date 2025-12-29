"""
Kalshi Data Refresh - Download Missing Games
Simple script to keep your Kalshi data up-to-date
"""
import os
import time
import pandas as pd
from datetime import datetime
from nba_api.stats.endpoints import leaguegamefinder
import requests
import sys

sys.path.insert(0, os.getcwd())
from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials


def get_existing_tickers(folder='kalshi_data/jan_dec_2025_games'):
    """Get list of tickers we already have"""
    if not os.path.exists(folder):
        os.makedirs(folder)
        return set()
    
    tickers = {f.replace('.csv', '') for f in os.listdir(folder) if f.endswith('.csv')}
    return tickers


def get_all_season_games(season='2025-26'):
    """Get all games from the season"""
    print(f"[INFO] Fetching {season} season games from NBA API...")
    
    gamefinder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        season_type_nullable='Regular Season'
    )
    
    games = gamefinder.get_data_frames()[0]
    games = games.drop_duplicates(subset=['GAME_ID'])
    games = games.sort_values('GAME_DATE')
    
    return games


def get_team_abbr(name):
    """Convert team name to abbreviation"""
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


def fetch_candlesticks(ticker, kalshi):
    """Fetch Kalshi candlestick data"""
    try:
        path = f"/markets/{ticker}/candlesticks?period_interval=1"
        headers = kalshi._get_auth_headers("GET", path)
        resp = requests.get(f"{kalshi.base_url}{path}", headers=headers, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json().get('candlesticks', [])
            if data:
                df = pd.DataFrame(data)
                if 'open_price' in df.columns:
                    df = df.rename(columns={
                        'open_price': 'open', 'high_price': 'high',
                        'low_price': 'low', 'close_price': 'close',
                        'start_period_time': 'datetime'
                    })
                return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()


def refresh_data(folder='kalshi_data/jan_dec_2025_games', season='2025-26'):
    """Main data refresh function"""
    
    print("="*80)
    print("KALSHI DATA REFRESH")
    print("="*80)
    
    # 1. Get existing
    print(f"\n[1/4] Checking existing data...")
    existing = get_existing_tickers(folder)
    print(f"  Currently have: {len(existing)} games")
    
    # 2. Get all season games
    print(f"\n[2/4] Getting {season} season games...")
    try:
        all_games = get_all_season_games(season)
        print(f"  Total season games: {len(all_games)}")
        print(f"  Date range: {all_games['GAME_DATE'].min()} to {all_games['GAME_DATE'].max()}")
    except Exception as e:
        print(f"  [ERROR] {e}")
        return
    
    # 3. Connect to Kalshi
    print(f"\n[3/4] Connecting to Kalshi...")
    api_key, private_key = load_kalshi_credentials()
    kalshi = KalshiAPIClient(api_key, private_key)
    print(f"  Connected")
    
    # 4. Download missing
    print(f"\n[4/4] Downloading missing games...")
    print("="*80)
    
    downloaded = 0
    skipped = 0
    no_market = 0
    no_data = 0
    
    for idx, game in all_games.iterrows():
        # Parse teams
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
        
        # Find markets
        markets = kalshi.find_nba_markets(away, home)
        if not markets:
            no_market += 1
            continue
        
        # Check each market
        for market in markets:
            ticker = market['ticker']
            
            # Already have?
            if ticker in existing:
                skipped += 1
                continue
            
            # Match date
            date_str = pd.to_datetime(game['GAME_DATE']).strftime('%y%b%d').upper()
            if date_str not in ticker:
                continue
            
            # Fetch data
            df = fetch_candlesticks(ticker, kalshi)
            if df.empty:
                no_data += 1
                continue
            
            # Add metadata
            df['ticker'] = ticker
            df['game_id'] = game['GAME_ID']
            df['away_team'] = away
            df['home_team'] = home
            df['game_date'] = date
            
            # Save
            df.to_csv(f"{folder}/{ticker}.csv", index=False)
            print(f"[{downloaded+1}] {date}: {away}@{home} - {ticker} ({len(df)} rows)")
            downloaded += 1
            
            time.sleep(0.5)
    
    # Summary
    print("\n" + "="*80)
    print("REFRESH COMPLETE")
    print("="*80)
    print(f"Started with: {len(existing)} games")
    print(f"Downloaded: {downloaded} new games")
    print(f"Already had: {skipped} games")
    print(f"No market: {no_market} games")
    print(f"No data: {no_data} games")
    print(f"Total now: {len(existing) + downloaded} games")
    print("="*80)


if __name__ == "__main__":
    refresh_data()


