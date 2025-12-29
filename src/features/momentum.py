"""Momentum and run detection features"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from .events import extract_scoring_events


def detect_runs(pbp_df: pd.DataFrame, min_points: int = 6) -> pd.DataFrame:
    """
    Identify scoring runs (e.g., 6-0, 8-0, 10-0 runs).
    
    Args:
        pbp_df: Play-by-play DataFrame with scoring events
        min_points: Minimum points for a run to be counted
        
    Returns:
        DataFrame with run information (start, end, team, points)
    """
    # Get scoring events only
    scoring = extract_scoring_events(pbp_df)
    
    if len(scoring) == 0:
        return pd.DataFrame(columns=['game_id', 'start_minute', 'end_minute', 'team', 'points', 'opponent_points'])
    
    # Sort by game minute
    scoring = scoring.sort_values('game_minute').reset_index(drop=True)
    
    runs = []
    
    # Track current run
    current_team = None
    run_points = 0
    run_start = None
    
    for idx, row in scoring.iterrows():
        scoring_team = row['location']  # 'h' or 'v'
        points = row.get('shot_value', 1)  # 1 for FT, 2 or 3 for shots
        
        if scoring_team == current_team:
            # Continue current run
            run_points += points
        else:
            # Check if previous run meets threshold
            if run_points >= min_points:
                runs.append({
                    'game_id': row['game_id'],
                    'start_minute': run_start,
                    'end_minute': scoring.iloc[idx-1]['game_minute'],
                    'team': current_team,
                    'points': run_points,
                    'opponent_points': 0
                })
            
            # Start new run
            current_team = scoring_team
            run_points = points
            run_start = row['game_minute']
    
    # Check final run
    if run_points >= min_points:
        runs.append({
            'game_id': scoring.iloc[-1]['game_id'],
            'start_minute': run_start,
            'end_minute': scoring.iloc[-1]['game_minute'],
            'team': current_team,
            'points': run_points,
            'opponent_points': 0
        })
    
    return pd.DataFrame(runs)


def compute_rolling_points(df: pd.DataFrame, windows: List[int] = [3, 5, 10]) -> pd.DataFrame:
    """
    Calculate rolling sum of points scored in last N minutes for each team.
    
    Args:
        df: DataFrame with points by minute
        windows: List of window sizes in minutes
        
    Returns:
        DataFrame with rolling point features
    """
    df = df.copy()
    
    # Ensure we have points columns
    if 'points_home' not in df.columns or 'points_away' not in df.columns:
        raise ValueError("points_home and points_away columns required")
    
    # Calculate rolling sums for each window
    for window in windows:
        df[f'rolling_points_home_{window}m'] = df['points_home'].rolling(window=window, min_periods=1).sum()
        df[f'rolling_points_away_{window}m'] = df['points_away'].rolling(window=window, min_periods=1).sum()
        
        # Also calculate differential
        df[f'rolling_diff_{window}m'] = df[f'rolling_points_home_{window}m'] - df[f'rolling_points_away_{window}m']
    
    return df


def compute_possession_changes(pbp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate possession changes per minute.
    
    Args:
        pbp_df: Play-by-play DataFrame
        
    Returns:
        DataFrame with possession change counts
    """
    if 'game_minute_rounded' not in pbp_df.columns:
        raise ValueError("game_minute_rounded column not found")
    
    # Possession changes when location changes (simplified)
    pbp_df = pbp_df.sort_values(['game_id', 'action_number']).copy()
    pbp_df['possession_change'] = (pbp_df['location'] != pbp_df['location'].shift(1)).astype(int)
    
    # Aggregate by minute
    possession_changes = pbp_df.groupby('game_minute_rounded')['possession_change'].sum().reset_index()
    possession_changes = possession_changes.rename(columns={'possession_change': 'possession_changes'})
    
    return possession_changes

