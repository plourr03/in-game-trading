"""
Trading Engine - Signal Generator
==================================

Watches Kalshi price data during games and generates buy/sell signals
based on validated profitable strategies.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Strategy:
    """Strategy configuration"""
    name: str
    price_min: float
    price_max: float
    move_threshold: float  # percentage
    hold_period: int  # minutes
    expected_pl: float  # expected P/L percentage
    sharpe_ratio: float
    win_rate: float


@dataclass
class Signal:
    """Trading signal"""
    timestamp: datetime
    game_id: str
    strategy_name: str
    action: str  # 'BUY' or 'SELL'
    entry_price: float
    target_exit_time: datetime
    expected_pl: float
    confidence: float
    reason: str


class SignalGenerator:
    """
    Generates trading signals by monitoring price movements.
    """
    
    def __init__(self, strategies: List[Strategy]):
        """
        Initialize signal generator with validated strategies.
        
        Args:
            strategies: List of Strategy objects to monitor
        """
        self.strategies = strategies
        self.active_positions = {}  # game_id -> list of open positions
        
    def watch_game(self, kalshi_df: pd.DataFrame, game_id: str) -> List[Signal]:
        """
        Watch a single game and generate signals.
        
        Args:
            kalshi_df: DataFrame with Kalshi price data for all games
            game_id: Specific game to watch
            
        Returns:
            List of Signal objects
        """
        # Filter to this game
        game_data = kalshi_df[kalshi_df['game_id'] == game_id].copy()
        game_data = game_data.sort_values('datetime').reset_index(drop=True)
        
        # Calculate price changes
        game_data['price_change'] = game_data['close'].diff()
        game_data['price_change_pct'] = (game_data['price_change'] / game_data['close'].shift(1)).abs() * 100
        
        signals = []
        
        # Iterate through each minute of the game
        for idx, row in game_data.iterrows():
            if idx == 0:
                continue  # Skip first minute (no price change yet)
            
            current_price = row['close']
            price_move_pct = row['price_change_pct']
            timestamp = row['datetime']
            
            # Check each strategy for a signal
            for strategy in self.strategies:
                # Check if price is in range for this strategy
                if not (strategy.price_min <= current_price <= strategy.price_max):
                    continue
                
                # Check if move exceeds threshold
                if price_move_pct > strategy.move_threshold:
                    # Generate BUY signal (mean reversion)
                    signal = Signal(
                        timestamp=timestamp,
                        game_id=game_id,
                        strategy_name=strategy.name,
                        action='BUY',
                        entry_price=current_price,
                        target_exit_time=timestamp + pd.Timedelta(minutes=strategy.hold_period),
                        expected_pl=strategy.expected_pl,
                        confidence=strategy.win_rate,
                        reason=f"Price moved {price_move_pct:.1f}% (threshold: {strategy.move_threshold}%)"
                    )
                    signals.append(signal)
        
        return signals
    
    def get_top_strategies(self, n: int = 5) -> List[Strategy]:
        """Get top N strategies by Sharpe ratio"""
        return sorted(self.strategies, key=lambda x: x.sharpe_ratio, reverse=True)[:n]


def load_validated_strategies() -> List[Strategy]:
    """
    Load validated strategies from backtest results.
    Returns top performing strategies with RELAXED criteria for demo purposes.
    """
    # Load backtest results
    df = pd.read_csv('outputs/backtests/comprehensive_backtest_results.csv')
    
    # Use more relaxed criteria to ensure we get trading opportunities
    # Criteria: Sharpe > 0.5, p-value < 0.05, at least 100 trades in backtest
    quality_strategies = df[
        (df['sharpe_ratio'] > 0.5) &
        (df['p_value'] < 0.05) &
        (df['total_trades'] > 100)
    ].copy()
    
    # If still no strategies, be even more relaxed
    if quality_strategies.empty:
        quality_strategies = df[
            (df['p_value'] < 0.05) &
            (df['total_trades'] > 50)
        ].copy()
    
    strategies = []
    
    for idx, row in quality_strategies.iterrows():
        strategy = Strategy(
            name=f"P{int(row['price_min'])}-{int(row['price_max'])} M{int(row['threshold'])}% H{int(row['hold_period'])}m",
            price_min=row['price_min'],
            price_max=row['price_max'],
            move_threshold=row['threshold'],
            hold_period=int(row['hold_period']),
            expected_pl=row['mean_net_pl_pct'],
            sharpe_ratio=row['sharpe_ratio'],
            win_rate=row['win_rate']
        )
        strategies.append(strategy)
    
    return strategies


if __name__ == "__main__":
    # Test the signal generator
    print("Loading validated strategies...")
    strategies = load_validated_strategies()
    
    print(f"\nLoaded {len(strategies)} high-quality strategies:")
    for s in strategies[:5]:
        print(f"  • {s.name}: Sharpe={s.sharpe_ratio:.2f}, Expected P/L={s.expected_pl:.2f}%")
    
    print("\nSignal generator ready!")

