"""Tradability and practical constraints - Area 11"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
from ..backtesting.fees import calculate_round_trip_cost, break_even_edge
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def estimate_slippage(df: pd.DataFrame, position_size: int = 100) -> pd.Series:
    """
    Estimate slippage based on typical volume.
    
    Args:
        df: Kalshi data with volume
        position_size: Number of contracts to trade
        
    Returns:
        Series with estimated slippage
    """
    logger.info(f"Estimating slippage for position size of {position_size} contracts...")
    
    # Simple model: slippage increases as position size relative to volume increases
    df = df.copy()
    df['volume_ratio'] = position_size / df['volume'].replace(0, np.nan)
    
    # Estimate slippage as percentage points (assume 0.1% per 10% of volume)
    df['estimated_slippage'] = np.minimum(df['volume_ratio'] * 0.1, 2.0)  # Cap at 2%
    
    return df['estimated_slippage']


def entry_exit_window_analysis(opportunities_df: pd.DataFrame) -> Dict:
    """
    Analyze how long identified edges persist.
    
    Args:
        opportunities_df: DataFrame with identified trading opportunities
        
    Returns:
        Dictionary with window statistics
    """
    logger.info("Analyzing entry/exit windows...")
    
    if 'duration' not in opportunities_df.columns:
        # Calculate duration if not present
        opportunities_df['duration'] = opportunities_df.groupby('game_id')['game_minute'].diff()
    
    results = {
        'mean_window': opportunities_df['duration'].mean(),
        'median_window': opportunities_df['duration'].median(),
        'percentiles': {
            'p25': opportunities_df['duration'].quantile(0.25),
            'p50': opportunities_df['duration'].quantile(0.50),
            'p75': opportunities_df['duration'].quantile(0.75),
            'p90': opportunities_df['duration'].quantile(0.90)
        },
        'short_windows': (opportunities_df['duration'] < 1).mean(),  # <1 minute
        'medium_windows': ((opportunities_df['duration'] >= 1) & (opportunities_df['duration'] < 3)).mean(),  # 1-3 min
        'long_windows': (opportunities_df['duration'] >= 3).mean()  # >3 min
    }
    
    return results


def fee_impact_by_price(prices: np.ndarray = np.arange(10, 91, 10)) -> pd.DataFrame:
    """
    Calculate break-even edge required at different price levels.
    
    Args:
        prices: Array of price levels to analyze
        
    Returns:
        DataFrame with fee impacts
    """
    logger.info("Calculating fee impact by price level...")
    
    results = []
    
    for price in prices:
        # Calculate round-trip cost
        round_trip = calculate_round_trip_cost(100, price, price)
        
        # Calculate break-even edge
        be_edge = break_even_edge(price, 100)
        
        # Max risk at this price
        max_risk = price * (100 - price) / 100
        
        results.append({
            'price': price,
            'round_trip_cost': round_trip,
            'break_even_edge_pct': be_edge,
            'max_risk_per_contract': max_risk,
            'fee_pct_of_risk': (round_trip / (max_risk * 100)) * 100 if max_risk > 0 else 0
        })
    
    return pd.DataFrame(results)


def optimal_position_sizing(edge: float, bankroll: float, 
                           kelly_fraction: float = 0.25) -> Dict:
    """
    Calculate optimal position size using Kelly criterion.
    
    Args:
        edge: Expected edge (decimal, e.g., 0.05 for 5%)
        bankroll: Total bankroll
        kelly_fraction: Fraction of Kelly to use (0.25 = quarter Kelly)
        
    Returns:
        Dictionary with position sizing recommendations
    """
    logger.info("Calculating optimal position sizing...")
    
    # Kelly formula: f* = (bp - q) / b
    # Where b = odds received, p = win probability, q = 1-p
    # For simplicity, assume even odds and calculate based on edge
    
    win_prob = 0.5 + edge / 2  # Approximate
    
    kelly_pct = edge  # Simplified Kelly
    adjusted_kelly = kelly_pct * kelly_fraction
    
    optimal_position = bankroll * adjusted_kelly
    
    results = {
        'edge': edge,
        'win_probability': win_prob,
        'full_kelly_pct': kelly_pct * 100,
        'adjusted_kelly_pct': adjusted_kelly * 100,
        'optimal_position_size': optimal_position,
        'contracts_at_50': int(optimal_position / 50),  # Assuming avg price of 50
        'max_loss_per_trade': optimal_position,
        'bankroll': bankroll,
        'kelly_fraction': kelly_fraction
    }
    
    # Risk of ruin estimates
    results['trades_to_double'] = int(np.log(2) / np.log(1 + adjusted_kelly)) if adjusted_kelly > 0 else np.inf
    
    return results


def win_rate_magnitude_tradeoff(strategies: List[Dict]) -> pd.DataFrame:
    """
    Compare strategies on win rate vs magnitude dimensions.
    
    Args:
        strategies: List of strategy performance dictionaries
        
    Returns:
        DataFrame comparing strategy profiles
    """
    logger.info("Analyzing win rate vs magnitude tradeoff...")
    
    comparison = []
    
    for strategy in strategies:
        name = strategy['name']
        trades = strategy.get('trades', [])
        
        if not trades:
            continue
        
        trades_df = pd.DataFrame(trades)
        
        wins = trades_df[trades_df['net_pl'] > 0]
        losses = trades_df[trades_df['net_pl'] <= 0]
        
        comparison.append({
            'strategy': name,
            'win_rate': len(wins) / len(trades_df),
            'avg_win': wins['net_pl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['net_pl'].mean() if len(losses) > 0 else 0,
            'total_trades': len(trades_df),
            'profit_factor': wins['net_pl'].sum() / abs(losses['net_pl'].sum()) if len(losses) > 0 else np.inf,
            'expected_value': trades_df['net_pl'].mean(),
            'sharpe_ratio': trades_df['net_pl'].mean() / trades_df['net_pl'].std() if trades_df['net_pl'].std() > 0 else 0
        })
    
    return pd.DataFrame(comparison)

