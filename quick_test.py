"""Test edge profitability with CORRECT fee calculation"""
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
from src.backtesting.fees import calculate_kalshi_fees
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("CORRECTED PROFITABILITY TEST")
print("=" * 80)

# Load
kalshi = load_kalshi_games()
kalshi = fill_prices(kalshi)

# Calculate changes
kalshi['pc'] = kalshi.groupby('game_id')['close'].diff()
kalshi['pc_lag2'] = kalshi.groupby('game_id')['pc'].shift(-2)

# Large moves
large = kalshi[kalshi['pc'].abs() > 5].copy()
print(f"\nTesting {len(large):,} large moves")

# Simulate
trades = []
for _, row in large.iterrows():
    if pd.notna(row['pc_lag2']):
        # Entry
        entry_price = row['close']
        move_dir = np.sign(row['pc'])
        
        # Exit 2min later
        exit_price = entry_price + row['pc_lag2']
        exit_price = np.clip(exit_price, 1, 99)
        
        # Did it reverse?
        reversal = (move_dir * row['pc_lag2']) < 0
        
        # P&L (100 contracts)
        if reversal:
            profit_pct = abs(row['pc_lag2'])
        else:
            profit_pct = -abs(row['pc_lag2'])
        
        gross_pl = profit_pct  # In percentage points
        
        # CORRECT fee calc: ~7% of (P * (1-P)) per 100 contracts  
        entry_fee = 0.07 * (entry_price/100) * (1 - entry_price/100) * 100
        exit_fee = 0.07 * (exit_price/100) * (1 - exit_price/100) * 100
        total_fee_pct = (entry_fee + exit_fee) / 100 * 100  # As percentage points
        
        net_pl = gross_pl - total_fee_pct
        
        trades.append({
            'reversal': reversal,
            'gross_pl': gross_pl,
            'fees': total_fee_pct,
            'net_pl': net_pl
        })

df = pd.DataFrame(trades)

print(f"\nWin Rate: {df['reversal'].mean():.1%}")
print(f"Avg gross P/L: {df['gross_pl'].mean():.2f}%")
print(f"Avg fees: {df['fees'].mean():.2f}%")
print(f"Avg NET P/L: {df['net_pl'].mean():.2f}%")

print(f"\nPer $100 position:")
print(f"  Avg net: ${df['net_pl'].mean():.2f}")
print(f"  Total over {len(df)} trades: ${df['net_pl'].sum():.2f}")
print(f"  Per game: ${df['net_pl'].sum() / 502:.2f}")

if df['net_pl'].mean() > 0:
    print("\n[OK] PROFITABLE!")
    print(f"Expected: ${df['net_pl'].sum() / 502 * 500:.0f}/year (500 games)")
else:
    print("\n[X] NOT PROFITABLE")
    
print("\n" + "=" * 80)

