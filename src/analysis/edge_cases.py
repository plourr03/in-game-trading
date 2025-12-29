"""Edge case and anomaly analysis - Area 10"""
import pandas as pd
import numpy as np
from typing import Dict, List
from scipy import stats
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def detect_garbage_time(df: pd.DataFrame, score_threshold: int = 20,
                       time_threshold: float = 5.0) -> pd.DataFrame:
    """
    Identify garbage time situations (big lead, little time left).
    
    Args:
        df: Merged data
        score_threshold: Minimum score differential
        time_threshold: Maximum time remaining (minutes)
        
    Returns:
        DataFrame with garbage time periods
    """
    logger.info("Detecting garbage time...")
    
    # Calculate score differential and time remaining
    if 'score_differential' not in df.columns:
        df['score_differential'] = df['score_home'] - df['score_away']
    
    if 'time_remaining' not in df.columns:
        df['time_remaining'] = 48 - df['game_minute']
    
    # Identify garbage time
    garbage_time = df[
        (df['score_differential'].abs() > score_threshold) &
        (df['time_remaining'] < time_threshold)
    ].copy()
    
    logger.info(f"Found {len(garbage_time)} garbage time minutes")
    
    return garbage_time


def overtime_analysis(df: pd.DataFrame) -> Dict:
    """
    Analyze different dynamics in overtime periods.
    
    Args:
        df: Merged data including OT games
        
    Returns:
        Dictionary with OT statistics
    """
    logger.info("Analyzing overtime games...")
    
    # Filter to OT periods
    ot_data = df[df['period'] > 4].copy()
    reg_data = df[df['period'] <= 4].copy()
    
    if len(ot_data) == 0:
        logger.warning("No overtime data found")
        return {}
    
    results = {
        'ot_games': ot_data['game_id'].nunique(),
        'total_games': df['game_id'].nunique(),
        'ot_rate': ot_data['game_id'].nunique() / df['game_id'].nunique(),
        'ot_stats': {},
        'regulation_stats': {}
    }
    
    # Calculate price volatility
    ot_data['price_change'] = ot_data.groupby('game_id')['close'].diff()
    reg_data['price_change'] = reg_data.groupby('game_id')['close'].diff()
    
    results['ot_stats']['mean_volatility'] = ot_data['price_change'].abs().mean()
    results['ot_stats']['volume'] = ot_data['volume'].mean()
    
    results['regulation_stats']['mean_volatility'] = reg_data['price_change'].abs().mean()
    results['regulation_stats']['volume'] = reg_data['volume'].mean()
    
    # Compare OT vs regulation
    results['ot_vs_reg'] = {
        'volatility_ratio': results['ot_stats']['mean_volatility'] / results['regulation_stats']['mean_volatility'],
        'volume_ratio': results['ot_stats']['volume'] / results['regulation_stats']['volume']
    }
    
    return results


def comeback_games(df: pd.DataFrame, deficit_threshold: int = 15) -> List[Dict]:
    """
    Identify games where team was down 15+ and won.
    
    Args:
        df: Game-level data
        deficit_threshold: Minimum deficit to consider
        
    Returns:
        List of comeback game details with price evolution
    """
    logger.info(f"Identifying comeback games (deficit >= {deficit_threshold})...")
    
    comebacks = []
    
    for game_id in df['game_id'].unique():
        game = df[df['game_id'] == game_id].sort_values('game_minute')
        
        if len(game) < 10:
            continue
        
        # Calculate score differential throughout game
        if 'score_differential' not in game.columns:
            game['score_differential'] = game['score_home'] - game['score_away']
        
        # Find maximum deficit
        max_deficit = game['score_differential'].min()
        
        # Check if team came back to win
        final_diff = game['score_differential'].iloc[-1]
        
        if max_deficit < -deficit_threshold and final_diff > 0:
            # Comeback win!
            comeback_point = game[game['score_differential'] == max_deficit].iloc[0]
            
            comebacks.append({
                'game_id': game_id,
                'max_deficit': max_deficit,
                'deficit_minute': comeback_point['game_minute'],
                'final_margin': final_diff,
                'price_at_deficit': comeback_point['close'],
                'final_price': game['close'].iloc[-1],
                'price_change': game['close'].iloc[-1] - comeback_point['close']
            })
    
    logger.info(f"Found {len(comebacks)} comeback games")
    
    return comebacks


def detect_anomalous_price_moves(df: pd.DataFrame, 
                                z_threshold: float = 3.0) -> pd.DataFrame:
    """
    Flag unusual price movements using statistical outlier detection.
    
    Args:
        df: Kalshi data
        z_threshold: Z-score threshold for anomaly
        
    Returns:
        DataFrame with anomalous periods
    """
    logger.info(f"Detecting anomalous price moves (z > {z_threshold})...")
    
    df = df.copy()
    df['price_change'] = df.groupby('game_id')['close'].diff()
    
    # Calculate z-scores
    mean_change = df['price_change'].mean()
    std_change = df['price_change'].std()
    
    df['z_score'] = (df['price_change'] - mean_change) / std_change
    
    # Flag anomalies
    anomalies = df[df['z_score'].abs() > z_threshold].copy()
    
    logger.info(f"Found {len(anomalies)} anomalous price movements")
    
    return anomalies

