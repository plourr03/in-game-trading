"""
Fetch Missing Kalshi Data Using Candlesticks
Downloads historical Kalshi market data for recent NBA games using candlesticks endpoint
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


def get_existing_games(data_folder='kalshi_data/jan_dec_2025_games'):
    """Get list of games we already have data for"""
    if not os.path.exists(data_folder):
        print(f"[INFO] Data folder doesn't exist: {data_folder}")
        return set()
    
    existing_games = set()
    for filename in os.listdir(data_folder):
        if filename.endswith('.csv'):
            existing_games.add(filename.replace('.csv', ''))
    
    print(f"[INFO] Found {len(existing_games)} existing game files")
    return existing_games


def get_recent_nba_games(days_back=7):
    """Get recent NBA games from the past N days"""
    print(f"\n[INFO] Fetching NBA games from the last {days_back} days...")
    
    today = datetime.now()
    start_date = today - timedelta(days=days_back)
    
    date_from = start_date.strftime('%m/%d/%Y')
    date_to = today.strftime('%m/%d/%Y')
    
    try:
        gamefinder = leaguegamefinder.LeagueGameFinder(
            date_from_nullable=date_from,
            date_to_nullable=date_to,
            league_id_nullable='00'
        )
        
        games = gamefinder.get_data_frames()[0]
        games = games.drop_duplicates(subset=['GAME_ID'])
        games = games.sort_values('GAME_DATE', ascending=False)
        
        print(f"[OK] Found {len(games)} games")
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
    """
    Fetch candlestick data for a Kalshi market
    
    Args:
        ticker: Market ticker
        kalshi_client: KalshiAPIClient instance
        period_interval: Interval in minutes (1 = 1-minute candles)
    """
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
                # Convert to DataFrame
                df = pd.DataFrame(candlesticks)
                
                # Rename columns to match our existing format
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
            print(f"      [ERROR] Status {response.status_code}: {response.text[:100]}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"      [ERROR] Failed to fetch candlesticks: {e}")
        return pd.DataFrame()


def download_missing_games(days_back=7, output_folder='kalshi_data/jan_dec_2025_games'):
    """Download Kalshi candlestick data for missing games"""
    
    print("="*80)
    print("FETCHING MISSING KALSHI DATA (CANDLESTICKS)")
    print("="*80)
    
    # Create output folder if needed
    os.makedirs(output_folder, exist_ok=True)
    
    # Get existing games
    existing_games = get_existing_games(output_folder)
    
    # Get recent NBA games
    nba_games = get_recent_nba_games(days_back)
    
    if nba_games.empty:
        print("\n[ERROR] No NBA games found")
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
    skipped = 0
    failed = 0
    
    for idx, game in nba_games.iterrows():
        game_id = game['GAME_ID']
        game_date = pd.to_datetime(game['GAME_DATE']).strftime('%Y-%m-%d')
        matchup = game['MATCHUP']
        
        # Parse teams from matchup
        if ' @ ' in matchup:
            away, home = matchup.split(' @ ')
        elif ' vs. ' in matchup:
            home, away = matchup.split(' vs. ')
        else:
            print(f"\n[SKIP] {game_date} - Can't parse matchup: {matchup}")
            skipped += 1
            continue
        
        # Get 3-letter abbreviations
        away_abbr = get_team_abbreviation(away)
        home_abbr = get_team_abbreviation(home)
        
        print(f"\n[{idx+1}/{len(nba_games)}] {game_date}: {away_abbr} @ {home_abbr}")
        
        # Search for Kalshi market
        print(f"  [INFO] Searching Kalshi markets...")
        markets = kalshi.find_nba_markets(away_abbr, home_abbr)
        
        if not markets:
            print(f"  [SKIP] No Kalshi market found")
            skipped += 1
            continue
        
        print(f"  [OK] Found {len(markets)} market(s)")
        
        # Download data for each market
        for market in markets:
            ticker = market['ticker']
            
            # Check if we already have this specific ticker
            if ticker in existing_games:
                print(f"    [SKIP] {ticker} - already have")
                skipped += 1
                continue
            
            print(f"    [FETCH] {ticker}...")
            
            # Fetch candlestick data (1-minute intervals)
            df = fetch_kalshi_candlesticks(ticker, kalshi, period_interval=1)
            
            if df.empty:
                print(f"      [SKIP] No candlestick data available")
                failed += 1
                continue
            
            # Add metadata columns
            df['ticker'] = ticker
            df['game_id'] = game_id
            df['away_team'] = away_abbr
            df['home_team'] = home_abbr
            df['game_date'] = game_date
            
            # Save to CSV
            output_file = os.path.join(output_folder, f"{ticker}.csv")
            df.to_csv(output_file, index=False)
            print(f"      [OK] Saved {len(df)} candlesticks to {ticker}.csv")
            downloaded += 1
            
            # Rate limit
            time.sleep(0.5)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Downloaded: {downloaded} games")
    print(f"Skipped (already have): {skipped} games")
    print(f"Failed: {failed} games")
    print(f"Total processed: {len(nba_games)} games")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch missing Kalshi candlestick data')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days back to check (default: 7)')
    parser.add_argument('--output', type=str, default='kalshi_data/jan_dec_2025_games',
                       help='Output folder for CSV files')
    
    args = parser.parse_args()
    
    print(f"\nFetching Kalshi candlestick data for games from the last {args.days} days...")
    print(f"Output folder: {args.output}\n")
    
    download_missing_games(days_back=args.days, output_folder=args.output)
    
    print("\n[OK] Done! You can now retrain your model with the updated data.")
