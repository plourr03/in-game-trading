"""
Trading Engine - Position Manager
==================================

Manages open positions, tracks P/L, and generates exit signals.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Position:
    """Open trading position"""
    position_id: str
    game_id: str
    strategy_name: str
    entry_time: datetime
    entry_price: float
    target_exit_time: datetime
    hold_period: int
    size: int = 100  # contracts
    expected_pl: float = 0.0
    
    # Tracking
    current_price: float = 0.0
    current_pl_pct: float = 0.0
    current_pl_dollars: float = 0.0
    status: str = 'OPEN'  # OPEN, CLOSED
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    realized_pl_pct: Optional[float] = None
    realized_pl_dollars: Optional[float] = None
    fees_paid: float = 0.0
    
    def update(self, current_price: float, current_time: datetime):
        """Update position with current price"""
        self.current_price = current_price
        
        # Calculate unrealized P/L (mean reversion logic)
        # If we're betting on reversion, profit = entry_price - current_price (if price was rising)
        # For simplicity, assume we always bet on reversion toward entry price
        price_move = self.entry_price - current_price
        gross_pl_dollars = price_move * (self.size / 100)
        
        # Estimate fees (will calculate exact on close)
        from trading_engine.execution.order_executor import calculate_fees
        entry_fee = calculate_fees(self.size, self.entry_price)
        est_exit_fee = calculate_fees(self.size, current_price)
        self.fees_paid = entry_fee + est_exit_fee
        
        # Net P/L
        self.current_pl_dollars = gross_pl_dollars - self.fees_paid
        
        # As percentage
        position_value = self.entry_price * (self.size / 100)
        self.current_pl_pct = (self.current_pl_dollars / position_value * 100) if position_value > 0 else 0
    
    def close(self, exit_price: float, exit_time: datetime):
        """Close the position"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.status = 'CLOSED'
        
        # Calculate realized P/L
        price_move = self.entry_price - exit_price
        gross_pl_dollars = price_move * (self.size / 100)
        
        # Calculate exact fees
        from trading_engine.execution.order_executor import calculate_fees
        entry_fee = calculate_fees(self.size, self.entry_price)
        exit_fee = calculate_fees(self.size, exit_price)
        self.fees_paid = entry_fee + exit_fee
        
        # Net P/L
        self.realized_pl_dollars = gross_pl_dollars - self.fees_paid
        
        # As percentage
        position_value = self.entry_price * (self.size / 100)
        self.realized_pl_pct = (self.realized_pl_dollars / position_value * 100) if position_value > 0 else 0


class PositionManager:
    """
    Manages all open positions and determines when to exit.
    """
    
    def __init__(self):
        self.positions: List[Position] = []
        self.closed_positions: List[Position] = []
        self.position_counter = 0
    
    def reset(self):
        """Reset the position manager for a new game"""
        self.positions = []
        self.closed_positions = []
        self.position_counter = 0
        
    def open_position(self, game_id: str, strategy_name: str, entry_time: datetime,
                     entry_price: float, hold_period: int, expected_pl: float,
                     size: int = 100) -> Position:
        """Open a new position"""
        self.position_counter += 1
        
        position = Position(
            position_id=f"POS_{self.position_counter:04d}",
            game_id=game_id,
            strategy_name=strategy_name,
            entry_time=entry_time,
            entry_price=entry_price,
            target_exit_time=entry_time + pd.Timedelta(minutes=hold_period),
            hold_period=hold_period,
            size=size,
            expected_pl=expected_pl,
            current_price=entry_price
        )
        
        self.positions.append(position)
        return position
    
    def update_positions(self, game_data: pd.DataFrame, current_time: datetime):
        """Update all open positions with current market data"""
        for position in self.positions:
            if position.status != 'OPEN':
                continue
            
            # Get current price for this game
            current_row = game_data[
                (game_data['game_id'] == position.game_id) &
                (game_data['datetime'] == current_time)
            ]
            
            if not current_row.empty:
                current_price = current_row.iloc[0]['close']
                position.update(current_price, current_time)
    
    def check_exits(self, current_time: datetime) -> List[Position]:
        """Check which positions should be exited"""
        to_exit = []
        
        for position in self.positions:
            if position.status != 'OPEN':
                continue
            
            # Exit if hold period reached
            if current_time >= position.target_exit_time:
                to_exit.append(position)
        
        return to_exit
    
    def close_position(self, position: Position, exit_price: float, exit_time: datetime):
        """Close a position"""
        position.close(exit_price, exit_time)
        self.positions.remove(position)
        self.closed_positions.append(position)
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        return [p for p in self.positions if p.status == 'OPEN']
    
    def get_performance_summary(self) -> Dict:
        """Get summary of all closed positions"""
        if not self.closed_positions:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pl_dollars': 0,
                'avg_pl_pct': 0,
                'total_fees': 0
            }
        
        wins = sum(1 for p in self.closed_positions if p.realized_pl_dollars > 0)
        losses = len(self.closed_positions) - wins
        total_pl = sum(p.realized_pl_dollars for p in self.closed_positions)
        avg_pl = np.mean([p.realized_pl_pct for p in self.closed_positions])
        total_fees = sum(p.fees_paid for p in self.closed_positions)
        
        return {
            'total_trades': len(self.closed_positions),
            'wins': wins,
            'losses': losses,
            'win_rate': wins / len(self.closed_positions),
            'total_pl_dollars': total_pl,
            'avg_pl_pct': avg_pl,
            'total_fees': total_fees
        }
    
    def get_positions_dataframe(self) -> pd.DataFrame:
        """Convert closed positions to DataFrame"""
        if not self.closed_positions:
            return pd.DataFrame()
        
        data = []
        for p in self.closed_positions:
            data.append({
                'position_id': p.position_id,
                'game_id': p.game_id,
                'strategy': p.strategy_name,
                'entry_time': p.entry_time,
                'entry_price': p.entry_price,
                'exit_time': p.exit_time,
                'exit_price': p.exit_price,
                'hold_minutes': (p.exit_time - p.entry_time).total_seconds() / 60,
                'size': p.size,
                'pl_pct': p.realized_pl_pct,
                'pl_dollars': p.realized_pl_dollars,
                'fees': p.fees_paid,
                'is_winner': p.realized_pl_dollars > 0
            })
        
        return pd.DataFrame(data)

