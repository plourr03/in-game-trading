"""Data quality validation"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from ..utils.helpers import get_logger
from ..utils.constants import MIN_VOLUME_COVERAGE

logger = get_logger(__name__)


def validate_game_outcome(kalshi_df: pd.DataFrame, pbp_df: pd.DataFrame) -> bool:
    """
    Verify that final Kalshi price matches final play-by-play score.
    
    Args:
        kalshi_df: Kalshi data for a game
        pbp_df: Play-by-play data for same game
        
    Returns:
        True if outcome matches, False otherwise
    """
    # Get final Kalshi price (should be near 0 or 100)
    final_price = kalshi_df.iloc[-1]['close']
    
    # Get final scores from PBP
    final_home = pbp_df['score_home'].iloc[-1]
    final_away = pbp_df['score_away'].iloc[-1]
    
    # Determine which team Kalshi probability is for
    is_home = kalshi_df.iloc[-1].get('is_home_team', True)
    
    # Check if price matches outcome
    if is_home:
        home_won = final_home > final_away
        price_indicates_home_won = final_price > 50
    else:
        home_won = final_away > final_home
        price_indicates_home_won = final_price > 50
    
    return home_won == price_indicates_home_won


def check_monotonic_scores(pbp_df: pd.DataFrame) -> bool:
    """
    Verify that scores never decrease in play-by-play data.
    
    Args:
        pbp_df: Play-by-play DataFrame
        
    Returns:
        True if scores are monotonic, False otherwise
    """
    # Check home score is non-decreasing
    home_decreases = (pbp_df['score_home'].diff() < 0).sum()
    
    # Check away score is non-decreasing
    away_decreases = (pbp_df['score_away'].diff() < 0).sum()
    
    if home_decreases > 0 or away_decreases > 0:
        logger.warning(f"Non-monotonic scores found: {home_decreases} home, {away_decreases} away")
        return False
    
    return True


def detect_missing_minutes(kalshi_df: pd.DataFrame) -> List[int]:
    """
    Identify which game minutes have missing data.
    
    Args:
        kalshi_df: Kalshi candlestick data
        
    Returns:
        List of missing minute indices
    """
    if 'game_minute' not in kalshi_df.columns:
        logger.warning("game_minute column not found")
        return []
    
    # Get all minutes that should exist
    expected_minutes = set(range(int(kalshi_df['game_minute'].min()), 
                                 int(kalshi_df['game_minute'].max()) + 1))
    
    # Get actual minutes
    actual_minutes = set(kalshi_df['game_minute'].unique())
    
    # Find missing
    missing = sorted(expected_minutes - actual_minutes)
    
    if missing:
        logger.info(f"Found {len(missing)} missing minutes")
    
    return missing


def volume_coverage_report(kalshi_df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate percentage of minutes with non-zero volume.
    
    Args:
        kalshi_df: Kalshi candlestick data
        
    Returns:
        Dictionary with coverage statistics
    """
    total_rows = len(kalshi_df)
    non_zero_volume = (kalshi_df['volume'] > 0).sum()
    
    coverage = non_zero_volume / total_rows if total_rows > 0 else 0
    
    # Calculate by game if game_id present
    coverage_by_game = {}
    if 'game_id' in kalshi_df.columns:
        coverage_by_game = kalshi_df.groupby('game_id').apply(
            lambda g: (g['volume'] > 0).sum() / len(g)
        ).to_dict()
    
    return {
        'overall_coverage': coverage,
        'total_rows': total_rows,
        'rows_with_volume': int(non_zero_volume),
        'meets_threshold': coverage >= MIN_VOLUME_COVERAGE,
        'by_game': coverage_by_game
    }


def timestamp_sanity_checks(df: pd.DataFrame) -> Dict[str, bool]:
    """
    Verify minute progression is logical and timestamps are valid.
    
    Args:
        df: DataFrame with timestamp/datetime columns
        
    Returns:
        Dictionary of validation results
    """
    results = {
        'has_timestamps': 'timestamp' in df.columns,
        'has_datetime': 'datetime' in df.columns,
        'timestamps_increasing': False,
        'no_duplicates': False,
        'valid_range': False
    }
    
    if 'timestamp' in df.columns:
        # Check timestamps are increasing
        results['timestamps_increasing'] = (df['timestamp'].diff().dropna() >= 0).all()
        
        # Check for duplicates
        results['no_duplicates'] = not df['timestamp'].duplicated().any()
        
        # Check timestamps are in valid range (not too far in past/future)
        min_ts = df['timestamp'].min()
        max_ts = df['timestamp'].max()
        results['valid_range'] = (min_ts > 1000000000) and (max_ts < 2000000000)
    
    return results

