"""
Fetch Missing Kalshi Data for Date Range
Downloads Kalshi data for games between Dec 13 - Today
"""
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from nba_api.stats.endpoints import leaguegamefinder
import requests
import sys

sys.path.insert(0, os.getcwd())

from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials


def get_existing_tickers(data_folder='kalshi_data/jan_dec_2025_games'):
    """Get set of tickers we already have"""
    if not os.path.exists(data_folder):
        print(f"[INFO] Data folder doesn't exist: {data_folder}")
        return set()
    
    existing = set()
    for filename in os.listdir(data_folder):
        if filename.endswith('.csv'):
            ticker = filename.replace('.csv', '')
            existing.add(ticker)
    
    print(f"[INFO] Found {len(existing)} existing game files")
    return existing


def get_games_in_date_range(start_date='12/14/2025', end_date=None):
    """Get NBA games between two dates"""
    
    if end_date is None:
        end_date = datetime.now().strftime('%m/%d/%Y')
    
    print(f"\n[INFO] Fetching games from {start_date} to {end_date}...")
    print(f"[INFO] Season: 2025-26")
    
    try:
        gamefinder = leaguegamefinder.LeagueGameFinder(
            date_from_nullable=start_date,
            date_to_nullable=end_date,
            league_id_nullable='00',
            season_nullable='2025-26',
            season_type_nullable='Regular Season'
        )
        
        games = gamefinder.get_data_frames()[0]
        games = games.drop_duplicates(subset=['GAME_ID'])
        games = games.sort_values('GAME_DATE', ascending=True)
        
        print(f"[OK] Found {len(games)} games in date range")
        return games
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch NBA games: {e}")
        return pd.DataFrame()


def get_team_abbreviation(team_name):
    """Convert team name to 3-letter abbreviation"""
    team_map = {
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
    return team_map.get(team_name, team_name[:3].upper())


def fetch_kalshi_candlesticks(ticker, kalshi_client, period_interval=1):
    """Fetch candlestick data for a Kalshi market"""
    try:
        path = f"/markets/{ticker}/candlesticks"
        params = f"?period_interval={period_interval}"
        full_path = path + params
        
        headers = kalshi_client._get_auth_headers("GET", full_path)
        
        response = requests.get(
            f"{kalshi_client.base_url}{full_path}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            candlesticks = data.get('candlesticks', [])
            
            if candlesticks:
                df = pd.DataFrame(candlesticks)
                
                if 'open_price' in df.columns:
                    df = df.rename(columns={
                        'open_price': 'open',
                        'high_price': 'high',
                        'low_price': 'low',
                        'close_price': 'close',
                        'volume': 'volume',
                        'start_period_time': 'datetime'
                    })
                
                return df
            else:
                return pd.DataFrame()
        else:
            return pd.DataFrame()
            
    except Exception as e:
        return pd.DataFrame()


def download_date_range(start_date='12/13/2024', end_date=None, 
                        output_folder='kalshi_data/jan_dec_2025_games'):
    """Download Kalshi data for games in date range"""
    
    print("="*80)
    print(f"FETCHING KALSHI DATA: {start_date} to {end_date or 'Today'}")
    print("="*80)
    
    os.makedirs(output_folder, exist_ok=True)
    
    # Get existing tickers
    existing_tickers = get_existing_tickers(output_folder)
    
    # Get games in date range
    nba_games = get_games_in_date_range(start_date, end_date)
    
    if nba_games.empty:
        print("\n[ERROR] No games found in date range")
        return
    
    # Initialize Kalshi client
    print("\n[INFO] Connecting to Kalshi API...")
    api_key, private_key = load_kalshi_credentials()
    kalshi = KalshiAPIClient(api_key, private_key)
    print("[OK] Connected")
    
    # Process each game
    print("\n" + "="*80)
    print("PROCESSING GAMES")
    print("="*80)
    
    downloaded = 0
    skipped_have = 0
    skipped_no_market = 0
    skipped_no_data = 0
    
    for idx, game in nba_games.iterrows():
        game_id = game['GAME_ID']
        game_date = pd.to_datetime(game['GAME_DATE']).strftime('%Y-%m-%d')
        matchup = game['MATCHUP']
        
        # Parse teams
        if ' @ ' in matchup:
            away, home = matchup.split(' @ ')
        elif ' vs. ' in matchup:
            home, away = matchup.split(' vs. ')
        else:
            skipped_no_market += 1
            continue
        
        away_abbr = get_team_abbreviation(away)
        home_abbr = get_team_abbreviation(home)
        
        print(f"\n[{idx+1}/{len(nba_games)}] {game_date}: {away_abbr} @ {home_abbr}")
        
        # Search for Kalshi markets
        print(f"  Searching Kalshi...")
        markets = kalshi.find_nba_markets(away_abbr, home_abbr)
        
        if not markets:
            print(f"  [SKIP] No Kalshi market found")
            skipped_no_market += 1
            continue
        
        print(f"  Found {len(markets)} market(s)")
        
        # Try each market
        for market in markets:
            ticker = market['ticker']
            
            # Check if we already have it
            if ticker in existing_tickers:
                print(f"    [SKIP] {ticker} - already have")
                skipped_have += 1
                continue
            
            # Check if ticker matches this game date
            date_str = pd.to_datetime(game['GAME_DATE']).strftime('%y%b%d').upper()
            if date_str not in ticker:
                continue
            
            print(f"    [FETCH] {ticker}...")
            
            # Fetch candlestick data
            df = fetch_kalshi_candlesticks(ticker, kalshi, period_interval=1)
            
            if df.empty:
                print(f"      [SKIP] No data available")
                skipped_no_data += 1
                continue
            
            # Add metadata
            df['ticker'] = ticker
            df['game_id'] = game_id
            df['away_team'] = away_abbr
            df['home_team'] = home_abbr
            df['game_date'] = game_date
            
            # Save
            output_file = os.path.join(output_folder, f"{ticker}.csv")
            df.to_csv(output_file, index=False)
            print(f"      [OK] Saved {len(df)} rows")
            downloaded += 1
            
            # Rate limit
            time.sleep(0.5)
    
    # Summary
    print("\n" + "="*80)
    print("DOWNLOAD SUMMARY")
    print("="*80)
    print(f"Date range: {start_date} to {end_date or 'Today'}")
    print(f"Games in range: {len(nba_games)}")
    print(f"\nResults:")
    print(f"  Downloaded: {downloaded} new games")
    print(f"  Already had: {skipped_have} games")
    print(f"  No Kalshi market: {skipped_no_market} games")
    print(f"  No data available: {skipped_no_data} games")
    print(f"\nTotal games now: {len(existing_tickers) + downloaded}")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch Kalshi data for date range')
    parser.add_argument('--start', type=str, default='12/14/2025',
                       help='Start date (MM/DD/YYYY) - default: 12/14/2025')
    parser.add_argument('--end', type=str, default=None,
                       help='End date (MM/DD/YYYY) - defaults to today (12/29/2025)')
    parser.add_argument('--output', type=str, default='kalshi_data/jan_dec_2025_games',
                       help='Output folder')
    
    args = parser.parse_args()
    
    download_date_range(
        start_date=args.start,
        end_date=args.end,
        output_folder=args.output
    )
    
    print("\n[OK] Done! You can now retrain your model with the complete dataset.")

