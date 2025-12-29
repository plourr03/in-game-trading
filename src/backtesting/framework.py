"""Backtesting framework"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from .fees import calculate_round_trip_cost
from ..utils.helpers import get_logger

logger = get_logger(__name__)


class Strategy(ABC):
    """Base class for trading strategies."""
    
    def __init__(self, name: str):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name
        """
        self.name = name
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals.
        
        Args:
            df: Game data
            
        Returns:
            DataFrame with signal column (-1 = sell, 0 = hold, 1 = buy)
        """
        pass


class Backtester:
    """Backtesting engine for strategy evaluation."""
    
    def __init__(self, initial_capital: float = 10000.0, 
                 position_size: int = 100):
        """
        Initialize backtester.
        
        Args:
            initial_capital: Starting capital
            position_size: Contracts per trade
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.trades = []
        self.capital = initial_capital
        
    def run(self, df: pd.DataFrame, strategy: Strategy) -> Dict:
        """
        Run backtest for a strategy.
        
        Args:
            df: Game data
            strategy: Strategy instance
            
        Returns:
            Dictionary with performance metrics
        """
        logger.info(f"Running backtest for strategy: {strategy.name}")
        
        # Generate signals
        df_with_signals = strategy.generate_signals(df)
        
        # Execute trades
        self.trades = []
        self.capital = self.initial_capital
        
        # Track positions
        position = None
        
        for idx in range(len(df_with_signals)):
            row = df_with_signals.iloc[idx]
            signal = row.get('signal', 0)
            
            # Entry logic
            if position is None and signal != 0:
                position = {
                    'entry_idx': idx,
                    'entry_price': row['close'],
                    'direction': signal,
                    'game_id': row['game_id'],
                    'entry_minute': row['game_minute']
                }
            
            # Exit logic (exit after 3 minutes or end of game)
            elif position is not None:
                time_in_trade = row['game_minute'] - position['entry_minute']
                
                if time_in_trade >= 3 or idx == len(df_with_signals) - 1:
                    # Exit position
                    trade = self._execute_trade(
                        entry_price=position['entry_price'],
                        exit_price=row['close'],
                        direction=position['direction'],
                        game_id=position['game_id']
                    )
                    self.trades.append(trade)
                    self.capital += trade['net_pl']
                    position = None
        
        # Calculate performance metrics
        metrics = performance_metrics(self.trades)
        metrics['final_capital'] = self.capital
        metrics['total_return'] = (self.capital - self.initial_capital) / self.initial_capital
        metrics['strategy'] = strategy.name
        
        logger.info(f"Backtest complete. Total return: {metrics['total_return']:.2%}")
        
        return metrics
    
    def _execute_trade(self, entry_price: float, exit_price: float, 
                      direction: int, game_id: int) -> Dict:
        """
        Execute a single trade with fees.
        
        Args:
            entry_price: Entry price
            exit_price: Exit price
            direction: 1 for buy, -1 for sell
            game_id: Game ID
            
        Returns:
            Dictionary with trade details
        """
        # Calculate gross P&L
        if direction == 1:  # Long
            gross_pl = (exit_price - entry_price) / 100 * self.position_size
        else:  # Short
            gross_pl = (entry_price - exit_price) / 100 * self.position_size
        
        # Calculate fees
        fees = calculate_round_trip_cost(self.position_size, entry_price, exit_price)
        
        # Net P&L
        net_pl = gross_pl - fees
        
        return {
            'game_id': game_id,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'direction': direction,
            'gross_pl': gross_pl,
            'fees': fees,
            'net_pl': net_pl
        }


def performance_metrics(trades: List[Dict]) -> Dict:
    """
    Calculate performance metrics from trade list.
    
    Metrics:
    - Total return
    - Sharpe ratio
    - Win rate
    - Average win/loss
    - Maximum drawdown
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        Dictionary with performance metrics
    """
    if not trades:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'total_net_pl': 0
        }
    
    trades_df = pd.DataFrame(trades)
    
    # Separate wins and losses
    wins = trades_df[trades_df['net_pl'] > 0]
    losses = trades_df[trades_df['net_pl'] <= 0]
    
    # Calculate metrics
    metrics = {
        'total_trades': len(trades_df),
        'win_rate': len(wins) / len(trades_df),
        'avg_win': wins['net_pl'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['net_pl'].mean() if len(losses) > 0 else 0,
        'total_net_pl': trades_df['net_pl'].sum(),
        'avg_net_pl': trades_df['net_pl'].mean(),
        'std_net_pl': trades_df['net_pl'].std()
    }
    
    # Sharpe ratio (annualized, assuming ~200 games per year)
    if metrics['std_net_pl'] > 0:
        metrics['sharpe_ratio'] = (metrics['avg_net_pl'] / metrics['std_net_pl']) * np.sqrt(200)
    else:
        metrics['sharpe_ratio'] = 0
    
    # Maximum drawdown
    cumulative_pl = trades_df['net_pl'].cumsum()
    running_max = cumulative_pl.cummax()
    drawdown = cumulative_pl - running_max
    metrics['max_drawdown'] = drawdown.min()
    
    # Profit factor
    if len(losses) > 0 and losses['net_pl'].sum() != 0:
        metrics['profit_factor'] = wins['net_pl'].sum() / abs(losses['net_pl'].sum())
    else:
        metrics['profit_factor'] = np.inf if len(wins) > 0 else 0
    
    return metrics

