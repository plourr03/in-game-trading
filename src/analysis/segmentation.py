"""Segmentation analysis - Area 9"""
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from typing import Dict, List
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def segment_by_pregame_odds(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Segment games by pre-game odds (favorites, underdogs, toss-ups).
    
    Args:
        df: Game-level data with pre-game odds
        
    Returns:
        Dictionary mapping segment names to DataFrames
    """
    logger.info("Segmenting by pre-game odds...")
    
    # Get first price of each game as pre-game odds
    pregame = df.groupby('game_id').first()['close']
    
    segments = {}
    
    # Toss-ups: 45-55
    tossups = pregame[(pregame >= 45) & (pregame <= 55)].index
    segments['toss_ups'] = df[df['game_id'].isin(tossups)]
    
    # Favorites: > 60
    favorites = pregame[pregame > 60].index
    segments['favorites'] = df[df['game_id'].isin(favorites)]
    
    # Underdogs: < 40
    underdogs = pregame[pregame < 40].index
    segments['underdogs'] = df[df['game_id'].isin(underdogs)]
    
    logger.info(f"Segments: {len(tossups)} toss-ups, {len(favorites)} favorites, {len(underdogs)} underdogs")
    
    return segments


def segment_by_final_margin(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Segment by final margin (blowouts, close, overtime).
    
    Args:
        df: Game-level data with final scores
        
    Returns:
        Dictionary mapping segment names to DataFrames
    """
    logger.info("Segmenting by final margin...")
    
    # Get final scores for each game
    final_scores = df.groupby('game_id').last()[['score_home', 'score_away', 'period']]
    final_scores['margin'] = (final_scores['score_home'] - final_scores['score_away']).abs()
    
    segments = {}
    
    # Overtime games
    ot_games = final_scores[final_scores['period'] > 4].index
    segments['overtime'] = df[df['game_id'].isin(ot_games)]
    
    # Close games (margin <= 5, no OT)
    close_games = final_scores[(final_scores['margin'] <= 5) & (final_scores['period'] <= 4)].index
    segments['close'] = df[df['game_id'].isin(close_games)]
    
    # Moderate games (5 < margin <= 15)
    moderate_games = final_scores[(final_scores['margin'] > 5) & (final_scores['margin'] <= 15)].index
    segments['moderate'] = df[df['game_id'].isin(moderate_games)]
    
    # Blowouts (margin > 15)
    blowout_games = final_scores[final_scores['margin'] > 15].index
    segments['blowouts'] = df[df['game_id'].isin(blowout_games)]
    
    logger.info(f"Segments: {len(ot_games)} OT, {len(close_games)} close, {len(moderate_games)} moderate, {len(blowout_games)} blowouts")
    
    return segments


def segment_by_total_points(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Segment by total points scored (high vs low scoring).
    
    Args:
        df: Game-level data with final scores
        
    Returns:
        Dictionary mapping segment names to DataFrames
    """
    logger.info("Segmenting by total points...")
    
    # Get total points for each game
    final_scores = df.groupby('game_id').last()[['score_home', 'score_away']]
    final_scores['total_points'] = final_scores['score_home'] + final_scores['score_away']
    
    # Use quartiles
    q25 = final_scores['total_points'].quantile(0.25)
    q75 = final_scores['total_points'].quantile(0.75)
    
    segments = {}
    
    # Low scoring (bottom quartile)
    low_scoring = final_scores[final_scores['total_points'] <= q25].index
    segments['low_scoring'] = df[df['game_id'].isin(low_scoring)]
    
    # Average scoring (middle 50%)
    avg_scoring = final_scores[(final_scores['total_points'] > q25) & (final_scores['total_points'] < q75)].index
    segments['average_scoring'] = df[df['game_id'].isin(avg_scoring)]
    
    # High scoring (top quartile)
    high_scoring = final_scores[final_scores['total_points'] >= q75].index
    segments['high_scoring'] = df[df['game_id'].isin(high_scoring)]
    
    logger.info(f"Segments: {len(low_scoring)} low, {len(avg_scoring)} average, {len(high_scoring)} high scoring")
    
    return segments


def compare_segments(segments: Dict[str, pd.DataFrame], 
                    metric_func) -> pd.DataFrame:
    """
    Compare key metrics across segments.
    
    Args:
        segments: Dictionary of segmented DataFrames
        metric_func: Function to calculate metrics
        
    Returns:
        DataFrame comparing segments
    """
    logger.info("Comparing segments...")
    
    results = []
    
    for segment_name, segment_df in segments.items():
        if len(segment_df) > 0:
            metrics = metric_func(segment_df)
            metrics['segment'] = segment_name
            metrics['n_rows'] = len(segment_df)
            results.append(metrics)
    
    return pd.DataFrame(results)

