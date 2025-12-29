"""
CORRECTED TEST: All improvements with proper fee calculations
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


def calculate_pl_correctly(row, size, hold_period='5min'):
    """Calculate P/L with correct fee calculation"""
    buy_fee = calculate_kalshi_fees(size, row['current_price'], is_taker=True)
    
    profit = row[f'profit_{hold_period}']
    sell_price = row['current_price'] + profit
    sell_fee = calculate_kalshi_fees(size, sell_price, is_taker=True)
    
    gross_profit_cents = profit * size
    total_fees_dollars = buy_fee + sell_fee
    net_profit_dollars = (gross_profit_cents / 100) - total_fees_dollars
    
    return net_profit_dollars


def test_all_improvements_corrected():
    """Test all improvements with correct fee calculations"""
    
    logger.info("="*100)
    logger.info("CORRECTED FULL TEST - All Improvements")
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
    
    # Test at different thresholds
    thresholds_to_test = [0.60, 0.65, 0.70, 0.75]
    
    all_results = []
    
    for threshold in thresholds_to_test:
        logger.info(f"\n{'='*100}")
        logger.info(f"TESTING THRESHOLD: {threshold:.2f}")
        logger.info(f"{'='*100}")
        
        entries = test_df[test_df['pred_proba'] >= threshold].copy()
        
        if len(entries) == 0:
            continue
        
        # Filter to entries with complete hold data
        entries = entries.dropna(subset=['profit_1min', 'profit_3min', 'profit_5min', 'profit_7min'])
        
        if len(entries) == 0:
            continue
        
        logger.info(f"  {len(entries):,} entries found")
        
        # Predict exit timing
        X_entries = entries[features].fillna(0).replace([np.inf, -np.inf], 0)
        entries['predicted_hold'] = exit_model.predict(X_entries)
        
        entries['volatility'] = entries['volatility_5min'].fillna(0)
        
        # ===== STRATEGY 1: Baseline (fixed 100c, 5min hold) =====
        logger.info("\n  [1/4] Baseline (100c, 5min)...")
        baseline_pl = []
        for idx, row in entries.iterrows():
            net_pl = calculate_pl_correctly(row, 100, '5min')
            baseline_pl.append(net_pl)
        
        baseline_total = sum(baseline_pl)
        baseline_wins = sum(1 for x in baseline_pl if x > 0)
        baseline_wr = baseline_wins / len(baseline_pl)
        
        logger.info(f"      Trades: {len(entries):,}, Win Rate: {baseline_wr:.1%}, P/L: ${baseline_total:.2f}")
        
        # ===== STRATEGY 2: With Exit Timing =====
        logger.info("  [2/4] + Exit Timing...")
        timing_pl = []
        for idx, row in entries.iterrows():
            hold = str(row['predicted_hold']) + 'min'
            net_pl = calculate_pl_correctly(row, 100, hold)
            timing_pl.append(net_pl)
        
        timing_total = sum(timing_pl)
        timing_wins = sum(1 for x in timing_pl if x > 0)
        timing_wr = timing_wins / len(timing_pl)
        timing_improvement = ((timing_total - baseline_total) / abs(baseline_total) * 100) if baseline_total != 0 else 0
        
        logger.info(f"      Trades: {len(entries):,}, Win Rate: {timing_wr:.1%}, P/L: ${timing_total:.2f} ({timing_improvement:+.1f}%)")
        
        # ===== STRATEGY 3: With Dynamic Sizing =====
        logger.info("  [3/4] + Dynamic Sizing...")
        
        dynamic_pl = []
        dynamic_sizes = []
        
        for idx, row in entries.iterrows():
            # Calculate size based on confidence (50-150 range for safer sizing)
            confidence = row['pred_proba']
            size = int(50 + (confidence - threshold) * 500)  # Scale from 50 to 150 based on confidence above threshold
            size = np.clip(size, 50, 150)
            dynamic_sizes.append(size)
            
            # Use predicted hold
            hold = str(row['predicted_hold']) + 'min'
            net_pl = calculate_pl_correctly(row, size, hold)
            dynamic_pl.append(net_pl)
        
        dynamic_total = sum(dynamic_pl)
        dynamic_wins = sum(1 for x in dynamic_pl if x > 0)
        dynamic_wr = dynamic_wins / len(dynamic_pl)
        dynamic_improvement = ((dynamic_total - baseline_total) / abs(baseline_total) * 100) if baseline_total != 0 else 0
        avg_size = np.mean(dynamic_sizes)
        
        logger.info(f"      Trades: {len(entries):,}, Win Rate: {dynamic_wr:.1%}, P/L: ${dynamic_total:.2f} ({dynamic_improvement:+.1f}%), Avg Size: {avg_size:.0f}c")
        
        # ===== STRATEGY 4: Scaled to 100c equivalent =====
        # Scale to 500c for comparison
        scaling_factor_500 = 5  # 100c -> 500c
        
        all_results.append({
            'threshold': threshold,
            'trades': len(entries),
            'baseline_pl_100': baseline_total,
            'timing_pl_100': timing_total,
            'dynamic_pl_100': dynamic_total,
            'baseline_pl_500': baseline_total * scaling_factor_500,
            'timing_pl_500': timing_total * scaling_factor_500,
            'dynamic_pl_500': dynamic_total * scaling_factor_500,
            'baseline_wr': baseline_wr,
            'timing_wr': timing_wr,
            'dynamic_wr': dynamic_wr
        })
    
    # Summary
    logger.info("\n" + "="*100)
    logger.info("SUMMARY - ALL THRESHOLDS")
    logger.info("="*100)
    
    print(f"\n{'Threshold':<12} {'Trades':<10} {'Baseline':<15} {'+ Exit':<15} {'+ Dynamic':<15} {'Best WR'}")
    print("="*100)
    
    for r in all_results:
        print(f"{r['threshold']:<12.2f} {r['trades']:<10} ${r['baseline_pl_100']:<14.2f} ${r['timing_pl_100']:<14.2f} ${r['dynamic_pl_100']:<14.2f} {r['dynamic_wr']:.1%}")
    
    # Find best
    best = max(all_results, key=lambda x: x['dynamic_pl_100'])
    
    logger.info("\n" + "="*100)
    logger.info(f"BEST CONFIGURATION: Threshold {best['threshold']:.2f}")
    logger.info("="*100)
    logger.info(f"  Trades: {best['trades']:,}")
    logger.info(f"  Win Rate: {best['dynamic_wr']:.1%}")
    logger.info(f"  Total P/L (100c): ${best['dynamic_pl_100']:.2f}")
    logger.info(f"  Total P/L (500c): ${best['dynamic_pl_500']:.2f}")
    
    # Scale to 502 games
    test_games = test_df['game_id'].nunique()
    scale_factor = 502 / test_games
    
    logger.info(f"\n  SCALED TO 502 GAMES (from {test_games}):")
    logger.info(f"    Estimated Trades: {int(best['trades'] * scale_factor):,}")
    logger.info(f"    Estimated P/L (100c): ${best['dynamic_pl_100'] * scale_factor:,.2f}")
    logger.info(f"    Estimated P/L (500c): ${best['dynamic_pl_500'] * scale_factor:,.2f}")
    
    # Improvement summary
    improvement_vs_baseline = ((best['dynamic_pl_100'] - best['baseline_pl_100']) / abs(best['baseline_pl_100']) * 100) if best['baseline_pl_100'] != 0 else 0
    
    logger.info(f"\n  IMPROVEMENT OVER BASELINE:")
    logger.info(f"    Baseline: ${best['baseline_pl_100']:.2f}")
    logger.info(f"    With All Improvements: ${best['dynamic_pl_100']:.2f}")
    logger.info(f"    Net Gain: ${best['dynamic_pl_100'] - best['baseline_pl_100']:.2f} ({improvement_vs_baseline:+.1f}%)")
    
    return all_results


if __name__ == "__main__":
    results = test_all_improvements_corrected()




