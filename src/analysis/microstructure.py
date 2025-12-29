"""Market microstructure analysis - Area 2"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def calculate_spread_proxy(df: pd.DataFrame) -> pd.Series:
    """
    Use high-low within candles as proxy for bid-ask spread.
    
    Args:
        df: Kalshi data with high/low columns
        
    Returns:
        Series with spread estimates
    """
    logger.info("Calculating spread proxy...")
    
    spread = df['high'] - df['low']
    
    logger.info(f"Mean spread: {spread.mean():.2f}, Median: {spread.median():.2f}")
    
    return spread


def analyze_volume_patterns(df: pd.DataFrame) -> Dict:
    """
    Analyze volume by game minute, score differential, quarter.
    
    Args:
        df: Merged data with volume and game state
        
    Returns:
        Dictionary with volume statistics
    """
    logger.info("Analyzing volume patterns...")
    
    results = {
        'overall_stats': {
            'mean_volume': df['volume'].mean(),
            'median_volume': df['volume'].median(),
            'total_volume': df['volume'].sum(),
            'pct_with_volume': (df['volume'] > 0).mean()
        },
        'by_period': df.groupby('period')['volume'].agg(['mean', 'median', 'sum']).to_dict(),
        'by_game_minute': df.groupby(pd.cut(df['game_minute'], bins=10))['volume'].mean().to_dict()
    }
    
    # Volume by score differential if available
    if 'score_differential' in df.columns:
        df['score_diff_abs'] = df['score_differential'].abs()
        results['by_score_diff'] = df.groupby(pd.cut(df['score_diff_abs'], bins=[0, 5, 10, 15, 100]))['volume'].mean().to_dict()
    
    return results


def liquidity_by_game_state(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare volume/liquidity in close games vs blowouts.
    
    Args:
        df: Merged data
        
    Returns:
        DataFrame with liquidity by game state
    """
    logger.info("Analyzing liquidity by game state...")
    
    # Define close games vs blowouts
    if 'score_differential' not in df.columns:
        df['score_differential'] = df['score_home'] - df['score_away']
    
    df['game_type'] = pd.cut(
        df['score_differential'].abs(),
        bins=[0, 5, 10, 15, 100],
        labels=['very_close', 'close', 'moderate', 'blowout']
    )
    
    # Aggregate by game type
    liquidity = df.groupby('game_type').agg({
        'volume': ['mean', 'median', 'sum', 'count'],
        'high': 'mean',
        'low': 'mean'
    })
    
    liquidity['spread'] = liquidity[('high', 'mean')] - liquidity[('low', 'mean')]
    
    return liquidity


def price_discovery_time(df: pd.DataFrame) -> float:
    """
    Calculate minutes until price stabilizes after game start.
    
    Args:
        df: Kalshi data
        
    Returns:
        Average minutes to stabilization
    """
    logger.info("Calculating price discovery time...")
    
    stabilization_times = []
    
    for game_id in df['game_id'].unique():
        game = df[df['game_id'] == game_id].sort_values('game_minute')
        
        if len(game) < 10:
            continue
        
        # Calculate rolling volatility
        game['price_change'] = game['close'].diff().abs()
        game['rolling_vol'] = game['price_change'].rolling(window=5).std()
        
        # Find when volatility drops below threshold
        threshold = game['rolling_vol'].median() * 0.5
        stabilized = game[game['rolling_vol'] < threshold]
        
        if len(stabilized) > 0:
            stabilization_times.append(stabilized.iloc[0]['game_minute'])
    
    if stabilization_times:
        mean_time = np.mean(stabilization_times)
        logger.info(f"Average stabilization time: {mean_time:.1f} minutes")
        return mean_time
    
    return np.nan


def identify_dead_periods(df: pd.DataFrame) -> Dict:
    """
    Identify systematic periods of no trading (halftime, quarter breaks).
    
    Args:
        df: Kalshi data
        
    Returns:
        Dictionary mapping periods to dead minute ranges
    """
    logger.info("Identifying dead periods...")
    
    # Calculate volume by minute across all games
    avg_volume_by_minute = df.groupby('game_minute')['volume'].mean()
    
    # Find minutes with very low volume
    low_volume_threshold = avg_volume_by_minute.quantile(0.1)
    dead_minutes = avg_volume_by_minute[avg_volume_by_minute < low_volume_threshold].index.tolist()
    
    # Identify typical break times
    dead_periods = {
        'halftime': [minute for minute in dead_minutes if 23 <= minute <= 26],  # Around minute 24
        'q1_q2_break': [minute for minute in dead_minutes if 11 <= minute <= 13],
        'q3_q4_break': [minute for minute in dead_minutes if 35 <= minute <= 37],
        'all_dead_minutes': dead_minutes
    }
    
    logger.info(f"Found {len(dead_minutes)} low-volume minutes")
    
    return dead_periods

