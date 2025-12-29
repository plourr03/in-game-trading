"""
Test dynamic contract sizing based on ML probabilities
"""
import pandas as pd
import numpy as np
import joblib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.backtesting.fees import calculate_kalshi_fees
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def kelly_criterion(win_prob, avg_win, avg_loss):
    """
    Calculate optimal bet size using Kelly Criterion
    
    f* = (p*b - q) / b
    where:
    - p = win probability
    - q = loss probability (1-p)
    - b = win/loss ratio
    """
    if avg_loss == 0:
        return 0
    
    b = abs(avg_win / avg_loss)  # Win/loss ratio
    q = 1 - win_prob
    
    kelly_fraction = (win_prob * b - q) / b
    
    # Use fractional Kelly (25%) for safety
    return max(0, kelly_fraction * 0.25)


def calculate_pl_with_size(row, size, hold_period='5min'):
    """Calculate P/L with specific contract size"""
    buy_fee = calculate_kalshi_fees(size, row['current_price'], is_taker=True)
    
    profit = row[f'profit_{hold_period}']
    sell_price = row['current_price'] + profit
    sell_fee = calculate_kalshi_fees(size, sell_price, is_taker=True)
    
    gross_profit_cents = profit * size
    total_fees_dollars = buy_fee + sell_fee
    net_profit_dollars = (gross_profit_cents / 100) - total_fees_dollars
    
    return net_profit_dollars


def test_dynamic_sizing():
    """Test different contract sizing strategies"""
    
    logger.info("="*100)
    logger.info("DYNAMIC CONTRACT SIZING TEST")
    logger.info("="*100)
    
    # Load data
    logger.info("\nLoading data...")
    df = pd.read_csv('ml_models/outputs/advanced_training_data.csv')
    split_idx = int(len(df) * 0.8)
    test_df = df[split_idx:].copy()
    
    # Load models
    logger.info("Loading models...")
    entry_model = joblib.load('ml_models/outputs/advanced_model.pkl')
    exit_model = joblib.load('ml_models/outputs/exit_timing_model.pkl')
    features = joblib.load('ml_models/outputs/advanced_features.pkl')
    
    # Get predictions
    X_test = test_df[features].fillna(0).replace([np.inf, -np.inf], 0)
    test_df['pred_proba'] = entry_model.predict_proba(X_test)[:, 1]
    
    # Test at threshold 0.60 (our best threshold)
    threshold = 0.60
    entries = test_df[test_df['pred_proba'] >= threshold].copy()
    entries = entries.dropna(subset=['profit_1min', 'profit_3min', 'profit_5min', 'profit_7min'])
    
    logger.info(f"Testing {len(entries):,} entries at threshold {threshold:.2f}")
    
    # Predict exit timing
    X_entries = entries[features].fillna(0).replace([np.inf, -np.inf], 0)
    entries['predicted_hold'] = exit_model.predict(X_entries)
    
    # Define sizing strategies
    strategies = []
    
    # ===== STRATEGY 1: Fixed 100 contracts =====
    logger.info("\n[1/6] Fixed 100 contracts...")
    fixed_100_pl = []
    for idx, row in entries.iterrows():
        hold = str(row['predicted_hold']) + 'min'
        net_pl = calculate_pl_with_size(row, 100, hold)
        fixed_100_pl.append(net_pl)
    
    strategies.append({
        'name': 'Fixed 100c',
        'pl_list': fixed_100_pl,
        'total_pl': sum(fixed_100_pl),
        'avg_size': 100
    })
    
    # ===== STRATEGY 2: Fixed 500 contracts =====
    logger.info("[2/6] Fixed 500 contracts...")
    fixed_500_pl = []
    for idx, row in entries.iterrows():
        hold = str(row['predicted_hold']) + 'min'
        net_pl = calculate_pl_with_size(row, 500, hold)
        fixed_500_pl.append(net_pl)
    
    strategies.append({
        'name': 'Fixed 500c',
        'pl_list': fixed_500_pl,
        'total_pl': sum(fixed_500_pl),
        'avg_size': 500
    })
    
    # ===== STRATEGY 3: Linear scaling (0.60 = 100c, 1.0 = 500c) =====
    logger.info("[3/6] Linear scaling (prob-based)...")
    linear_pl = []
    linear_sizes = []
    
    for idx, row in entries.iterrows():
        # Scale from 100 to 500 based on probability
        # 0.60 -> 100c, 1.0 -> 500c
        prob = row['pred_proba']
        size = int(100 + (prob - threshold) / (1.0 - threshold) * 400)
        size = np.clip(size, 100, 500)
        linear_sizes.append(size)
        
        hold = str(row['predicted_hold']) + 'min'
        net_pl = calculate_pl_with_size(row, size, hold)
        linear_pl.append(net_pl)
    
    strategies.append({
        'name': 'Linear Scaling',
        'pl_list': linear_pl,
        'total_pl': sum(linear_pl),
        'avg_size': np.mean(linear_sizes)
    })
    
    # ===== STRATEGY 4: Aggressive scaling (exponential) =====
    logger.info("[4/6] Aggressive scaling (exponential)...")
    aggressive_pl = []
    aggressive_sizes = []
    
    for idx, row in entries.iterrows():
        # Exponential scaling - higher probs get disproportionately more
        prob = row['pred_proba']
        normalized = (prob - threshold) / (1.0 - threshold)  # 0 to 1
        size = int(100 + (normalized ** 2) * 400)  # Square for exponential
        size = np.clip(size, 100, 500)
        aggressive_sizes.append(size)
        
        hold = str(row['predicted_hold']) + 'min'
        net_pl = calculate_pl_with_size(row, size, hold)
        aggressive_pl.append(net_pl)
    
    strategies.append({
        'name': 'Aggressive (Exponential)',
        'pl_list': aggressive_pl,
        'total_pl': sum(aggressive_pl),
        'avg_size': np.mean(aggressive_sizes)
    })
    
    # ===== STRATEGY 5: Conservative (root scaling) =====
    logger.info("[5/6] Conservative scaling (root)...")
    conservative_pl = []
    conservative_sizes = []
    
    for idx, row in entries.iterrows():
        # Root scaling - more conservative increase
        prob = row['pred_proba']
        normalized = (prob - threshold) / (1.0 - threshold)
        size = int(100 + (normalized ** 0.5) * 400)  # Square root
        size = np.clip(size, 100, 500)
        conservative_sizes.append(size)
        
        hold = str(row['predicted_hold']) + 'min'
        net_pl = calculate_pl_with_size(row, size, hold)
        conservative_pl.append(net_pl)
    
    strategies.append({
        'name': 'Conservative (Root)',
        'pl_list': conservative_pl,
        'total_pl': sum(conservative_pl),
        'avg_size': np.mean(conservative_sizes)
    })
    
    # ===== STRATEGY 6: Kelly Criterion (fractional) =====
    logger.info("[6/6] Kelly Criterion (25% fractional)...")
    
    # First, calculate historical win/loss amounts for Kelly
    sample_results = []
    for idx, row in entries.head(200).iterrows():  # Use sample to estimate
        hold = str(row['predicted_hold']) + 'min'
        net_pl = calculate_pl_with_size(row, 100, hold)
        sample_results.append(net_pl)
    
    sample_wins = [x for x in sample_results if x > 0]
    sample_losses = [x for x in sample_results if x < 0]
    
    avg_win = np.mean(sample_wins) if sample_wins else 0
    avg_loss = abs(np.mean(sample_losses)) if sample_losses else 1
    
    kelly_pl = []
    kelly_sizes = []
    
    for idx, row in entries.iterrows():
        prob = row['pred_proba']
        kelly_fraction = kelly_criterion(prob, avg_win, avg_loss)
        
        # Convert Kelly fraction to contract size (max 500)
        size = int(100 + kelly_fraction * 400)
        size = np.clip(size, 100, 500)
        kelly_sizes.append(size)
        
        hold = str(row['predicted_hold']) + 'min'
        net_pl = calculate_pl_with_size(row, size, hold)
        kelly_pl.append(net_pl)
    
    strategies.append({
        'name': 'Kelly Criterion (25%)',
        'pl_list': kelly_pl,
        'total_pl': sum(kelly_pl),
        'avg_size': np.mean(kelly_sizes)
    })
    
    # Calculate additional stats
    for strat in strategies:
        wins = sum(1 for x in strat['pl_list'] if x > 0)
        losses = len(strat['pl_list']) - wins
        strat['wins'] = wins
        strat['losses'] = losses
        strat['win_rate'] = wins / len(strat['pl_list'])
        strat['avg_pl'] = strat['total_pl'] / len(strat['pl_list'])
        
        if wins > 0:
            strat['avg_win'] = np.mean([x for x in strat['pl_list'] if x > 0])
        else:
            strat['avg_win'] = 0
            
        if losses > 0:
            strat['avg_loss'] = np.mean([x for x in strat['pl_list'] if x < 0])
        else:
            strat['avg_loss'] = 0
    
    # Display results
    logger.info("\n" + "="*100)
    logger.info("RESULTS COMPARISON")
    logger.info("="*100)
    
    print(f"\n{'Strategy':<30} {'Avg Size':<12} {'Win Rate':<12} {'Total P/L':<15} {'Avg P/L':<12} {'Improvement'}")
    print("="*100)
    
    baseline = strategies[0]['total_pl']
    
    for strat in strategies:
        improvement = ((strat['total_pl'] - baseline) / abs(baseline) * 100) if baseline != 0 else 0
        print(f"{strat['name']:<30} {strat['avg_size']:<12.0f} {strat['win_rate']:<12.1%} ${strat['total_pl']:<14,.2f} ${strat['avg_pl']:<11.2f} {improvement:+.1f}%")
    
    # Find best
    best = max(strategies, key=lambda x: x['total_pl'])
    
    logger.info("\n" + "="*100)
    logger.info(f"BEST STRATEGY: {best['name']}")
    logger.info("="*100)
    logger.info(f"  Trades: {len(entries):,}")
    logger.info(f"  Avg Size: {best['avg_size']:.0f} contracts")
    logger.info(f"  Win Rate: {best['win_rate']:.1%}")
    logger.info(f"  Total P/L: ${best['total_pl']:,.2f}")
    logger.info(f"  Avg P/L: ${best['avg_pl']:.2f}")
    logger.info(f"  Avg Win: ${best['avg_win']:.2f}")
    logger.info(f"  Avg Loss: ${best['avg_loss']:.2f}")
    
    # Scale to 502 games
    test_games = test_df['game_id'].nunique()
    scale_factor = 502 / test_games
    
    logger.info(f"\n  SCALED TO 502 GAMES (from {test_games}):")
    logger.info(f"    Estimated Trades: {int(len(entries) * scale_factor):,}")
    logger.info(f"    Estimated P/L: ${best['total_pl'] * scale_factor:,.2f}")
    
    improvement_vs_fixed_500 = ((best['total_pl'] - strategies[1]['total_pl']) / abs(strategies[1]['total_pl']) * 100)
    logger.info(f"\n  IMPROVEMENT vs Fixed 500c: {improvement_vs_fixed_500:+.1f}%")
    
    return strategies, best


if __name__ == "__main__":
    strategies, best = test_dynamic_sizing()




