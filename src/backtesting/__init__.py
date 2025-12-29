"""Backtesting framework for strategy evaluation"""
from .fees import calculate_kalshi_fees, calculate_round_trip_cost
from .framework import Strategy, Backtester, performance_metrics
from .rules import SimpleRuleStrategy

__all__ = [
    'calculate_kalshi_fees',
    'calculate_round_trip_cost',
    'Strategy',
    'Backtester',
    'performance_metrics',
    'SimpleRuleStrategy',
]

