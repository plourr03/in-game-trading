"""Price reaction analysis - Area 3"""
import pandas as pd
import numpy as np
from typing import List, Dict
from scipy import stats
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def price_change_after_event(df: pd.DataFrame, event_type: str, 
                             lags: List[int] = [0, 1, 2, 3]) -> pd.DataFrame:
    """
    Calculate price change at various lags after specific event types.
    
    Args:
        df: Merged data with events and prices
        event_type: Type of event to analyze
        lags: Minutes after event to measure price change
        
    Returns:
        DataFrame with price changes by lag
    """
    logger.info(f"Analyzing price reactions to {event_type} events...")
    
    # Filter to specific event type
    events = df[df['action_type'] == event_type].copy()
    
    if len(events) == 0:
        logger.warning(f"No events of type {event_type} found")
        return pd.DataFrame()
    
    # Calculate price changes at each lag
    for lag in lags:
        events[f'price_change_lag_{lag}'] = (
            df.loc[events.index, 'close'].shift(-lag) - events['close']
        )
    
    # Calculate statistics
    results = []
    for lag in lags:
        col = f'price_change_lag_{lag}'
        results.append({
            'lag': lag,
            'mean_change': events[col].mean(),
            'median_change': events[col].median(),
            'std': events[col].std(),
            'count': events[col].notna().sum(),
            't_stat': stats.ttest_1samp(events[col].dropna(), 0)[0],
            'p_value': stats.ttest_1samp(events[col].dropna(), 0)[1]
        })
    
    return pd.DataFrame(results)


def reaction_by_point_value(df: pd.DataFrame) -> Dict:
    """
    Compare price reactions to 2pt vs 3pt vs free throw scoring.
    
    Args:
        df: Merged data
        
    Returns:
        Dictionary with reaction statistics by point value
    """
    logger.info("Analyzing reactions by point value...")
    
    # Filter to scoring events
    scoring = df[df['action_type'] == 'Made Shot'].copy()
    
    # Calculate immediate price change
    scoring['price_change'] = scoring.groupby('game_id')['close'].diff()
    
    # Group by shot value
    results = {}
    for shot_value in [1, 2, 3]:
        shots = scoring[scoring['shot_value'] == shot_value]
        if len(shots) > 0:
            results[f'{shot_value}pt'] = {
                'mean_reaction': shots['price_change'].mean(),
                'median_reaction': shots['price_change'].median(),
                'std': shots['price_change'].std(),
                'count': len(shots),
                'reaction_per_point': shots['price_change'].mean() / shot_value
            }
    
    return results


def reaction_by_game_state(df: pd.DataFrame, score_diff_buckets: List[int] = [-20, -10, -5, 0, 5, 10, 20],
                          time_buckets: List[int] = [0, 12, 24, 36, 48]) -> pd.DataFrame:
    """
    Analyze how reactions vary by score differential and time remaining.
    
    Args:
        df: Merged data
        score_diff_buckets: Bucket edges for score differential
        time_buckets: Bucket edges for time remaining
        
    Returns:
        DataFrame with reactions by game state
    """
    logger.info("Analyzing reactions by game state...")
    
    # Calculate score differential and time remaining if not present
    if 'score_differential' not in df.columns:
        df['score_differential'] = df['score_home'] - df['score_away']
    
    if 'time_remaining' not in df.columns:
        df['time_remaining'] = 48 - df['game_minute']
    
    # Calculate price changes
    df['price_change'] = df.groupby('game_id')['close'].diff()
    
    # Create bins
    df['score_diff_bin'] = pd.cut(df['score_differential'], bins=score_diff_buckets)
    df['time_bin'] = pd.cut(df['time_remaining'], bins=time_buckets)
    
    # Group and aggregate
    results = df.groupby(['score_diff_bin', 'time_bin']).agg({
        'price_change': ['mean', 'std', 'count']
    }).reset_index()
    
    return results


def cumulative_scoring_effect(df: pd.DataFrame) -> pd.DataFrame:
    """
    Test if 5th consecutive basket has different impact than 1st.
    
    Args:
        df: Merged data with run information
        
    Returns:
        DataFrame showing price impact vs position in run
    """
    logger.info("Analyzing cumulative scoring effects...")
    
    # Identify consecutive scoring
    scoring = df[df['action_type'] == 'Made Shot'].copy()
    scoring['price_change'] = scoring.groupby('game_id')['close'].diff()
    
    # Track position in run
    scoring['same_team'] = (scoring['location'] == scoring['location'].shift(1))
    scoring['run_position'] = scoring.groupby('game_id')['same_team'].cumsum() + 1
    scoring.loc[~scoring['same_team'], 'run_position'] = 1
    
    # Group by position in run
    results = scoring.groupby('run_position').agg({
        'price_change': ['mean', 'std', 'count']
    }).reset_index()
    
    return results


def overreaction_detection(df: pd.DataFrame, threshold: float = 5.0) -> Dict:
    """
    Detect price overreactions followed by reversals.
    
    Args:
        df: Kalshi data
        threshold: Minimum price move to consider (percentage points)
        
    Returns:
        Dictionary with overreaction statistics
    """
    logger.info(f"Detecting overreactions (threshold: {threshold}%)...")
    
    # Calculate price changes
    df = df.copy()
    df['price_change'] = df.groupby('game_id')['close'].diff()
    df['next_change'] = df.groupby('game_id')['price_change'].shift(-1)
    df['next_2_change'] = df.groupby('game_id')['price_change'].shift(-2)
    df['next_3_change'] = df.groupby('game_id')['price_change'].shift(-3)
    
    # Identify large moves
    large_moves = df[df['price_change'].abs() > threshold].copy()
    
    # Check for reversals
    large_moves['reversal_1min'] = (
        (large_moves['price_change'] > 0) & (large_moves['next_change'] < 0) |
        (large_moves['price_change'] < 0) & (large_moves['next_change'] > 0)
    )
    
    large_moves['reversal_3min'] = (
        (large_moves['price_change'] > 0) & 
        ((large_moves['next_change'] + large_moves['next_2_change'] + large_moves['next_3_change']) < 0) |
        (large_moves['price_change'] < 0) & 
        ((large_moves['next_change'] + large_moves['next_2_change'] + large_moves['next_3_change']) > 0)
    )
    
    results = {
        'total_large_moves': len(large_moves),
        'reversal_rate_1min': large_moves['reversal_1min'].mean(),
        'reversal_rate_3min': large_moves['reversal_3min'].mean(),
        'mean_move_size': large_moves['price_change'].abs().mean(),
        'mean_reversal_size_1min': large_moves['next_change'].abs().mean(),
        'mean_reversal_size_3min': (
            large_moves[['next_change', 'next_2_change', 'next_3_change']].sum(axis=1).abs().mean()
        )
    }
    
    return results

