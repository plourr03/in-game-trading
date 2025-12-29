"""Data preprocessing and cleaning"""
import pandas as pd
import numpy as np
from typing import Optional
from ..utils.helpers import parse_clock_string, get_logger
from ..utils.constants import MINUTES_PER_PERIOD, OVERTIME_MINUTES

logger = get_logger(__name__)


def fill_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Forward-fill then back-fill OHLC prices to handle gaps in trading data.
    
    Args:
        df: DataFrame with OHLC columns
        
    Returns:
        DataFrame with filled prices
    """
    logger.info("Filling missing prices...")
    
    # Make a copy to avoid modifying original
    df = df.copy()
    
    price_cols = ['open', 'high', 'low', 'close']
    
    # Group by game_id if present
    if 'game_id' in df.columns:
        for game_id in df['game_id'].unique():
            mask = df['game_id'] == game_id
            for col in price_cols:
                if col in df.columns:
                    # Forward fill first, then backward fill
                    df.loc[mask, col] = df.loc[mask, col].fillna(method='ffill').fillna(method='bfill')
    else:
        # Fill all at once if no game_id
        for col in price_cols:
            if col in df.columns:
                df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
    
    logger.info("Price filling complete")
    return df


def calculate_game_minute(period: int, clock: str) -> float:
    """
    Convert period and clock string to game minute.
    
    Formula: game_minute = (period - 1) * 12 + (12 - minutes_remaining_in_period)
    
    Args:
        period: Period number (1-4 for regulation, 5+ for OT)
        clock: Clock string (e.g., 'PT11M50.00S')
        
    Returns:
        Game minute as float
    """
    minutes_remaining = parse_clock_string(clock)
    
    if period <= 4:
        # Regular periods
        game_minute = (period - 1) * MINUTES_PER_PERIOD + (MINUTES_PER_PERIOD - minutes_remaining)
    else:
        # Overtime periods - each OT is 5 minutes
        regulation_minutes = 4 * MINUTES_PER_PERIOD
        ot_number = period - 4
        game_minute = regulation_minutes + (ot_number - 1) * OVERTIME_MINUTES + (OVERTIME_MINUTES - minutes_remaining)
    
    return game_minute


def add_team_to_kalshi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse ticker to determine which team the probability represents.
    
    Args:
        df: Kalshi DataFrame with ticker column
        
    Returns:
        DataFrame with team information added
    """
    logger.info("Parsing ticker information...")
    
    df = df.copy()
    
    # Example ticker: KXNBAGAME-25DEC01CLEIND-IND
    # The last part after the dash is the team the probability is for
    def parse_ticker(ticker):
        if pd.isna(ticker):
            return None
        parts = ticker.split('-')
        if len(parts) >= 3:
            return parts[-1]
        return None
    
    df['kalshi_team'] = df['ticker'].apply(parse_ticker)
    
    # Determine if this is home or away team
    df['is_home_team'] = df['kalshi_team'] == df['home_team']
    
    logger.info("Ticker parsing complete")
    return df

