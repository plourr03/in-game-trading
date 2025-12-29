"""Data loader for Kalshi CSVs and PostgreSQL play-by-play data"""
import pandas as pd
import psycopg2
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def load_kalshi_games(data_dir: str = "kalshi_data/jan_dec_2025_games") -> pd.DataFrame:
    """
    Load all Kalshi candlestick CSV files and concatenate into single DataFrame.
    
    Args:
        data_dir: Directory containing Kalshi CSV files
        
    Returns:
        DataFrame with all games concatenated
    """
    logger.info(f"Loading Kalshi data from {data_dir}...")
    
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    csv_files = list(data_path.glob("*.csv"))
    logger.info(f"Found {len(csv_files)} CSV files")
    
    if len(csv_files) == 0:
        raise ValueError(f"No CSV files found in {data_dir}")
    
    dfs = []
    for csv_file in tqdm(csv_files, desc="Loading CSVs"):
        try:
            # Extract metadata from filename
            metadata = get_game_metadata(csv_file.name)
            
            # Load CSV
            df = pd.read_csv(csv_file)
            
            # Add metadata columns
            df['away_team'] = metadata['away_team']
            df['home_team'] = metadata['home_team']
            df['game_date'] = metadata['date']
            
            dfs.append(df)
            
        except Exception as e:
            logger.warning(f"Error loading {csv_file.name}: {e}")
            continue
    
    if len(dfs) == 0:
        raise ValueError("No valid CSV files could be loaded")
    
    # Concatenate all games
    logger.info("Concatenating all games...")
    all_games = pd.concat(dfs, ignore_index=True)
    
    # Convert game_id to string and add '00' prefix for database matching
    # e.g., 22500001 -> '0022500001', 42400101 -> '0042400101'
    all_games['game_id'] = all_games['game_id'].astype(str).str.zfill(10)
    
    logger.info(f"Loaded {len(all_games)} rows from {len(dfs)} games")
    
    return all_games


def connect_to_pbp_db(host: str, port: int, database: str, 
                      user: str, password: str) -> psycopg2.extensions.connection:
    """
    Connect to PostgreSQL database containing play-by-play data.
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Username
        password: Password
        
    Returns:
        Database connection
    """
    logger.info(f"Connecting to PostgreSQL database at {host}:{port}/{database}...")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        logger.info("Database connection successful")
        return conn
    
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


def load_pbp_data(game_ids: List[int], conn: psycopg2.extensions.connection) -> pd.DataFrame:
    """
    Load play-by-play data for specific game IDs from database.
    
    Args:
        game_ids: List of game IDs to load
        conn: Database connection
        
    Returns:
        DataFrame with play-by-play data
    """
    logger.info(f"Loading play-by-play data for {len(game_ids)} games...")
    
    if len(game_ids) == 0:
        raise ValueError("No game IDs provided")
    
    # Create SQL query with IN clause - cast to VARCHAR for compatibility
    game_ids_str = ','.join(f"'{gid}'" for gid in game_ids)  # Wrap in quotes for VARCHAR
    query = f"""
        SELECT * 
        FROM nba.nba_play_by_play 
        WHERE game_id IN ({game_ids_str})
        ORDER BY game_id, action_number
    """
    
    try:
        df = pd.read_sql(query, conn)
        logger.info(f"Loaded {len(df)} play-by-play events")
        return df
    
    except Exception as e:
        logger.error(f"Error loading play-by-play data: {e}")
        raise


def get_game_metadata(filename: str) -> Dict[str, str]:
    """
    Extract metadata from Kalshi CSV filename.
    
    Args:
        filename: Kalshi CSV filename (e.g., '22500310_CLE_at_IND_2025-12-01_candles.csv')
        
    Returns:
        Dictionary with game_id, away_team, home_team, date
    """
    # Remove .csv extension
    name = filename.replace('_candles.csv', '')
    
    # Split by underscore
    parts = name.split('_')
    
    if len(parts) < 5:
        raise ValueError(f"Invalid filename format: {filename}")
    
    # Game ID needs '00' prefix for database matching
    # e.g., '22500310' -> '0022500310', '42400101' -> '0042400101'
    # Keep as STRING to preserve leading zeros!
    game_id_str = parts[0]
    if not game_id_str.startswith('00'):
        game_id_str = '00' + game_id_str
    game_id = game_id_str  # Keep as string!
    away_team = parts[1]
    # Skip 'at'
    home_team = parts[3]
    date = parts[4]
    
    return {
        'game_id': game_id,
        'away_team': away_team,
        'home_team': home_team,
        'date': date
    }

