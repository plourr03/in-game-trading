"""
Fetch ALL Missing Kalshi Data for 2024-25 Season
Checks entire season and downloads any games we don't have yet
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


def get_existing_game_ids(data_folder='kalshi_data/jan_dec_2025_games'):
    """Get list of game IDs we already have data for"""
    if not os.path.exists(data_folder):
        print(f"[INFO] Data folder doesn't exist: {data_folder}")
        return set()
    
    existing_games = {}  # ticker -> game_info
    
    for filename in os.listdir(data_folder):
        if filename.endswith('.csv'):
            try:
                # Read CSV to get game_id
                df = pd.read_csv(os.path.join(data_folder, filename), nrows=1)
                if 'game_id' in df.columns:
                    game_id = str(df['game_id'].iloc[0])
                    ticker = filename.replace('.csv', '')
                    existing_games[game_id] = ticker
            except:
                continue
    
    print(f"[INFO] Found {len(existing_games)} existing games")
    return existing_games


def get_all_season_games(season='2024-25'):
    """Get ALL NBA games from the 2024-25 season"""
    print(f"\n[INFO] Fetching ALL games from {season} season...")
    
    try:
        # Get all games from the season
        gamefinder = leaguegamefinder.LeagueGameFinder(
            season_nullable=season,
            league_id_nullable='00',
            season_type_nullable='Regular Season'
        )
        
        games = gamefinder.get_data_frames()[0]
        
        # Filter to get unique games (each game appears twice, once per team)
        games = games.drop_duplicates(subset=['GAME_ID'])
        
        # Sort by date
        games = games.sort_values('GAME_DATE', ascending=True)
        
        print(f"[OK] Found {len(games)} total games in {season} season")
        
        # Show date range
        first_game = pd.to_datetime(games['GAME_DATE'].min()).strftime('%Y-%m-%d')
        last_game = pd.to_datetime(games['GAME_DATE'].max()).strftime('%Y-%m-%d')
        print(f"[INFO] Date range: {first_game} to {last_game}")
        
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
                
                # Rename columns to match our format
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


def download_all_missing_games(output_folder='kalshi_data/jan_dec_2025_games', season='2024-25'):
    """Download Kalshi data for ALL missing games from the season"""
    
    print("="*80)
    print(f"FETCHING ALL MISSING KALSHI DATA - {season} SEASON")
    print("="*80)
    
    # Create output folder if needed
    os.makedirs(output_folder, exist_ok=True)
    
    # Get existing games
    existing_games = get_existing_game_ids(output_folder)
    print(f"[INFO] Currently have: {len(existing_games)} games")
    
    # Get ALL season games
    nba_games = get_all_season_games(season)
    
    if nba_games.empty:
        print("\n[ERROR] No NBA games found")
        return
    
    print(f"[INFO] Total season games: {len(nba_games)}")
    print(f"[INFO] Missing games: {len(nba_games) - len(existing_games)}")
    
    # Initialize Kalshi client
    print("\n[INFO] Connecting to Kalshi API...")
    api_key, private_key = load_kalshi_credentials()
    kalshi = KalshiAPIClient(api_key, private_key)
    print("[OK] Connected")
    
    # Filter to only missing games
    missing_games = nba_games[~nba_games['GAME_ID'].isin(existing_games.keys())]
    
    print(f"\n[INFO] Will attempt to download {len(missing_games)} missing games")
    
    # Process each missing game
    print("\n" + "="*80)
    print("PROCESSING MISSING GAMES")
    print("="*80)
    
    downloaded = 0
    skipped_no_market = 0
    skipped_no_data = 0
    failed = 0
    
    for idx, game in missing_games.iterrows():
        game_id = game['GAME_ID']
        game_date = pd.to_datetime(game['GAME_DATE']).strftime('%Y-%m-%d')
        matchup = game['MATCHUP']
        
        # Parse teams from matchup
        if ' @ ' in matchup:
            away, home = matchup.split(' @ ')
        elif ' vs. ' in matchup:
            home, away = matchup.split(' vs. ')
        else:
            skipped_no_market += 1
            continue
        
        # Get 3-letter abbreviations
        away_abbr = get_team_abbreviation(away)
        home_abbr = get_team_abbreviation(home)
        
        # Show progress every 10 games
        if (idx % 10) == 0 or idx == len(missing_games) - 1:
            print(f"\n[Progress: {idx+1}/{len(missing_games)}] {game_date}: {away_abbr} @ {home_abbr}")
        
        # Search for Kalshi market
        markets = kalshi.find_nba_markets(away_abbr, home_abbr)
        
        if not markets:
            skipped_no_market += 1
            continue
        
        # Download data for each market
        found_data = False
        for market in markets:
            ticker = market['ticker']
            
            # Check if ticker matches this game date
            # Kalshi ticker format: KXNBAGAME-25DEC28SACLAL-LAL
            date_str = pd.to_datetime(game['GAME_DATE']).strftime('%y%b%d').upper()
            if date_str not in ticker:
                continue  # Skip markets from different dates
            
            # Fetch candlestick data
            df = fetch_kalshi_candlesticks(ticker, kalshi, period_interval=1)
            
            if df.empty:
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
            
            if (idx % 10) == 0 or idx == len(missing_games) - 1:
                print(f"    [OK] Downloaded {ticker} ({len(df)} rows)")
            
            downloaded += 1
            found_data = True
            
            # Rate limit
            time.sleep(0.3)
        
        if not found_data:
            skipped_no_data += 1
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Season: {season}")
    print(f"Total games in season: {len(nba_games)}")
    print(f"Games already had: {len(existing_games)}")
    print(f"Missing games found: {len(missing_games)}")
    print(f"\nDownload Results:")
    print(f"  Successfully downloaded: {downloaded}")
    print(f"  No Kalshi market: {skipped_no_market}")
    print(f"  No data available: {skipped_no_data}")
    print(f"  Failed: {failed}")
    print(f"\nNew total: {len(existing_games) + downloaded} games")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch ALL missing Kalshi data from season')
    parser.add_argument('--season', type=str, default='2024-25',
                       help='NBA season (default: 2024-25)')
    parser.add_argument('--output', type=str, default='kalshi_data/jan_dec_2025_games',
                       help='Output folder for CSV files')
    
    args = parser.parse_args()
    
    print(f"\nFetching ALL missing Kalshi data for {args.season} season...")
    print(f"Output folder: {args.output}\n")
    
    download_all_missing_games(output_folder=args.output, season=args.season)
    
    print("\n[OK] Done! Run this again periodically to get new games as they become available.")



