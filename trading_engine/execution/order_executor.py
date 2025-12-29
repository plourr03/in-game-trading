"""
Trading Engine - Order Executor
================================

Handles order execution and fee calculations.
"""

import pandas as pd
import numpy as np
from typing import Dict


# Kalshi fee structure
TAKER_FEE_RATE = 0.07  # 7%
MAKER_FEE_RATE = 0.0175  # 1.75%


def calculate_fees(contracts: int, price: float, is_taker: bool = True) -> float:
    """
    Calculate Kalshi trading fees.
    
    Formula: fee = rate × contracts × P × (1-P)
    where P is price as decimal (0-1)
    
    Args:
        contracts: Number of contracts
        price: Price in cents (0-100)
        is_taker: Whether this is a taker order (vs maker)
        
    Returns:
        Fee in dollars
    """
    price_decimal = price / 100.0
    rate = TAKER_FEE_RATE if is_taker else MAKER_FEE_RATE
    fee = rate * contracts * price_decimal * (1 - price_decimal)
    return fee


def simulate_order_execution(price: float, volume: int, order_size: int,
                            order_type: str = 'market') -> Dict:
    """
    Simulate order execution with slippage.
    
    Args:
        price: Current market price
        volume: Available volume at this price level
        order_size: Number of contracts to trade
        order_type: 'market' or 'limit'
        
    Returns:
        Dict with execution details
    """
    if order_type == 'limit':
        # Limit order - no slippage but might not fill
        fill_probability = min(1.0, volume / order_size) if order_size > 0 else 1.0
        executed_price = price
        executed_size = order_size if np.random.random() < fill_probability else 0
        is_taker = False  # Maker fees
    else:
        # Market order - always fills but with slippage
        slippage_pct = 0.01 if volume > order_size else 0.05  # 1-5% slippage
        executed_price = price * (1 + slippage_pct * np.random.uniform(-1, 1))
        executed_size = order_size
        is_taker = True  # Taker fees
    
    # Calculate fees
    fees = calculate_fees(executed_size, executed_price, is_taker)
    
    return {
        'executed_price': executed_price,
        'executed_size': executed_size,
        'fees': fees,
        'is_taker': is_taker,
        'slippage_pct': abs(executed_price - price) / price * 100
    }


class OrderExecutor:
    """Executes trades with realistic execution modeling"""
    
    def __init__(self, default_size: int = 100, order_type: str = 'market'):
        """
        Initialize executor.
        
        Args:
            default_size: Default number of contracts per trade
            order_type: 'market' or 'limit'
        """
        self.default_size = default_size
        self.order_type = order_type
        self.execution_log = []
    
    def execute_buy(self, game_id: str, timestamp: pd.Timestamp, price: float,
                    volume: int, size: int = None) -> Dict:
        """Execute a buy order"""
        size = size or self.default_size
        
        execution = simulate_order_execution(price, volume, size, self.order_type)
        execution['action'] = 'BUY'
        execution['game_id'] = game_id
        execution['timestamp'] = timestamp
        
        self.execution_log.append(execution)
        return execution
    
    def execute_sell(self, game_id: str, timestamp: pd.Timestamp, price: float,
                     volume: int, size: int = None) -> Dict:
        """Execute a sell order"""
        size = size or self.default_size
        
        execution = simulate_order_execution(price, volume, size, self.order_type)
        execution['action'] = 'SELL'
        execution['game_id'] = game_id
        execution['timestamp'] = timestamp
        
        self.execution_log.append(execution)
        return execution
    
    def get_execution_stats(self) -> Dict:
        """Get execution statistics"""
        if not self.execution_log:
            return {}
        
        df = pd.DataFrame(self.execution_log)
        
        return {
            'total_executions': len(df),
            'avg_slippage_pct': df['slippage_pct'].mean(),
            'total_fees': df['fees'].sum(),
            'taker_rate': df['is_taker'].mean()
        }

