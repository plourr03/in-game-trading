"""
VERIFICATION: Check if the numbers are correct
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


def verify_calculations():
    """Verify the profit calculations are correct"""
    
    logger.info("="*100)
    logger.info("VERIFICATION: Checking calculations")
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
    
    # Filter entries
    entries = test_df[test_df['pred_proba'] >= 0.50].copy()
    logger.info(f"\nTotal entries: {len(entries):,}")
    
    # Check a few examples manually
    logger.info("\n" + "="*100)
    logger.info("MANUAL CALCULATION CHECK (first 5 trades)")
    logger.info("="*100)
    
    sample = entries.head(5)
    
    for idx, row in sample.iterrows():
        logger.info(f"\nTrade {idx}:")
        logger.info(f"  Current price: {row['current_price']:.1f}¢")
        logger.info(f"  Profit_5min: {row['profit_5min']:.1f}¢")
        logger.info(f"  Exit price: {row['current_price'] + row['profit_5min']:.1f}¢")
        
        # Calculate fees for 500 contracts
        size = 500
        buy_fee = calculate_kalshi_fees(size, row['current_price'], is_taker=True)
        sell_price = row['current_price'] + row['profit_5min']
        sell_fee = calculate_kalshi_fees(size, sell_price, is_taker=True)
        
        logger.info(f"  Buy fee (500c): ${buy_fee:.2f}")
        logger.info(f"  Sell fee (500c): ${sell_fee:.2f}")
        logger.info(f"  Total fees: ${buy_fee + sell_fee:.2f}")
        
        # Net profit calculation
        gross_profit = row['profit_5min'] * size  # cents * contracts
        net_profit_cents = gross_profit - (buy_fee + sell_fee) * 100  # Convert fees back to cents
        net_profit_dollars = net_profit_cents / 100
        
        logger.info(f"  Gross profit: {gross_profit:.1f}¢ = ${gross_profit/100:.2f}")
        logger.info(f"  Net profit: {net_profit_cents:.1f}¢ = ${net_profit_dollars:.2f}")
        
        # Check if profitable
        is_win = net_profit_dollars > 0
        logger.info(f"  Result: {'WIN' if is_win else 'LOSS'}")
    
    # Now calculate for all trades
    logger.info("\n" + "="*100)
    logger.info("FULL TEST SET CALCULATION")
    logger.info("="*100)
    
    total_pl = 0
    wins = 0
    losses = 0
    
    for idx, row in entries.iterrows():
        size = 500
        buy_fee = calculate_kalshi_fees(size, row['current_price'], is_taker=True)
        sell_price = row['current_price'] + row['profit_5min']
        sell_fee = calculate_kalshi_fees(size, sell_price, is_taker=True)
        
        # Net profit in dollars
        gross_profit_cents = row['profit_5min'] * size
        total_fees_dollars = buy_fee + sell_fee
        net_profit_dollars = (gross_profit_cents / 100) - total_fees_dollars
        
        total_pl += net_profit_dollars
        
        if net_profit_dollars > 0:
            wins += 1
        else:
            losses += 1
    
    win_rate = wins / len(entries) if len(entries) > 0 else 0
    avg_pl = total_pl / len(entries) if len(entries) > 0 else 0
    
    logger.info(f"\nTotal trades: {len(entries):,}")
    logger.info(f"Wins: {wins:,}")
    logger.info(f"Losses: {losses:,}")
    logger.info(f"Win rate: {win_rate:.1%}")
    logger.info(f"Total P/L: ${total_pl:,.2f}")
    logger.info(f"Average P/L: ${avg_pl:.2f}")
    
    # Scale to full 502 games
    test_games = test_df['game_id'].nunique()
    scale_factor = 502 / test_games
    
    scaled_trades = int(len(entries) * scale_factor)
    scaled_pl = total_pl * scale_factor
    
    logger.info(f"\n" + "="*100)
    logger.info(f"SCALED TO 502 GAMES (from {test_games} test games)")
    logger.info(f"="*100)
    logger.info(f"Estimated trades: {scaled_trades:,}")
    logger.info(f"Estimated P/L: ${scaled_pl:,.2f}")
    
    # Compare to original claim
    logger.info("\n" + "="*100)
    logger.info("COMPARISON TO ORIGINAL TEST")
    logger.info("="*100)
    logger.info(f"Original claim: $16,650 (500 contracts)")
    logger.info(f"Verified result: ${scaled_pl:,.2f}")
    
    return total_pl, scaled_pl


if __name__ == "__main__":
    verify_calculations()

