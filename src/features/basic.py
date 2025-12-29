"""Basic feature engineering"""
import pandas as pd
import numpy as np
from typing import Optional
from ..utils.constants import MINUTES_PER_PERIOD, PERIODS_IN_REGULATION, TOTAL_REGULATION_MINUTES


def compute_score_differential(home_score: pd.Series, away_score: pd.Series, 
                               is_home_team: bool) -> pd.Series:
    """
    Calculate score differential from perspective of team being bet on.
    
    Args:
        home_score: Home team score
        away_score: Away team score
        is_home_team: Whether the Kalshi probability is for home team
        
    Returns:
        Score differential (positive = team ahead)
    """
    if is_home_team:
        return home_score - away_score
    else:
        return away_score - home_score


def compute_time_remaining(period: pd.Series, game_minute: pd.Series) -> pd.Series:
    """
    Calculate total time remaining in game.
    
    Args:
        period: Period number
        game_minute: Current game minute
        
    Returns:
        Minutes remaining in regulation
    """
    # Total regulation time is 48 minutes
    time_remaining = TOTAL_REGULATION_MINUTES - game_minute
    
    # For overtime, time remaining is negative (or we could handle differently)
    # For now, treat OT as extension beyond regulation
    return time_remaining


def compute_period_indicators(period: pd.Series) -> pd.DataFrame:
    """
    Create indicator variables for period (Q1, Q2, Q3, Q4, OT).
    
    Args:
        period: Period number
        
    Returns:
        DataFrame with period indicators
    """
    indicators = pd.DataFrame()
    
    indicators['is_q1'] = (period == 1).astype(int)
    indicators['is_q2'] = (period == 2).astype(int)
    indicators['is_q3'] = (period == 3).astype(int)
    indicators['is_q4'] = (period == 4).astype(int)
    indicators['is_ot'] = (period > 4).astype(int)
    
    # Also add first/second half indicators
    indicators['is_first_half'] = (period <= 2).astype(int)
    indicators['is_second_half'] = ((period > 2) & (period <= 4)).astype(int)
    
    return indicators

