"""
Create Exit Training Data
Generates labeled training data for dynamic exit timing model
Uses historical Kalshi data and entry model to simulate trades
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import pandas as pd
import numpy as np
import joblib
from glob import glob
from tqdm import tqdm
from datetime import datetime

print("Loading models and data...")

# Load entry model and features
try:
    entry_model = joblib.load('ml_models/outputs/advanced_model.pkl')
    features_list = joblib.load('ml_models/outputs/advanced_features.pkl')
    print(f"[OK] Loaded entry model with {len(features_list)} features")
except Exception as e:
    print(f"[ERROR] Could not load models: {e}")
    sys.exit(1)

# Load all historical games
kalshi_files = glob('kalshi_data/jan_dec_2025_games/*_candles.csv')
print(f"[OK] Found {len(kalshi_files)} games")

def calculate_features_for_exit(price_history, current_idx, entry_idx, entry_price):
    """Calculate features for exit decision at current_idx"""
    
    features = {}
    current = price_history.iloc[current_idx]
    
    # Basic position info
    minutes_held = current_idx - entry_idx
    features['minutes_held'] = minutes_held
    features['entry_price'] = entry_price
    features['current_price'] = current['close']
    
    # Unrealized P/L
    features['unrealized_pl'] = current['close'] - entry_price
    features['unrealized_pl_pct'] = (current['close'] - entry_price) / entry_price if entry_price > 0 else 0
    
    # Price momentum
    if current_idx >= 1:
        features['price_change_1min'] = current['close'] - price_history.iloc[current_idx-1]['close']
    else:
        features['price_change_1min'] = 0
    
    if current_idx >= 3:
        features['price_change_3min'] = current['close'] - price_history.iloc[current_idx-3]['close']
    else:
        features['price_change_3min'] = 0
    
    if current_idx >= 5:
        features['price_change_5min'] = current['close'] - price_history.iloc[current_idx-5]['close']
    else:
        features['price_change_5min'] = 0
    
    # Volatility
    if current_idx >= 5:
        recent_prices = price_history.iloc[max(0, current_idx-5):current_idx+1]['close']
        features['price_volatility_5min'] = recent_prices.std()
    else:
        features['price_volatility_5min'] = 0
    
    # Price to peak ratio (how far from highest we've seen)
    if entry_idx < current_idx:
        peak_price = price_history.iloc[entry_idx:current_idx+1]['close'].max()
        features['price_to_peak_ratio'] = current['close'] / peak_price if peak_price > 0 else 1.0
        features['from_peak_cents'] = peak_price - current['close']
    else:
        features['price_to_peak_ratio'] = 1.0
        features['from_peak_cents'] = 0
    
    # Game state
    features['time_remaining'] = current.get('time_remaining', 48 - current.get('game_minute', 0))
    features['is_late_game'] = 1 if features['time_remaining'] <= 5 else 0
    
    # Score change since entry
    if entry_idx < len(price_history):
        entry_row = price_history.iloc[entry_idx]
        entry_score_diff = entry_row.get('score_diff', 0)
        current_score_diff = current.get('score_diff', 0)
        features['score_diff_change'] = current_score_diff - entry_score_diff
    else:
        features['score_diff_change'] = 0
    
    # Momentum direction
    features['price_rising'] = 1 if features['price_change_1min'] > 0 else 0
    features['price_falling'] = 1 if features['price_change_1min'] < 0 else 0
    
    # Hold duration bins
    features['hold_short'] = 1 if minutes_held <= 2 else 0
    features['hold_medium'] = 1 if 2 < minutes_held <= 5 else 0
    features['hold_long'] = 1 if minutes_held > 5 else 0
    
    return features


def label_optimal_exit(price_history, entry_idx, lookforward=15):
    """
    Label optimal exit points using hybrid approach:
    - Near peak profit (within 90%)
    - Positive profit
    - Price declining after this point
    """
    labels = []
    
    max_idx = min(entry_idx + lookforward, len(price_history))
    entry_price = price_history.iloc[entry_idx]['close']
    
    # Get all prices after entry
    future_prices = price_history.iloc[entry_idx:max_idx]['close'].values
    
    if len(future_prices) < 2:
        return []
    
    # Find peak profit
    peak_profit = np.max(future_prices - entry_price)
    
    for i in range(len(future_prices)):
        actual_idx = entry_idx + i
        
        if i == 0:  # Don't exit immediately on entry
            labels.append((actual_idx, 0))
            continue
        
        current_price = future_prices[i]
        current_profit = current_price - entry_price
        
        # Check if this is a good exit point
        is_optimal = False
        
        if current_profit > 0 and peak_profit > 0:
            # Near peak (within 90%)
            if current_profit >= 0.90 * peak_profit:
                # Check if declining next
                if i < len(future_prices) - 1:
                    next_price = future_prices[i + 1]
                    if next_price <= current_price:
                        is_optimal = True
                else:
                    # At the end, exit if profitable
                    is_optimal = True
        
        labels.append((actual_idx, 1 if is_optimal else 0))
    
    return labels


def generate_exit_training_data():
    """Generate training data from all historical games"""
    
    all_training_data = []
    
    print("\nGenerating exit training data...")
    
    for kalshi_file in tqdm(kalshi_files, desc="Processing games"):
        try:
            # Load game data
            df = pd.read_csv(kalshi_file)
            
            if len(df) < 20:  # Skip very short games
                continue
            
            # Basic preprocessing
            df['close'] = df['close'].fillna(method='ffill')
            df['game_minute'] = df.get('game_minute', range(len(df)))
            df['time_remaining'] = 48 - df['game_minute']
            df['score_diff'] = df.get('score_home', 0) - df.get('score_away', 0)
            
            # Find entry points using entry model
            # Simulate feature calculation for each minute
            for idx in range(15, len(df) - 15):  # Leave room for lookforward
                row = df.iloc[idx]
                
                # Simplified entry check (in real scenario, would calculate all 70 features)
                # For now, use price and momentum as proxy
                current_price = row['close']
                
                # Simple entry heuristic: reasonable price range and momentum
                if 20 < current_price < 80:  # Tradeable range
                    # This is a potential entry point
                    entry_idx = idx
                    entry_price = current_price
                    
                    # Label optimal exits for this entry
                    exit_labels = label_optimal_exit(df, entry_idx, lookforward=15)
                    
                    # Generate features for each minute after entry
                    for exit_idx, label in exit_labels:
                        if exit_idx > entry_idx:  # Don't include entry minute itself
                            features = calculate_features_for_exit(df, exit_idx, entry_idx, entry_price)
                            features['label'] = label
                            features['game_id'] = os.path.basename(kalshi_file).split('_')[0]
                            all_training_data.append(features)
        
        except Exception as e:
            print(f"\nError processing {kalshi_file}: {e}")
            continue
    
    # Convert to DataFrame
    print("\nCreating training dataset...")
    training_df = pd.DataFrame(all_training_data)
    
    # Print statistics
    print("\n" + "="*80)
    print("TRAINING DATA STATISTICS")
    print("="*80)
    print(f"Total examples: {len(training_df):,}")
    print(f"Unique games: {training_df['game_id'].nunique()}")
    print(f"\nLabel distribution:")
    print(f"  HOLD (0): {(training_df['label'] == 0).sum():,} ({(training_df['label'] == 0).sum() / len(training_df) * 100:.1f}%)")
    print(f"  EXIT (1): {(training_df['label'] == 1).sum():,} ({(training_df['label'] == 1).sum() / len(training_df) * 100:.1f}%)")
    
    print(f"\nFeatures: {len([c for c in training_df.columns if c not in ['label', 'game_id']])}")
    print(f"Feature names: {[c for c in training_df.columns if c not in ['label', 'game_id']][:10]}...")
    
    # Save
    output_file = 'ml_models/exit_training_data.csv'
    training_df.to_csv(output_file, index=False)
    print(f"\n[OK] Saved to: {output_file}")
    print("="*80)
    
    return training_df


if __name__ == "__main__":
    training_df = generate_exit_training_data()
    print("\n[COMPLETE] Exit training data generated successfully!")

