"""Time alignment between Kalshi and play-by-play data"""
import pandas as pd
import numpy as np
from typing import Optional
from .preprocessor import calculate_game_minute
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def align_pbp_to_minutes(pbp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Map each play-by-play event to its corresponding game minute.
    
    Args:
        pbp_df: Play-by-play DataFrame
        
    Returns:
        DataFrame with game_minute column added
    """
    logger.info("Aligning play-by-play to game minutes...")
    
    pbp_df = pbp_df.copy()
    
    # Calculate game minute for each event
    pbp_df['game_minute'] = pbp_df.apply(
        lambda row: calculate_game_minute(row['period'], row['clock']),
        axis=1
    )
    
    # Round to nearest minute for alignment
    pbp_df['game_minute_rounded'] = pbp_df['game_minute'].round().astype(int)
    
    logger.info(f"Aligned {len(pbp_df)} events to game minutes")
    return pbp_df


def merge_kalshi_pbp(kalshi_df: pd.DataFrame, pbp_df: pd.DataFrame, 
                     game_id: int) -> pd.DataFrame:
    """
    Align and merge Kalshi and play-by-play data by game minute.
    
    Args:
        kalshi_df: Kalshi candlestick data
        pbp_df: Play-by-play data with game_minute
        game_id: Game ID to merge
        
    Returns:
        Merged DataFrame
    """
    logger.info(f"Merging Kalshi and PBP data for game {game_id}...")
    
    # Filter to specific game
    kalshi_game = kalshi_df[kalshi_df['game_id'] == game_id].copy()
    pbp_game = pbp_df[pbp_df['game_id'] == game_id].copy()
    
    # Kalshi datetime already represents game minutes (0, 1, 2, ...)
    # Extract minute from datetime
    if 'datetime' in kalshi_game.columns:
        # Get the minute offset from the first timestamp
        kalshi_game = kalshi_game.sort_values('datetime')
        first_timestamp = kalshi_game['datetime'].iloc[0]
        kalshi_game['game_minute'] = (
            (pd.to_datetime(kalshi_game['datetime']) - pd.to_datetime(first_timestamp))
            .dt.total_seconds() / 60
        ).astype(int)
    
    # Aggregate play-by-play to minute level
    # Count events and scoring by minute
    pbp_agg = pbp_game.groupby('game_minute_rounded').agg({
        'action_number': 'count',
        'score_home': 'last',
        'score_away': 'last',
        'points_total': 'last'
    }).rename(columns={'action_number': 'events_count'})
    
    # Merge on game minute
    merged = kalshi_game.merge(
        pbp_agg,
        left_on='game_minute',
        right_index=True,
        how='left'
    )
    
    # Also include raw events for detailed analysis
    merged = merged.merge(
        pbp_game[['game_minute_rounded', 'action_type', 'sub_type', 'location', 'shot_value', 'shot_result']],
        left_on='game_minute',
        right_on='game_minute_rounded',
        how='left',
        suffixes=('', '_event')
    )
    
    logger.info(f"Merged {len(merged)} rows for game {game_id}")
    return merged


def handle_overtime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle special processing for overtime periods (period > 4).
    
    Args:
        df: DataFrame with period column
        
    Returns:
        DataFrame with overtime properly handled
    """
    logger.info("Processing overtime periods...")
    
    df = df.copy()
    
    # Add overtime indicator
    df['is_overtime'] = df['period'] > 4
    
    # Calculate OT period number (1st OT, 2nd OT, etc.)
    df['overtime_number'] = np.where(df['is_overtime'], df['period'] - 4, 0)
    
    logger.info(f"Found {df['is_overtime'].sum()} overtime events")
    return df

