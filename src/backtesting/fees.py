"""Kalshi fee calculations"""
import numpy as np
from ..utils.constants import KALSHI_TAKER_FEE_RATE, KALSHI_MAKER_FEE_RATE


def calculate_kalshi_fees(contracts: int, price: float, is_taker: bool = True) -> float:
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
    
    rate = KALSHI_TAKER_FEE_RATE if is_taker else KALSHI_MAKER_FEE_RATE
    fee = rate * contracts * price_decimal * (1 - price_decimal)
    
    return fee


def calculate_round_trip_cost(contracts: int, entry_price: float, 
                              exit_price: float) -> float:
    """
    Calculate total cost for round-trip trade (entry + exit).
    
    Assumes both legs are taker orders (conservative).
    
    Args:
        contracts: Number of contracts
        entry_price: Entry price in cents
        exit_price: Exit price in cents
        
    Returns:
        Total round-trip fee cost in dollars
    """
    entry_fee = calculate_kalshi_fees(contracts, entry_price, is_taker=True)
    exit_fee = calculate_kalshi_fees(contracts, exit_price, is_taker=True)
    
    return entry_fee + exit_fee


def break_even_edge(price: float, contracts: int = 100) -> float:
    """
    Calculate minimum edge needed to break even after fees.
    
    Args:
        price: Price level in cents
        contracts: Position size
        
    Returns:
        Break-even edge in percentage points
    """
    round_trip = calculate_round_trip_cost(contracts, price, price)
    position_value = contracts * (price / 100.0)
    
    return (round_trip / position_value) * 100.0

