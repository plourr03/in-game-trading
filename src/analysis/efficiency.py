"""Market efficiency tests - Area 8"""
import pandas as pd
import numpy as np
from typing import Dict, List
from scipy import stats
from ..backtesting.fees import calculate_round_trip_cost
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def autocorrelation_analysis(df: pd.DataFrame, lags: int = 5) -> Dict:
    """
    Test if price changes are autocorrelated (momentum or mean-reversion).
    
    Args:
        df: Kalshi data
        lags: Number of lags to test
        
    Returns:
        Dictionary with autocorrelation coefficients and p-values
    """
    logger.info("Running autocorrelation analysis...")
    
    # Calculate price changes
    df = df.copy()
    df['price_change'] = df.groupby('game_id')['close'].diff()
    
    results = {'lags': {}}
    
    for lag in range(1, lags + 1):
        df[f'lag_{lag}'] = df.groupby('game_id')['price_change'].shift(lag)
        
        # Calculate correlation
        valid_data = df[['price_change', f'lag_{lag}']].dropna()
        
        if len(valid_data) > 0:
            corr = valid_data['price_change'].corr(valid_data[f'lag_{lag}'])
            
            # T-test for significance
            t_stat, p_value = stats.pearsonr(valid_data['price_change'], valid_data[f'lag_{lag}'])
            
            results['lags'][lag] = {
                'correlation': corr,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'interpretation': 'momentum' if corr > 0 else 'mean_reversion'
            }
    
    return results


def event_lead_lag(merged_df: pd.DataFrame, lags: List[int] = [1, 2, 3]) -> Dict:
    """
    Test if events predict future price changes.
    
    Args:
        merged_df: Merged data
        lags: Future lags to test
        
    Returns:
        Dictionary with predictive power statistics
    """
    logger.info("Testing event predictive power...")
    
    merged_df = merged_df.copy()
    merged_df['price_change'] = merged_df.groupby('game_id')['close'].diff()
    
    results = {}
    
    # Test if scoring events predict future price changes
    for event_type in ['Made Shot', 'Turnover', 'Foul']:
        merged_df['is_event'] = (merged_df['action_type'] == event_type).astype(int)
        
        event_results = {}
        for lag in lags:
            merged_df[f'future_change_{lag}'] = merged_df.groupby('game_id')['price_change'].shift(-lag)
            
            # Compare price change after events vs non-events
            with_event = merged_df[merged_df['is_event'] == 1][f'future_change_{lag}']
            without_event = merged_df[merged_df['is_event'] == 0][f'future_change_{lag}']
            
            if len(with_event) > 10 and len(without_event) > 10:
                t_stat, p_value = stats.ttest_ind(with_event.dropna(), without_event.dropna())
                
                event_results[f'lag_{lag}'] = {
                    'mean_change_with_event': with_event.mean(),
                    'mean_change_without_event': without_event.mean(),
                    'difference': with_event.mean() - without_event.mean(),
                    'p_value': p_value,
                    'significant': p_value < 0.05
                }
        
        results[event_type] = event_results
    
    return results


def simple_rule_backtest(merged_df: pd.DataFrame, rules: List[Dict]) -> pd.DataFrame:
    """
    Test simple trading rules like "buy after 6-0 run against".
    
    Args:
        merged_df: Merged data
        rules: List of rule dictionaries with 'name', 'condition', 'direction'
        
    Returns:
        DataFrame with backtest results per rule
    """
    logger.info("Backtesting simple trading rules...")
    
    results = []
    
    for rule in rules:
        rule_name = rule['name']
        logger.info(f"Testing rule: {rule_name}")
        
        # Apply rule condition (example implementation)
        if rule_name == 'fade_momentum':
            # After large price move up, bet down
            merged_df['large_up_move'] = (merged_df.groupby('game_id')['close'].diff() > 5)
            signals = merged_df[merged_df['large_up_move']]
            
        elif rule_name == 'buy_underdog_q4':
            # Buy underdog when they score in Q4 close game
            signals = merged_df[
                (merged_df['period'] == 4) &
                (merged_df['score_differential'].abs() < 5) &
                (merged_df['action_type'] == 'Made Shot')
            ]
            
        elif rule_name == 'contrarian':
            # After >5% move, bet reversal
            merged_df['large_move'] = (merged_df.groupby('game_id')['close'].diff().abs() > 5)
            signals = merged_df[merged_df['large_move']]
        
        else:
            continue
        
        # Calculate P&L for each signal
        trades = []
        for idx in signals.index:
            try:
                entry_price = merged_df.loc[idx, 'close']
                
                # Exit 3 minutes later
                game_id = merged_df.loc[idx, 'game_id']
                game_minute = merged_df.loc[idx, 'game_minute']
                
                exit_data = merged_df[
                    (merged_df['game_id'] == game_id) &
                    (merged_df['game_minute'] == game_minute + 3)
                ]
                
                if len(exit_data) > 0:
                    exit_price = exit_data.iloc[0]['close']
                    
                    # Calculate P&L (assuming 100 contracts)
                    direction = rule.get('direction', 'sell')
                    if direction == 'sell':
                        gross_pl = (entry_price - exit_price) / 100 * 100  # Per contract
                    else:
                        gross_pl = (exit_price - entry_price) / 100 * 100
                    
                    # Subtract fees
                    fees = calculate_round_trip_cost(100, entry_price, exit_price)
                    net_pl = gross_pl - fees
                    
                    trades.append({
                        'rule': rule_name,
                        'game_id': game_id,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'gross_pl': gross_pl,
                        'fees': fees,
                        'net_pl': net_pl
                    })
            except:
                continue
        
        if trades:
            trades_df = pd.DataFrame(trades)
            results.append({
                'rule': rule_name,
                'total_trades': len(trades_df),
                'win_rate': (trades_df['net_pl'] > 0).mean(),
                'mean_net_pl': trades_df['net_pl'].mean(),
                'total_net_pl': trades_df['net_pl'].sum(),
                'sharpe_ratio': trades_df['net_pl'].mean() / trades_df['net_pl'].std() if trades_df['net_pl'].std() > 0 else 0,
                'max_drawdown': trades_df['net_pl'].cumsum().min()
            })
    
    return pd.DataFrame(results)


def information_decay_curve(merged_df: pd.DataFrame) -> pd.DataFrame:
    """
    Measure how long it takes for events to be fully priced in.
    
    Args:
        merged_df: Merged data
        
    Returns:
        DataFrame showing price adjustment over time
    """
    logger.info("Calculating information decay curve...")
    
    # Focus on scoring events
    scoring = merged_df[merged_df['action_type'] == 'Made Shot'].copy()
    
    decay_results = []
    
    for lag in range(0, 6):  # 0 to 5 minutes after event
        scoring[f'price_change_lag_{lag}'] = scoring.groupby('game_id')['close'].shift(-lag) - scoring['close']
        
        mean_change = scoring[f'price_change_lag_{lag}'].mean()
        std_change = scoring[f'price_change_lag_{lag}'].std()
        
        decay_results.append({
            'lag_minutes': lag,
            'mean_price_change': mean_change,
            'std_price_change': std_change,
            'pct_of_final': mean_change / scoring['price_change_lag_5'].mean() if lag < 5 else 1.0
        })
    
    return pd.DataFrame(decay_results)

