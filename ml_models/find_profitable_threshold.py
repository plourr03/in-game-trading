"""
Find which threshold is actually profitable
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


def find_profitable_threshold():
    """Find threshold that's actually profitable"""
    
    logger.info("="*100)
    logger.info("FINDING PROFITABLE THRESHOLD")
    logger.info("="*100)
    
    # Load data
    df = pd.read_csv('ml_models/outputs/advanced_training_data.csv')
    split_idx = int(len(df) * 0.8)
    test_df = df[split_idx:].copy()
    
    # Load model
    model = joblib.load('ml_models/outputs/advanced_model.pkl')
    features = joblib.load('ml_models/outputs/advanced_features.pkl')
    
    # Get predictions
    X_test = test_df[features].fillna(0).replace([np.inf, -np.inf], 0)
    test_df['pred_proba'] = model.predict_proba(X_test)[:, 1]
    
    # Test thresholds
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    
    results = []
    
    for threshold in thresholds:
        entries = test_df[test_df['pred_proba'] >= threshold].copy()
        
        if len(entries) == 0:
            continue
        
        # Calculate P/L with 100 contracts
        size = 100
        total_pl = 0
        wins = 0
        
        for idx, row in entries.iterrows():
            buy_fee = calculate_kalshi_fees(size, row['current_price'], is_taker=True)
            sell_price = row['current_price'] + row['profit_5min']
            sell_fee = calculate_kalshi_fees(size, sell_price, is_taker=True)
            
            gross_profit_cents = row['profit_5min'] * size
            total_fees_dollars = buy_fee + sell_fee
            net_profit_dollars = (gross_profit_cents / 100) - total_fees_dollars
            
            total_pl += net_profit_dollars
            if net_profit_dollars > 0:
                wins += 1
        
        win_rate = wins / len(entries) if len(entries) > 0 else 0
        avg_pl = total_pl / len(entries) if len(entries) > 0 else 0
        
        results.append({
            'threshold': threshold,
            'trades': len(entries),
            'win_rate': win_rate,
            'total_pl': total_pl,
            'avg_pl': avg_pl
        })
    
    # Display
    logger.info("\n" + "="*100)
    logger.info("RESULTS (100 contracts per trade)")
    logger.info("="*100)
    
    print(f"\n{'Threshold':<12} {'Trades':<10} {'Win Rate':<12} {'Total P/L':<15} {'Avg P/L':<12} {'Profitable?'}")
    print("="*100)
    
    for r in results:
        profitable = "YES" if r['total_pl'] > 0 else "NO"
        print(f"{r['threshold']:<12.2f} {r['trades']:<10} {r['win_rate']:<12.1%} ${r['total_pl']:<14.2f} ${r['avg_pl']:<11.2f} {profitable}")
    
    # Find best
    profitable = [r for r in results if r['total_pl'] > 0]
    
    if profitable:
        best = max(profitable, key=lambda x: x['total_pl'])
        
        logger.info("\n" + "="*100)
        logger.info(f"BEST PROFITABLE THRESHOLD: {best['threshold']:.2f}")
        logger.info("="*100)
        logger.info(f"  Trades: {best['trades']}")
        logger.info(f"  Win Rate: {best['win_rate']:.1%}")
        logger.info(f"  Total P/L: ${best['total_pl']:.2f}")
        logger.info(f"  Avg P/L: ${best['avg_pl']:.2f}")
        
        # Scale to 502 games
        test_games = test_df['game_id'].nunique()
        scale_factor = 502 / test_games
        scaled_pl = best['total_pl'] * scale_factor
        scaled_trades = int(best['trades'] * scale_factor)
        
        logger.info(f"\n  SCALED TO 502 GAMES:")
        logger.info(f"    Est. Trades: {scaled_trades:,}")
        logger.info(f"    Est. P/L (100c): ${scaled_pl:,.2f}")
        logger.info(f"    Est. P/L (500c): ${scaled_pl * 5:,.2f}")
    else:
        logger.info("\n❌ NO PROFITABLE THRESHOLDS FOUND")


if __name__ == "__main__":
    find_profitable_threshold()





