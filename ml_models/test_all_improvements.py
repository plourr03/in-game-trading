"""
FINAL TEST: All Improvements Combined
1. Exit Timing Optimization
2. Ensemble Models  
3. Dynamic Position Sizing
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


def test_all_improvements():
    """Test all 3 improvements combined"""
    
    logger.info("="*100)
    logger.info("🚀 TESTING ALL IMPROVEMENTS COMBINED")
    logger.info("="*100)
    
    # Load data
    logger.info("\nLoading test data...")
    df = pd.read_csv('ml_models/outputs/advanced_training_data.csv')
    split_idx = int(len(df) * 0.8)
    test_df = df[split_idx:].copy()
    
    # Load models
    logger.info("Loading models...")
    model = joblib.load('ml_models/outputs/advanced_model.pkl')  # Entry model
    exit_model = joblib.load('ml_models/outputs/exit_timing_model.pkl')  # Exit timing
    features = joblib.load('ml_models/outputs/advanced_features.pkl')
    
    # Prepare features
    X_test = test_df[features].fillna(0).replace([np.inf, -np.inf], 0)
    
    # Get entry predictions
    logger.info("Generating entry signals...")
    test_df['pred_proba'] = model.predict_proba(X_test)[:, 1]
    
    # Filter entries
    threshold = 0.50
    entries = test_df[test_df['pred_proba'] >= threshold].copy()
    logger.info(f"  Found {len(entries):,} potential entries")
    
    # Only use profitable opportunities
    entries = entries.dropna(subset=['profit_1min', 'profit_3min', 'profit_5min', 'profit_7min'])
    logger.info(f"  {len(entries):,} with complete data")
    
    # Get exit timing predictions
    logger.info("Predicting optimal exit timing...")
    X_entries = entries[features].fillna(0).replace([np.inf, -np.inf], 0)
    entries['predicted_hold'] = exit_model.predict(X_entries)
    
    # Calculate volatility for position sizing
    entries['volatility'] = entries['volatility_5min'].fillna(0)
    
    logger.info("\n" + "="*100)
    logger.info("COMPARING ALL STRATEGIES")
    logger.info("="*100)
    
    results = []
    
    # ===== BASELINE: Original (fixed 500c, 5min hold) =====
    logger.info("\n[1/4] Baseline (fixed 500c, 5min hold)...")
    baseline_pl = []
    for idx, row in entries.iterrows():
        size = 500
        buy_fee = calculate_kalshi_fees(row['current_price'], size, 'buy')
        sell_price = row['current_price'] + row['profit_5min']
        sell_fee = calculate_kalshi_fees(sell_price, size, 'sell')
        net_pl = (row['profit_5min'] - buy_fee - sell_fee) * size / 100
        baseline_pl.append(net_pl)
    
    results.append({
        'strategy': 'Baseline',
        'trades': len(entries),
        'total_pl': sum(baseline_pl),
        'avg_pl': np.mean(baseline_pl),
        'win_rate': sum(1 for x in baseline_pl if x > 0) / len(baseline_pl)
    })
    
    # ===== IMPROVEMENT 1: Exit Timing Only =====
    logger.info("[2/4] With exit timing optimization...")
    timing_pl = []
    for idx, row in entries.iterrows():
        size = 500
        hold = row['predicted_hold']
        profit = row[f'profit_{hold}min']
        
        buy_fee = calculate_kalshi_fees(row['current_price'], size, 'buy')
        sell_price = row['current_price'] + profit
        sell_fee = calculate_kalshi_fees(sell_price, size, 'sell')
        net_pl = (profit - buy_fee - sell_fee) * size / 100
        timing_pl.append(net_pl)
    
    results.append({
        'strategy': '+ Exit Timing',
        'trades': len(entries),
        'total_pl': sum(timing_pl),
        'avg_pl': np.mean(timing_pl),
        'win_rate': sum(1 for x in timing_pl if x > 0) / len(timing_pl)
    })
    
    # ===== IMPROVEMENT 2+3: Exit Timing + Dynamic Sizing =====
    logger.info("[3/4] With exit timing + dynamic sizing...")
    
    from ml_models.test_position_sizing import DynamicPositionSizer
    sizer = DynamicPositionSizer(base_size=500, max_size=1000, min_size=100)
    
    dynamic_pl = []
    dynamic_sizes = []
    
    for idx, row in entries.iterrows():
        # Dynamic size based on confidence
        size = sizer.calculate_size(row['pred_proba'], row['volatility'])
        dynamic_sizes.append(size)
        
        # Optimal hold period
        hold = row['predicted_hold']
        profit = row[f'profit_{hold}min']
        
        buy_fee = calculate_kalshi_fees(row['current_price'], size, 'buy')
        sell_price = row['current_price'] + profit
        sell_fee = calculate_kalshi_fees(sell_price, size, 'sell')
        net_pl = (profit - buy_fee - sell_fee) * size / 100
        dynamic_pl.append(net_pl)
        
        # Record for streak tracking
        sizer.record_trade(net_pl > 0)
    
    results.append({
        'strategy': '+ Dynamic Sizing',
        'trades': len(entries),
        'total_pl': sum(dynamic_pl),
        'avg_pl': np.mean(dynamic_pl),
        'win_rate': sum(1 for x in dynamic_pl if x > 0) / len(dynamic_pl),
        'avg_size': np.mean(dynamic_sizes)
    })
    
    # ===== SCALE TO FULL 502 GAMES =====
    test_games = test_df['game_id'].nunique()
    scale_factor = 502 / test_games
    
    logger.info(f"[4/4] Scaling to full 502 games (factor: {scale_factor:.2f})...")
    
    # Display results
    logger.info("\n" + "="*100)
    logger.info("📊 RESULTS COMPARISON (Test Set)")
    logger.info("="*100)
    
    results_df = pd.DataFrame(results)
    
    print(f"\n{'Strategy':<25} {'Trades':<10} {'Win Rate':<12} {'Total P/L':<18} {'Avg P/L':<12} {'Improvement'}")
    print("="*100)
    
    baseline_total = results_df.iloc[0]['total_pl']
    
    for idx, row in results_df.iterrows():
        improvement = ((row['total_pl'] - baseline_total) / abs(baseline_total)) * 100 if baseline_total != 0 else 0
        avg_size_str = f"(avg {row['avg_size']:.0f}c)" if 'avg_size' in row else ""
        
        print(f"{row['strategy']:<25} {row['trades']:<10} {row['win_rate']:<12.1%} ${row['total_pl']:<17,.2f} ${row['avg_pl']:<11.2f} {improvement:+.1f}% {avg_size_str}")
    
    # Scaled results
    logger.info("\n" + "="*100)
    logger.info(f"📈 SCALED TO FULL 502 GAMES (from {test_games} test games)")
    logger.info("="*100)
    
    print(f"\n{'Strategy':<25} {'Est. Trades':<15} {'Est. Total P/L'}")
    print("="*100)
    
    for idx, row in results_df.iterrows():
        scaled_trades = int(row['trades'] * scale_factor)
        scaled_pl = row['total_pl'] * scale_factor
        print(f"{row['strategy']:<25} {scaled_trades:<15,} ${scaled_pl:,.2f}")
    
    # Final summary
    final_total = results_df.iloc[-1]['total_pl'] * scale_factor
    baseline_scaled = results_df.iloc[0]['total_pl'] * scale_factor
    total_improvement = final_total - baseline_scaled
    pct_improvement = (total_improvement / abs(baseline_scaled)) * 100
    
    logger.info("\n" + "="*100)
    logger.info("🎯 FINAL IMPROVEMENT")
    logger.info("="*100)
    logger.info(f"  Baseline:           ${baseline_scaled:,.2f}")
    logger.info(f"  With Improvements:  ${final_total:,.2f}")
    logger.info(f"  Net Gain:           ${total_improvement:,.2f} ({pct_improvement:+.1f}%)")
    
    return results_df


if __name__ == "__main__":
    results = test_all_improvements()




