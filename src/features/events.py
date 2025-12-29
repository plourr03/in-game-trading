"""Event-based features from play-by-play data"""
import pandas as pd
import numpy as np
from typing import Dict, List


def extract_scoring_events(pbp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter play-by-play to scoring events only (Made Shots, Free Throws).
    
    Args:
        pbp_df: Full play-by-play DataFrame
        
    Returns:
        DataFrame with scoring events only
    """
    # Filter to made shots and free throws
    scoring_mask = (
        (pbp_df['action_type'] == 'Made Shot') |
        ((pbp_df['action_type'] == 'Free Throw') & (pbp_df['shot_result'] == 'Made'))
    )
    
    scoring_events = pbp_df[scoring_mask].copy()
    
    return scoring_events


def compute_points_by_minute(pbp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate points scored per minute for each team.
    
    Args:
        pbp_df: Play-by-play DataFrame with game_minute
        
    Returns:
        DataFrame with points_home, points_away by minute
    """
    if 'game_minute_rounded' not in pbp_df.columns:
        raise ValueError("game_minute_rounded column not found. Run align_pbp_to_minutes first.")
    
    # Extract scoring events
    scoring = extract_scoring_events(pbp_df)
    
    # Calculate points per event
    scoring['points'] = scoring['shot_value'].fillna(1)  # Free throws are 1 point
    
    # Aggregate by minute and location (home/away)
    points_by_minute = scoring.groupby(['game_minute_rounded', 'location'])['points'].sum().unstack(fill_value=0)
    
    # Rename columns
    if 'h' in points_by_minute.columns:
        points_by_minute = points_by_minute.rename(columns={'h': 'points_home'})
    else:
        points_by_minute['points_home'] = 0
        
    if 'v' in points_by_minute.columns:
        points_by_minute = points_by_minute.rename(columns={'v': 'points_away'})
    else:
        points_by_minute['points_away'] = 0
    
    # Reset index to make game_minute a column
    points_by_minute = points_by_minute.reset_index()
    
    return points_by_minute


def identify_turnovers_by_minute(pbp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Count turnovers per minute for each team.
    
    Args:
        pbp_df: Play-by-play DataFrame
        
    Returns:
        DataFrame with turnover counts by minute
    """
    if 'game_minute_rounded' not in pbp_df.columns:
        raise ValueError("game_minute_rounded column not found")
    
    # Filter to turnovers
    turnover_mask = pbp_df['action_type'] == 'Turnover'
    turnovers = pbp_df[turnover_mask].copy()
    
    # Aggregate by minute and location
    turnovers_by_minute = turnovers.groupby(['game_minute_rounded', 'location']).size().unstack(fill_value=0)
    
    # Rename columns
    if 'h' in turnovers_by_minute.columns:
        turnovers_by_minute = turnovers_by_minute.rename(columns={'h': 'turnovers_home'})
    else:
        turnovers_by_minute['turnovers_home'] = 0
        
    if 'v' in turnovers_by_minute.columns:
        turnovers_by_minute = turnovers_by_minute.rename(columns={'v': 'turnovers_away'})
    else:
        turnovers_by_minute['turnovers_away'] = 0
    
    turnovers_by_minute = turnovers_by_minute.reset_index()
    
    return turnovers_by_minute


def count_fouls_by_minute(pbp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Count fouls committed per minute for each team.
    
    Args:
        pbp_df: Play-by-play DataFrame
        
    Returns:
        DataFrame with foul counts by minute
    """
    if 'game_minute_rounded' not in pbp_df.columns:
        raise ValueError("game_minute_rounded column not found")
    
    # Filter to fouls
    foul_mask = pbp_df['action_type'] == 'Foul'
    fouls = pbp_df[foul_mask].copy()
    
    # Aggregate by minute and location
    fouls_by_minute = fouls.groupby(['game_minute_rounded', 'location']).size().unstack(fill_value=0)
    
    # Rename columns
    if 'h' in fouls_by_minute.columns:
        fouls_by_minute = fouls_by_minute.rename(columns={'h': 'fouls_home'})
    else:
        fouls_by_minute['fouls_home'] = 0
        
    if 'v' in fouls_by_minute.columns:
        fouls_by_minute = fouls_by_minute.rename(columns={'v': 'fouls_away'})
    else:
        fouls_by_minute['fouls_away'] = 0
    
    fouls_by_minute = fouls_by_minute.reset_index()
    
    return fouls_by_minute

