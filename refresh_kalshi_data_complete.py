"""
Refresh Kalshi Data - Complete Version
Gets game IDs from database and uses correct naming format
"""
import os
import time
import pandas as pd
from datetime import datetime, timezone, timedelta
import requests
import sys
import yaml
import psycopg2

sys.path.insert(0, os.getcwd())
from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials


def get_db_connection():
    """Connect to PBP database"""
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    db_config = config['database']
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )
    return conn


def get_all_games_from_db():
    """Get all 2025-26 season games with game_ids from database"""
    print("[INFO] Fetching game_ids from database...")
    
    conn = get_db_connection()
    
    # Just get unique game_ids from PBP data
    query = """
        SELECT DISTINCT game_id
        FROM nba.nba_play_by_play
        ORDER BY game_id
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Now use nba_api to get full game details
    from nba_api.stats.endpoints import leaguegamefinder
    
    print("[INFO] Fetching game details from NBA API...")
    gamefinder = leaguegamefinder.LeagueGameFinder(
        season_nullable='2025-26',
        season_type_nullable='Regular Season'
    )
    
    all_games = gamefinder.get_data_frames()[0]
    all_games = all_games.drop_duplicates(subset=['GAME_ID'])
    
    # Filter to only games we have in database
    db_game_ids = set(df['game_id'].astype(str).str.zfill(10))
    all_games = all_games[all_games['GAME_ID'].isin(db_game_ids)]
    
    # Create output dataframe
    result = pd.DataFrame({
        'game_id': all_games['GAME_ID'],
        'home_team': all_games['MATCHUP'].apply(lambda x: x.split(' @ ')[1] if ' @ ' in x else x.split(' vs. ')[0]),
        'away_team': all_games['MATCHUP'].apply(lambda x: x.split(' @ ')[0] if ' @ ' in x else x.split(' vs. ')[1]),
        'game_date': pd.to_datetime(all_games['GAME_DATE']).dt.strftime('%Y-%m-%d')
    })
    
    return result


def get_existing_game_ids(folder='kalshi_data/jan_dec_2025_games'):
    """Get set of game_ids we already have"""
    if not os.path.exists(folder):
        os.makedirs(folder)
        return set()
    
    game_ids = set()
    for filename in os.listdir(folder):
        if filename.endswith('_candles.csv'):
            # Extract game_id from filename: 22500001_HOU_at_OKC_2025-10-21_candles.csv
            parts = filename.split('_')
            if len(parts) >= 1:
                try:
                    game_ids.add(int(parts[0]))
                except:
                    pass
    
    return game_ids


def get_team_abbr(name):
    """Convert team name to abbreviation"""
    teams = {
        'ATL': 'ATL', 'BOS': 'BOS', 'BKN': 'BKN', 'CHA': 'CHA', 'CHI': 'CHI',
        'CLE': 'CLE', 'DAL': 'DAL', 'DEN': 'DEN', 'DET': 'DET', 'GSW': 'GSW',
        'HOU': 'HOU', 'IND': 'IND', 'LAC': 'LAC', 'LAL': 'LAL', 'MEM': 'MEM',
        'MIA': 'MIA', 'MIL': 'MIL', 'MIN': 'MIN', 'NOP': 'NOP', 'NYK': 'NYK',
        'OKC': 'OKC', 'ORL': 'ORL', 'PHI': 'PHI', 'PHX': 'PHX', 'POR': 'POR',
        'SAC': 'SAC', 'SAS': 'SAS', 'TOR': 'TOR', 'UTA': 'UTA', 'WAS': 'WAS'
    }
    # Handle full names too
    full_names = {
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
    
    return teams.get(name, full_names.get(name, name[:3].upper()))


def fetch_candlesticks_correct(ticker, game_date, kalshi):
    """Fetch Kalshi candlestick data using CORRECT endpoint"""
    try:
        # Calculate timestamp range
        game_dt = pd.to_datetime(game_date)
        start_ts = int((game_dt - timedelta(days=1)).replace(tzinfo=timezone.utc).timestamp())
        end_ts = int((game_dt + timedelta(days=2)).replace(tzinfo=timezone.utc).timestamp())
        
        # CORRECT endpoint format
        path = f"/series/KXNBAGAME/markets/{ticker}/candlesticks"
        params = f"?start_ts={start_ts}&end_ts={end_ts}&period_interval=1"
        full_path = path + params
        
        headers = kalshi._get_auth_headers("GET", full_path)
        resp = requests.get(f"{kalshi.base_url}{full_path}", headers=headers, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json().get('candlesticks', [])
            if data:
                # Parse candlesticks
                candle_list = []
                for c in data:
                    ts = c.get('end_period_ts', c.get('start_period_ts', 0))
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
                    price = c.get('price', {})
                    
                    candle_list.append({
                        'timestamp': ts,
                        'datetime': dt.strftime('%Y-%m-%d %H:%M:%S') if dt else None,
                        'open': price.get('open'),
                        'high': price.get('high'),
                        'low': price.get('low'),
                        'close': price.get('close'),
                        'volume': c.get('volume', 0)
                    })
                
                return pd.DataFrame(candle_list)
        
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()


def refresh_data(folder='kalshi_data/jan_dec_2025_games'):
    """Main data refresh function"""
    
    print("="*80)
    print("KALSHI DATA REFRESH - COMPLETE")
    print("="*80)
    
    # 1. Get existing game_ids
    print(f"\n[1/4] Checking existing data...")
    existing_game_ids = get_existing_game_ids(folder)
    print(f"  Currently have: {len(existing_game_ids)} games")
    
    # 2. Get all games from database
    print(f"\n[2/4] Getting games from database...")
    try:
        all_games = get_all_games_from_db()
        print(f"  Total games in DB: {len(all_games)}")
        if len(all_games) > 0:
            print(f"  Date range: {all_games['game_date'].min()} to {all_games['game_date'].max()}")
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
        game_id = int(game['game_id'])
        
        # Already have?
        if game_id in existing_game_ids:
            skipped += 1
            continue
        
        home = get_team_abbr(game['home_team'])
        away = get_team_abbr(game['away_team'])
        date = game['game_date']
        
        # Find markets
        markets = kalshi.find_nba_markets(away, home)
        if not markets:
            no_market += 1
            continue
        
        # Check each market
        found = False
        for market in markets:
            ticker = market['ticker']
            
            # Match date
            date_str = pd.to_datetime(date).strftime('%y%b%d').upper()
            if date_str not in ticker:
                continue
            
            # Fetch data
            df = fetch_candlesticks_correct(ticker, date, kalshi)
            if df.empty:
                continue
            
            # Add metadata columns
            df.insert(0, 'game_id', game_id)
            df.insert(1, 'ticker', ticker)
            
            # Save with CORRECT filename format
            filename = f"{game_id}_{away}_at_{home}_{date}_candles.csv"
            output_file = os.path.join(folder, filename)
            df.to_csv(output_file, index=False)
            
            print(f"[{downloaded+1}] {date}: {away}@{home} - {filename} ({len(df)} rows)")
            downloaded += 1
            found = True
            
            time.sleep(0.5)
            break
        
        if not found:
            no_data += 1
    
    # Summary
    print("\n" + "="*80)
    print("REFRESH COMPLETE")
    print("="*80)
    print(f"Started with: {len(existing_game_ids)} games")
    print(f"Downloaded: {downloaded} new games")
    print(f"Already had: {skipped} games")
    print(f"No market: {no_market} games")
    print(f"No data: {no_data} games")
    print(f"Total now: {len(existing_game_ids) + downloaded} games")
    print("="*80)


if __name__ == "__main__":
    refresh_data()

