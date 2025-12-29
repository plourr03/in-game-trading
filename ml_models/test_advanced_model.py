"""
Test advanced features model at different thresholds to find optimal trade frequency
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


def test_advanced_model():
    """Test the advanced features model"""
    
    logger.info("="*100)
    logger.info("TESTING ADVANCED FEATURES MODEL")
    logger.info("="*100)
    
    # Load data
    logger.info("\nLoading test data...")
    df = pd.read_csv('ml_models/outputs/advanced_training_data.csv')
    
    # Time-based split
    split_idx = int(len(df) * 0.8)
    test_df = df[split_idx:].copy()
    logger.info(f"Test set: {len(test_df):,} samples")
    
    # Load model
    model = joblib.load('ml_models/outputs/advanced_model.pkl')
    features = joblib.load('ml_models/outputs/advanced_features.pkl')
    
    # Get predictions
    X_test = test_df[features].fillna(0)
    test_df['pred_proba'] = model.predict_proba(X_test)[:, 1]
    
    # Test at different thresholds
    logger.info("\n" + "="*100)
    logger.info("THRESHOLD TESTING")
    logger.info("="*100)
    
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
    results = []
    
    for threshold in thresholds:
        entries = test_df[test_df['pred_proba'] >= threshold].copy()
        
        if len(entries) == 0:
            continue
        
        # Simulate trading (using 5min hold as the target)
        entries['profit'] = entries['profit_5min']
        entries['won'] = (entries['profit'] > 3).astype(int)
        
        # Calculate fees
        entries['buy_fee'] = entries.apply(
            lambda row: calculate_kalshi_fees(row['current_price'], 100, 'buy'),
            axis=1
        )
        entries['sell_price'] = entries['current_price'] + entries['profit']
        entries['sell_fee'] = entries.apply(
            lambda row: calculate_kalshi_fees(row['sell_price'], 100, 'sell'),
            axis=1
        )
        entries['total_fee'] = entries['buy_fee'] + entries['sell_fee']
        entries['net_profit'] = entries['profit'] - entries['total_fee']
        
        # Stats
        trades = len(entries)
        wins = entries['won'].sum()
        losses = trades - wins
        win_rate = wins / trades if trades > 0 else 0
        
        avg_win = entries[entries['won'] == 1]['net_profit'].mean() if wins > 0 else 0
        avg_loss = entries[entries['won'] == 0]['net_profit'].mean() if losses > 0 else 0
        total_pl = entries['net_profit'].sum()
        
        results.append({
            'threshold': threshold,
            'trades': trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_pl_100': total_pl,
            'total_pl_500': total_pl * 5,
            'total_pl_1000': total_pl * 10
        })
    
    results_df = pd.DataFrame(results)
    
    print("\n" + "="*100)
    print("RESULTS (100 contracts per trade)")
    print("="*100)
    print(results_df[['threshold', 'trades', 'win_rate', 'total_pl_100']].to_string(index=False))
    
    # Find optimal threshold
    profitable = results_df[results_df['total_pl_500'] > 0].copy()
    
    if len(profitable) > 0:
        # Sort by: profitable AND high trade volume AND good win rate
        profitable['score'] = profitable['total_pl_500'] * (profitable['trades'] / profitable['trades'].max())
        best = profitable.loc[profitable['score'].idxmax()]
        
        print("\n" + "="*100)
        print(f"OPTIMAL THRESHOLD: {best['threshold']:.2f}")
        print("="*100)
        print(f"  Trades:        {int(best['trades'])}")
        print(f"  Win Rate:      {best['win_rate']:.1%}")
        print(f"  Avg Win:       ${best['avg_win']:.2f}")
        print(f"  Avg Loss:      ${best['avg_loss']:.2f}")
        print(f"  P/L (100):     ${best['total_pl_100']:.2f}")
        print(f"  P/L (500):     ${best['total_pl_500']:.2f}")
        print(f"  P/L (1000):    ${best['total_pl_1000']:.2f}")
        
        # Scale to full 502 games
        test_games = test_df['game_id'].nunique()
        full_trades = int(best['trades'] * (502 / test_games))
        full_pl_500 = best['total_pl_500'] * (502 / test_games)
        
        print(f"\n  SCALED TO FULL 502 GAMES:")
        print(f"     Estimated Trades:  {full_trades}")
        print(f"     Estimated P/L:     ${full_pl_500:.2f} (500 contracts)")
    else:
        print("\n❌ NO PROFITABLE THRESHOLDS FOUND")
        print("\nTrying best by trade volume:")
        best_volume = results_df.loc[results_df['trades'].idxmax()]
        print(f"\n  Threshold {best_volume['threshold']:.2f}:")
        print(f"    Trades: {int(best_volume['trades'])}")
        print(f"    Win Rate: {best_volume['win_rate']:.1%}")
        print(f"    P/L: ${best_volume['total_pl_100']:.2f}")
    
    # Save results
    results_df.to_csv('ml_models/outputs/advanced_threshold_results.csv', index=False)
    logger.info("\n✅ Saved: ml_models/outputs/advanced_threshold_results.csv")


if __name__ == "__main__":
    test_advanced_model()

