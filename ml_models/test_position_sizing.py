"""
IMPROVEMENT #3: Dynamic Position Sizing
Size positions based on model confidence, volatility, and recent performance
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


class DynamicPositionSizer:
    """
    Dynamically size positions based on:
    1. Model confidence (probability)
    2. Recent win/loss streak
    3. Market volatility
    """
    
    def __init__(self, base_size=100, max_size=1000, min_size=50):
        self.base_size = base_size
        self.max_size = max_size
        self.min_size = min_size
        self.recent_trades = []
        
    def calculate_size(self, probability, volatility):
        """
        Calculate optimal position size
        
        Args:
            probability: Model predicted probability (0-1)
            volatility: Recent price volatility
        """
        # 1. Confidence multiplier (higher probability = larger size)
        # Map 0.5-1.0 probability to 0.5-2.0x multiplier
        confidence_mult = 0.5 + (probability - 0.5) * 3.0
        confidence_mult = np.clip(confidence_mult, 0.5, 2.0)
        
        # 2. Streak multiplier (reduce after losses)
        if len(self.recent_trades) >= 3:
            last_3 = self.recent_trades[-3:]
            wins = sum(last_3)
            
            if wins == 0:  # 3 losses in a row
                streak_mult = 0.5
            elif wins == 1:  # 2 losses
                streak_mult = 0.75
            elif wins == 2:  # 2 wins
                streak_mult = 1.1
            elif wins == 3:  # 3 wins
                streak_mult = 1.25
            else:
                streak_mult = 1.0
        else:
            streak_mult = 1.0
        
        # 3. Volatility multiplier (reduce size in high volatility)
        # Normalize volatility (typical range 0-10)
        vol_mult = 1.5 - (volatility / 20.0)  # High vol = lower mult
        vol_mult = np.clip(vol_mult, 0.7, 1.3)
        
        # Calculate final size
        size = self.base_size * confidence_mult * streak_mult * vol_mult
        size = int(np.clip(size, self.min_size, self.max_size))
        
        return size
    
    def record_trade(self, won):
        """Record trade result for streak tracking"""
        self.recent_trades.append(1 if won else 0)
        # Keep only last 10 trades
        if len(self.recent_trades) > 10:
            self.recent_trades.pop(0)


def test_position_sizing():
    """Test dynamic position sizing vs fixed size"""
    
    logger.info("="*100)
    logger.info("TESTING DYNAMIC POSITION SIZING")
    logger.info("="*100)
    
    # Load data
    logger.info("\nLoading data...")
    df = pd.read_csv('ml_models/outputs/advanced_training_data.csv')
    split_idx = int(len(df) * 0.8)
    test_df = df[split_idx:].copy()
    
    # Load model (use CatBoost for simplicity)
    model = joblib.load('ml_models/outputs/advanced_model.pkl')
    features = joblib.load('ml_models/outputs/advanced_features.pkl')
    
    # Get predictions
    logger.info("Generating predictions...")
    X_test = test_df[features].fillna(0).replace([np.inf, -np.inf], 0)
    test_df['pred_proba'] = model.predict_proba(X_test)[:, 1]
    
    # Filter entries
    threshold = 0.50
    entries = test_df[test_df['pred_proba'] >= threshold].copy()
    logger.info(f"Found {len(entries):,} entries at threshold {threshold}")
    
    # Calculate volatility
    entries['volatility'] = entries['volatility_5min'].fillna(0)
    
    # Simulate both strategies
    logger.info("\n" + "="*100)
    logger.info("SIMULATING TRADING")
    logger.info("="*100)
    
    # Strategy 1: Fixed size (500 contracts)
    fixed_size = 500
    entries['profit_5min_net'] = entries['profit_5min'] - 2  # Approximate fees
    entries['won'] = (entries['profit_5min_net'] > 0).astype(int)
    
    fixed_pl = []
    for idx, row in entries.iterrows():
        buy_fee = calculate_kalshi_fees(row['current_price'], fixed_size, 'buy')
        sell_price = row['current_price'] + row['profit_5min']
        sell_fee = calculate_kalshi_fees(sell_price, fixed_size, 'sell')
        net_pl = (row['profit_5min'] - buy_fee - sell_fee) * fixed_size / 100
        fixed_pl.append(net_pl)
    
    entries['fixed_pl'] = fixed_pl
    
    # Strategy 2: Dynamic sizing
    sizer = DynamicPositionSizer(base_size=500, max_size=1000, min_size=100)
    
    dynamic_pl = []
    dynamic_sizes = []
    
    for idx, row in entries.iterrows():
        # Calculate dynamic size
        size = sizer.calculate_size(row['pred_proba'], row['volatility'])
        dynamic_sizes.append(size)
        
        # Calculate P/L
        buy_fee = calculate_kalshi_fees(row['current_price'], size, 'buy')
        sell_price = row['current_price'] + row['profit_5min']
        sell_fee = calculate_kalshi_fees(sell_price, size, 'sell')
        net_pl = (row['profit_5min'] - buy_fee - sell_fee) * size / 100
        dynamic_pl.append(net_pl)
        
        # Record result
        sizer.record_trade(row['won'])
    
    entries['dynamic_size'] = dynamic_sizes
    entries['dynamic_pl'] = dynamic_pl
    
    # Compare results
    logger.info(f"\n{'Strategy':<20} {'Trades':<10} {'Win Rate':<12} {'Total P/L':<15} {'Avg P/L'}")
    logger.info("="*100)
    
    fixed_total = entries['fixed_pl'].sum()
    fixed_avg = entries['fixed_pl'].mean()
    
    dynamic_total = entries['dynamic_pl'].sum()
    dynamic_avg = entries['dynamic_pl'].mean()
    
    logger.info(f"{'Fixed (500c)':<20} {len(entries):<10} {entries['won'].mean():<12.1%} ${fixed_total:<14.2f} ${fixed_avg:.2f}")
    logger.info(f"{'Dynamic':<20} {len(entries):<10} {entries['won'].mean():<12.1%} ${dynamic_total:<14.2f} ${dynamic_avg:.2f}")
    
    improvement = ((dynamic_total - fixed_total) / abs(fixed_total)) * 100 if fixed_total != 0 else 0
    logger.info(f"\n{'Improvement:':<20} {'':<10} {'':<12} ${dynamic_total - fixed_total:<14.2f} ({improvement:+.1f}%)")
    
    # Position size distribution
    logger.info("\n" + "="*100)
    logger.info("POSITION SIZE DISTRIBUTION")
    logger.info("="*100)
    
    size_bins = [0, 200, 400, 600, 800, 1000, 2000]
    size_labels = ['<200', '200-400', '400-600', '600-800', '800-1000', '1000+']
    entries['size_bin'] = pd.cut(entries['dynamic_size'], bins=size_bins, labels=size_labels)
    
    dist = entries.groupby('size_bin', observed=True).agg({
        'dynamic_size': 'count',
        'won': 'mean',
        'dynamic_pl': 'sum'
    }).rename(columns={'dynamic_size': 'trades', 'won': 'win_rate'})
    
    print("\n", dist.to_string())
    
    # Save position sizer
    joblib.dump(sizer, 'ml_models/outputs/position_sizer.pkl')
    logger.info("\n✅ Saved: ml_models/outputs/position_sizer.pkl")
    
    return sizer


if __name__ == "__main__":
    sizer = test_position_sizing()

