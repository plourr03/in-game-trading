"""
Add Missing Play-by-Play Data to Database
Fetches PBP data for games that are in Kalshi folder but not in database
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import pandas as pd
import psycopg2
import yaml
from nba_api.stats.endpoints import playbyplayv2
from datetime import datetime
import time


def get_db_connection():
    """Connect to database"""
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    db_config = config['database']
    return psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )


def get_games_in_kalshi_folder():
    """Get all game IDs from Kalshi folder"""
    folder = 'kalshi_data/jan_dec_2025_games'
    game_ids = set()
    
    for filename in os.listdir(folder):
        if filename.endswith('_candles.csv'):
            # Extract game_id: 0022500378_GSW_at_PHX_2025-12-18_candles.csv
            parts = filename.split('_')
            if len(parts) >= 1:
                game_ids.add(parts[0])
    
    return sorted(game_ids)


def get_games_in_database():
    """Get all game IDs from database"""
    conn = get_db_connection()
    
    query = """
        SELECT DISTINCT game_id
        FROM nba.nba_play_by_play
        WHERE game_id LIKE '0022500%'
        ORDER BY game_id
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    return set(df['game_id'].astype(str))


def fetch_pbp_data(game_id):
    """Fetch play-by-play data from NBA API"""
    try:
        pbp = playbyplayv2.PlayByPlayV2(game_id)
        df = pbp.get_data_frames()[0]
        
        if df.empty:
            return pd.DataFrame()
        
        # Map columns to our database schema
        result = pd.DataFrame({
            'game_id': game_id,
            'action_number': df['EVENTNUM'],
            'action_id': df.get('EVENTMSGACTIONTYPE', None),
            'period': df['PERIOD'],
            'clock': df['PCTIMESTRING'],
            'team_id': df.get('PLAYER1_TEAM_ID', None),
            'team_tricode': df.get('PLAYER1_TEAM_ABBREVIATION', None),
            'person_id': df.get('PLAYER1_ID', None),
            'player_name': df.get('PLAYER1_NAME', None),
            'player_name_i': None,  # Not available in stats API
            'x_legacy': df.get('HOMEDESCRIPTION', None),  # Repurpose for description
            'y_legacy': df.get('VISITORDESCRIPTION', None),  # Repurpose for description  
            'shot_distance': None,
            'shot_result': None,
            'is_field_goal': 0,
            'score_home': df.get('SCORE', '').apply(lambda x: x.split('-')[0] if isinstance(x, str) and '-' in x else None),
            'score_away': df.get('SCORE', '').apply(lambda x: x.split('-')[1] if isinstance(x, str) and '-' in x else None),
            'points_total': None,
            'location': df.get('HOMEDESCRIPTION', None).apply(lambda x: 'H' if pd.notna(x) else ('A' if pd.notna(df.get('VISITORDESCRIPTION')) else None)),
            'description': df['HOMEDESCRIPTION'].fillna('') + ' ' + df['VISITORDESCRIPTION'].fillna(''),
            'action_type': df['EVENTMSGTYPE'].astype(str),
            'sub_type': None,
            'shot_value': None,
            'video_available': 0
        })
        
        return result
        
    except Exception as e:
        print(f"    Error fetching PBP: {e}")
        return pd.DataFrame()


def insert_pbp_data(df, conn):
    """Insert play-by-play data into database"""
    
    cur = conn.cursor()
    
    insert_query = """
        INSERT INTO nba.nba_play_by_play (
            game_id, action_number, action_id, period, clock,
            team_id, team_tricode, person_id, player_name, player_name_i,
            x_legacy, y_legacy, shot_distance, shot_result, is_field_goal,
            score_home, score_away, points_total, location, description,
            action_type, sub_type, shot_value, video_available,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            NOW(), NOW()
        )
        ON CONFLICT (game_id, action_number) DO NOTHING
    """
    
    for _, row in df.iterrows():
        # Convert None/NaN to None, handle large integers
        def safe_int(val):
            if pd.isna(val) or val is None:
                return None
            try:
                v = int(val)
                # Check if it fits in PostgreSQL integer (32-bit)
                if v < -2147483648 or v > 2147483647:
                    return None
                return v
            except:
                return None
        
        def safe_str(val):
            if pd.isna(val) or val is None:
                return None
            return str(val)
        
        cur.execute(insert_query, (
            safe_str(row['game_id']), 
            safe_int(row['action_number']), 
            safe_int(row['action_id']), 
            safe_int(row['period']), 
            safe_str(row['clock']),
            safe_int(row['team_id']), 
            safe_str(row['team_tricode']), 
            safe_int(row['person_id']), 
            safe_str(row['player_name']), 
            safe_str(row['player_name_i']),
            safe_int(row['x_legacy']), 
            safe_int(row['y_legacy']), 
            safe_int(row['shot_distance']), 
            safe_str(row['shot_result']), 
            safe_int(row['is_field_goal']),
            safe_str(row['score_home']), 
            safe_str(row['score_away']), 
            safe_int(row['points_total']), 
            safe_str(row['location']), 
            safe_str(row['description']),
            safe_str(row['action_type']), 
            safe_str(row['sub_type']), 
            safe_int(row['shot_value']), 
            safe_int(row['video_available'])
        ))
    
    conn.commit()
    cur.close()


def main():
    print("="*80)
    print("ADD MISSING PLAY-BY-PLAY DATA TO DATABASE")
    print("="*80)
    
    # 1. Get games in Kalshi folder
    print("\n[1/4] Checking Kalshi folder...")
    kalshi_games = get_games_in_kalshi_folder()
    print(f"  Games in Kalshi folder: {len(kalshi_games)}")
    
    # 2. Get games in database
    print("\n[2/4] Checking database...")
    db_games = get_games_in_database()
    print(f"  Games in database: {len(db_games)}")
    
    # 3. Find missing games
    print("\n[3/4] Finding missing games...")
    missing_games = [g for g in kalshi_games if g not in db_games]
    print(f"  Missing games: {len(missing_games)}")
    
    if len(missing_games) == 0:
        print("\n[OK] All games already in database!")
        return
    
    # 4. Fetch and insert missing PBP data
    print("\n[4/4] Fetching and inserting PBP data...")
    print("="*80)
    
    conn = get_db_connection()
    success = 0
    failed = 0
    
    for idx, game_id in enumerate(missing_games, 1):
        print(f"\n[{idx}/{len(missing_games)}] Game {game_id}")
        
        # Fetch PBP data
        print(f"  Fetching from NBA API...")
        df = fetch_pbp_data(game_id)
        
        if df.empty:
            print(f"  [FAILED] No data available")
            failed += 1
            continue
        
        print(f"  Got {len(df)} actions")
        
        # Insert into database
        print(f"  Inserting into database...")
        try:
            insert_pbp_data(df, conn)
            print(f"  [SUCCESS] Inserted {len(df)} rows")
            success += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            failed += 1
        
        # Rate limit
        time.sleep(0.5)
    
    conn.close()
    
    # Summary
    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)
    print(f"Successfully added: {success} games")
    print(f"Failed: {failed} games")
    print(f"Total PBP games now: {len(db_games) + success}")
    print("="*80)


if __name__ == "__main__":
    main()

