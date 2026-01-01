"""
Backtest Exit Strategies
Compares static (fixed 5-min hold) vs dynamic (ML-driven) exit strategies
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import pandas as pd
import numpy as np
import joblib
from glob import glob
from tqdm import tqdm
from src.backtesting.fees import calculate_kalshi_fees

print("="*80)
print("EXIT STRATEGY BACKTEST COMPARISON")
print("="*80)

# Load models
print("\nLoading models...")
entry_model = joblib.load('ml_models/outputs/advanced_model.pkl')
entry_features = joblib.load('ml_models/outputs/advanced_features.pkl')
exit_model_static = joblib.load('ml_models/outputs/exit_timing_model.pkl')  # Returns hold minutes
exit_model_dynamic = joblib.load('ml_models/outputs/exit_timing_dynamic.pkl')  # Returns exit probability
exit_features = joblib.load('ml_models/outputs/exit_features.pkl')

print(f"[OK] Entry model: {len(entry_features)} features")
print(f"[OK] Static exit model loaded")
print(f"[OK] Dynamic exit model: {len(exit_features)} features")

# Load test games
kalshi_files = glob('kalshi_data/jan_dec_2025_games/*_candles.csv')
print(f"[OK] Found {len(kalshi_files)} games to backtest")

# Entry threshold
ENTRY_THRESHOLD = 0.60
CONTRACTS = 500
EXIT_THRESHOLD_DYNAMIC = 0.70  # Probability threshold for dynamic exit

def calculate_exit_features(price_history, current_idx, entry_idx, entry_price):
    """Calculate features for exit decision"""
    features = {}
    current = price_history.iloc[current_idx]
    
    minutes_held = current_idx - entry_idx
    features['minutes_held'] = minutes_held
    features['entry_price'] = entry_price
    features['current_price'] = current['close']
    features['unrealized_pl'] = current['close'] - entry_price
    features['unrealized_pl_pct'] = (current['close'] - entry_price) / entry_price if entry_price > 0 else 0
    
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
        recent_prices = price_history.iloc[max(0, current_idx-5):current_idx+1]['close']
        features['price_volatility_5min'] = recent_prices.std()
    else:
        features['price_change_5min'] = 0
        features['price_volatility_5min'] = 0
    
    if entry_idx < current_idx:
        peak_price = price_history.iloc[entry_idx:current_idx+1]['close'].max()
        features['price_to_peak_ratio'] = current['close'] / peak_price if peak_price > 0 else 1.0
        features['from_peak_cents'] = peak_price - current['close']
    else:
        features['price_to_peak_ratio'] = 1.0
        features['from_peak_cents'] = 0
    
    features['time_remaining'] = 48 - current.get('game_minute', 0)
    features['is_late_game'] = 1 if features['time_remaining'] <= 5 else 0
    features['score_diff_change'] = 0
    features['price_rising'] = 1 if features['price_change_1min'] > 0 else 0
    features['price_falling'] = 1 if features['price_change_1min'] < 0 else 0
    features['hold_short'] = 1 if minutes_held <= 2 else 0
    features['hold_medium'] = 1 if 2 < minutes_held <= 5 else 0
    features['hold_long'] = 1 if minutes_held > 5 else 0
    
    return features

def backtest_game_static(df, entry_indices):
    """Backtest with static exit (fixed 5 minutes)"""
    trades = []
    
    for entry_idx in entry_indices:
        entry_price = df.iloc[entry_idx]['close']
        
        # Static: hold for 5 minutes
        exit_idx = min(entry_idx + 5, len(df) - 1)
        exit_price = df.iloc[exit_idx]['close']
        
        # Calculate P/L
        buy_fee = calculate_kalshi_fees(CONTRACTS, entry_price, is_taker=True)
        sell_fee = calculate_kalshi_fees(CONTRACTS, exit_price, is_taker=True)
        gross_profit = (exit_price - entry_price) * CONTRACTS / 100
        net_profit = gross_profit - buy_fee - sell_fee
        
        trades.append({
            'entry_idx': entry_idx,
            'exit_idx': exit_idx,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'hold_minutes': exit_idx - entry_idx,
            'net_profit': net_profit,
            'won': net_profit > 0
        })
    
    return trades

def backtest_game_dynamic(df, entry_indices):
    """Backtest with dynamic exit (ML-driven)"""
    trades = []
    
    for entry_idx in entry_indices:
        entry_price = df.iloc[entry_idx]['close']
        
        # Dynamic: check exit probability each minute
        exit_idx = entry_idx + 1  # Start checking next minute
        max_hold = 15  # Maximum hold duration
        
        for check_idx in range(entry_idx + 1, min(entry_idx + max_hold, len(df))):
            # Calculate exit features
            exit_feats = calculate_exit_features(df, check_idx, entry_idx, entry_price)
            
            # Ensure all required features are present
            feat_dict = {f: exit_feats.get(f, 0) for f in exit_features}
            X_exit = pd.DataFrame([feat_dict])[exit_features]
            
            # Get exit probability
            exit_prob = exit_model_dynamic.predict(X_exit)[0]
            
            if exit_prob >= EXIT_THRESHOLD_DYNAMIC:
                exit_idx = check_idx
                break
            
            exit_idx = check_idx  # If we reach here, exit at max hold
        
        exit_price = df.iloc[exit_idx]['close']
        
        # Calculate P/L
        buy_fee = calculate_kalshi_fees(CONTRACTS, entry_price, is_taker=True)
        sell_fee = calculate_kalshi_fees(CONTRACTS, exit_price, is_taker=True)
        gross_profit = (exit_price - entry_price) * CONTRACTS / 100
        net_profit = gross_profit - buy_fee - sell_fee
        
        trades.append({
            'entry_idx': entry_idx,
            'exit_idx': exit_idx,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'hold_minutes': exit_idx - entry_idx,
            'net_profit': net_profit,
            'won': net_profit > 0
        })
    
    return trades

# Run backtest
print("\nRunning backtest...")
print("-"*80)

static_trades = []
dynamic_trades = []

for kalshi_file in tqdm(kalshi_files[:100], desc="Backtesting"):  # Test on first 100 games
    try:
        df = pd.read_csv(kalshi_file)
        
        if len(df) < 20:
            continue
        
        df['close'] = df['close'].fillna(method='ffill')
        df['game_minute'] = df.get('game_minute', range(len(df)))
        
        # Find entry points (simple heuristic for testing)
        entry_indices = []
        for idx in range(15, len(df) - 15):
            price = df.iloc[idx]['close']
            if 20 < price < 80:  # Tradeable range
                # Skip if too close to previous entry
                if not entry_indices or idx - entry_indices[-1] > 10:
                    entry_indices.append(idx)
        
        if entry_indices:
            # Backtest both strategies
            static_trades.extend(backtest_game_static(df, entry_indices))
            dynamic_trades.extend(backtest_game_dynamic(df, entry_indices))
    
    except Exception as e:
        continue

# Results
print("\n" + "="*80)
print("BACKTEST RESULTS")
print("="*80)

def print_strategy_stats(trades, strategy_name):
    if not trades:
        print(f"\n{strategy_name}: No trades")
        return
    
    df_trades = pd.DataFrame(trades)
    total_pl = df_trades['net_profit'].sum()
    win_rate = (df_trades['won']).sum() / len(df_trades)
    avg_pl = df_trades['net_profit'].mean()
    avg_hold = df_trades['hold_minutes'].mean()
    
    # Sharpe ratio (simplified)
    if df_trades['net_profit'].std() > 0:
        sharpe = (avg_pl / df_trades['net_profit'].std()) * np.sqrt(len(df_trades))
    else:
        sharpe = 0
    
    print(f"\n{strategy_name}:")
    print(f"  Trades: {len(df_trades):,}")
    print(f"  Win Rate: {win_rate:.1%}")
    print(f"  Total P/L: ${total_pl:+,.2f}")
    print(f"  Avg P/L: ${avg_pl:+.2f}")
    print(f"  Avg Hold: {avg_hold:.1f} minutes")
    print(f"  Sharpe: {sharpe:.2f}")
    
    return {
        'trades': len(df_trades),
        'win_rate': win_rate,
        'total_pl': total_pl,
        'avg_pl': avg_pl,
        'avg_hold': avg_hold,
        'sharpe': sharpe
    }

static_stats = print_strategy_stats(static_trades, "STATIC EXIT (5-min hold)")
dynamic_stats = print_strategy_stats(dynamic_trades, "DYNAMIC EXIT (ML-driven)")

# Comparison
if static_stats and dynamic_stats:
    print("\n" + "="*80)
    print("IMPROVEMENT (Dynamic vs Static)")
    print("="*80)
    
    win_rate_diff = (dynamic_stats['win_rate'] - static_stats['win_rate']) * 100
    pl_diff = dynamic_stats['total_pl'] - static_stats['total_pl']
    pl_pct_diff = (pl_diff / abs(static_stats['total_pl'])) * 100 if static_stats['total_pl'] != 0 else 0
    hold_diff = dynamic_stats['avg_hold'] - static_stats['avg_hold']
    
    print(f"  Win Rate: {win_rate_diff:+.1f}%")
    print(f"  Total P/L: ${pl_diff:+,.2f} ({pl_pct_diff:+.1f}%)")
    print(f"  Avg Hold: {hold_diff:+.1f} minutes")
    print(f"  Sharpe: {dynamic_stats['sharpe'] - static_stats['sharpe']:+.2f}")

# Save results
results_df = pd.DataFrame({
    'strategy': ['static', 'dynamic'],
    'trades': [static_stats['trades'], dynamic_stats['trades']],
    'win_rate': [static_stats['win_rate'], dynamic_stats['win_rate']],
    'total_pl': [static_stats['total_pl'], dynamic_stats['total_pl']],
    'avg_pl': [static_stats['avg_pl'], dynamic_stats['avg_pl']],
    'avg_hold': [static_stats['avg_hold'], dynamic_stats['avg_hold']],
    'sharpe': [static_stats['sharpe'], dynamic_stats['sharpe']]
})

results_df.to_csv('ml_models/exit_strategy_comparison.csv', index=False)
print(f"\n[OK] Results saved to: ml_models/exit_strategy_comparison.csv")

print("\n" + "="*80)
print("[COMPLETE] Backtest finished!")
print("="*80)

