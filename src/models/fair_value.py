"""Fair value calculation and comparison"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from typing import Dict
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def calculate_fair_value(df: pd.DataFrame, model: LogisticRegression) -> pd.Series:
    """
    Calculate theoretical fair value using win probability model.
    
    Args:
        df: Data with features
        model: Fitted win probability model
        
    Returns:
        Series with fair value estimates (0-100 scale)
    """
    logger.info("Calculating fair values...")
    
    # Prepare features (must match training features)
    X = df[['score_differential', 'time_remaining']].copy()
    X['interaction'] = X['score_differential'] * X['time_remaining']
    
    # Predict probabilities
    probabilities = model.predict_proba(X)[:, 1]
    
    # Convert to 0-100 scale (like Kalshi prices)
    fair_values = probabilities * 100
    
    return pd.Series(fair_values, index=df.index, name='fair_value')


def compare_to_market(df: pd.DataFrame, fair_value: pd.Series,
                     market_price: pd.Series) -> pd.DataFrame:
    """
    Compare theoretical fair value to actual market prices.
    
    Args:
        df: Game data
        fair_value: Theoretical fair values
        market_price: Actual Kalshi prices
        
    Returns:
        DataFrame with divergence analysis
    """
    logger.info("Comparing fair value to market prices...")
    
    comparison = pd.DataFrame({
        'fair_value': fair_value,
        'market_price': market_price,
        'divergence': market_price - fair_value,
        'abs_divergence': (market_price - fair_value).abs(),
        'pct_divergence': ((market_price - fair_value) / fair_value * 100)
    })
    
    # Calculate statistics
    stats = {
        'mean_divergence': comparison['divergence'].mean(),
        'median_divergence': comparison['divergence'].median(),
        'std_divergence': comparison['divergence'].std(),
        'mean_abs_divergence': comparison['abs_divergence'].mean(),
        'large_divergences': (comparison['abs_divergence'] > 5).sum(),  # >5% off
        'market_overprices': (comparison['divergence'] > 0).mean(),  # % of time market too high
        'market_underprices': (comparison['divergence'] < 0).mean(),  # % of time market too low
    }
    
    logger.info(f"Mean divergence: {stats['mean_divergence']:.2f}%")
    logger.info(f"Mean absolute divergence: {stats['mean_abs_divergence']:.2f}%")
    
    comparison.attrs['stats'] = stats
    
    return comparison

