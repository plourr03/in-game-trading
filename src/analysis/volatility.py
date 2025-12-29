"""Volatility analysis - Area 7"""
import pandas as pd
import numpy as np
from typing import Dict
from scipy import stats
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def volatility_by_minute(df: pd.DataFrame) -> pd.Series:
    """
    Calculate standard deviation of price changes by game minute.
    
    Args:
        df: Kalshi data with prices
        
    Returns:
        Series with volatility by minute
    """
    logger.info("Calculating volatility by game minute...")
    
    # Calculate price changes
    df = df.copy()
    df['price_change'] = df.groupby('game_id')['close'].diff()
    
    # Group by minute and calculate volatility
    volatility = df.groupby('game_minute')['price_change'].std()
    
    return volatility


def volatility_by_score_diff(df: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    """
    Analyze volatility by score differential (close games more volatile).
    
    Args:
        df: Merged data
        bins: Number of score differential bins
        
    Returns:
        DataFrame with volatility by score diff
    """
    logger.info("Analyzing volatility by score differential...")
    
    df = df.copy()
    df['price_change'] = df.groupby('game_id')['close'].diff()
    
    # Calculate score differential if not present
    if 'score_differential' not in df.columns:
        df['score_differential'] = df['score_home'] - df['score_away']
    
    # Use absolute score differential
    df['score_diff_abs'] = df['score_differential'].abs()
    
    # Create bins
    df['score_diff_bin'] = pd.cut(df['score_diff_abs'], bins=bins)
    
    # Calculate volatility by bin
    volatility = df.groupby('score_diff_bin').agg({
        'price_change': ['std', 'mean', 'count']
    }).reset_index()
    
    volatility.columns = ['score_diff_bin', 'volatility', 'mean_change', 'count']
    
    return volatility


def volatility_clustering(df: pd.DataFrame, lags: int = 5) -> Dict:
    """
    Test for GARCH-like volatility clustering.
    
    Args:
        df: Kalshi data
        lags: Number of lags to test
        
    Returns:
        Dictionary with autocorrelation results
    """
    logger.info("Testing for volatility clustering...")
    
    df = df.copy()
    df['price_change'] = df.groupby('game_id')['close'].diff()
    df['abs_price_change'] = df['price_change'].abs()
    
    results = {}
    
    for lag in range(1, lags + 1):
        df[f'lag_{lag}_abs'] = df.groupby('game_id')['abs_price_change'].shift(lag)
        
        # Calculate correlation of absolute price changes
        valid_data = df[['abs_price_change', f'lag_{lag}_abs']].dropna()
        
        if len(valid_data) > 0:
            corr, p_value = stats.pearsonr(
                valid_data['abs_price_change'],
                valid_data[f'lag_{lag}_abs']
            )
            
            results[f'lag_{lag}'] = {
                'correlation': corr,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'clustering': corr > 0.1  # Positive correlation = clustering
            }
    
    return results


def event_driven_volatility(merged_df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify which play types cause largest price movements.
    
    Args:
        merged_df: Merged data with events and prices
        
    Returns:
        DataFrame ranking events by price impact
    """
    logger.info("Analyzing event-driven volatility...")
    
    merged_df = merged_df.copy()
    merged_df['price_change'] = merged_df.groupby('game_id')['close'].diff()
    merged_df['abs_price_change'] = merged_df['price_change'].abs()
    
    # Group by action type
    event_volatility = merged_df.groupby('action_type').agg({
        'abs_price_change': ['mean', 'std', 'max', 'count']
    }).reset_index()
    
    event_volatility.columns = ['action_type', 'mean_impact', 'std_impact', 'max_impact', 'count']
    
    # Sort by mean impact
    event_volatility = event_volatility.sort_values('mean_impact', ascending=False)
    
    # Also analyze by shot value
    shot_volatility = merged_df[merged_df['shot_value'].notna()].groupby('shot_value').agg({
        'abs_price_change': ['mean', 'std', 'count']
    }).reset_index()
    
    shot_volatility.columns = ['shot_value', 'mean_impact', 'std_impact', 'count']
    
    return {
        'by_action_type': event_volatility,
        'by_shot_value': shot_volatility
    }

