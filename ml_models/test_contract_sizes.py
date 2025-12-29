"""
Test different position sizes to find profitability
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


def test_position_sizes():
    """Test different position sizes"""
    
    logger.info("="*100)
    logger.info("TESTING DIFFERENT POSITION SIZES")
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
    
    # Filter entries at threshold 0.50
    entries = test_df[test_df['pred_proba'] >= 0.50].copy()
    
    logger.info(f"Testing {len(entries):,} entries")
    
    # Test different sizes
    sizes_to_test = [1, 10, 50, 100, 200, 500, 1000]
    
    results = []
    
    for size in sizes_to_test:
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
        
        win_rate = wins / len(entries)
        avg_pl = total_pl / len(entries)
        
        results.append({
            'contracts': size,
            'total_pl': total_pl,
            'avg_pl': avg_pl,
            'win_rate': win_rate,
            'wins': wins,
            'losses': len(entries) - wins
        })
    
    # Display
    logger.info("\n" + "="*100)
    logger.info("RESULTS")
    logger.info("="*100)
    
    print(f"\n{'Contracts':<12} {'Total P/L':<15} {'Avg P/L':<12} {'Win Rate':<12} {'Wins':<8} {'Losses'}")
    print("="*100)
    
    for r in results:
        print(f"{r['contracts']:<12} ${r['total_pl']:<14,.2f} ${r['avg_pl']:<11.2f} {r['win_rate']:<12.1%} {r['wins']:<8} {r['losses']}")
    
    # Scale profitable ones to 502 games
    test_games = test_df['game_id'].nunique()
    scale_factor = 502 / test_games
    
    logger.info(f"\n" + "="*100)
    logger.info(f"SCALED TO 502 GAMES (from {test_games} test games)")
    logger.info("="*100)
    
    print(f"\n{'Contracts':<12} {'Est. Trades':<15} {'Est. Total P/L'}")
    print("="*100)
    
    for r in results:
        scaled_trades = int(len(entries) * scale_factor)
        scaled_pl = r['total_pl'] * scale_factor
        profitable = " ✓" if scaled_pl > 0 else " ✗"
        print(f"{r['contracts']:<12} {scaled_trades:<15,} ${scaled_pl:,.2f}{profitable}")


if __name__ == "__main__":
    test_position_sizes()




