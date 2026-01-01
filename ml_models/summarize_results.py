"""Quick summary of ML results"""
import pandas as pd

print("\n" + "="*80)
print("ML PIPELINE RESULTS SUMMARY")
print("="*80)

# Training data
df = pd.read_csv('ml_models/outputs/training_data.csv')
print(f"\nTRAINING DATA:")
print(f"  Total Samples:     {len(df):,}")
print(f"  Games:             {df['game_id'].nunique()}")
print(f"  Profitable:        {df['any_profitable'].sum():,} ({df['any_profitable'].mean():.1%})")

# Backtest results
ml = pd.read_csv('ml_models/outputs/ml_backtest_trades.csv')
rules = pd.read_csv('ml_models/outputs/rules_backtest_trades.csv')

print("\n" + "="*80)
print("BACKTEST COMPARISON (20 Test Games)")
print("="*80)

print(f"\nML STRATEGY:")
print(f"  Total Trades:      {len(ml):,}")
print(f"  Win Rate:          {ml['is_winner'].mean():.1%}")
print(f"  Avg P/L per Trade: ${ml['net_pl'].mean():.2f}")
print(f"  Total P/L:         ${ml['net_pl'].sum():.2f}")
print(f"  Avg Fees:          ${ml['fees'].mean():.2f}")

print(f"\nRULES STRATEGY (1-5c, >20% move, 3min hold):")
print(f"  Total Trades:      {len(rules):,}")
print(f"  Win Rate:          {rules['is_winner'].mean():.1%}")
print(f"  Avg P/L per Trade: ${rules['net_pl'].mean():.2f}")
print(f"  Total P/L:         ${rules['net_pl'].sum():.2f}")
print(f"  Avg Fees:          ${rules['fees'].mean():.2f}")

print("\n" + "="*80)
print("VERDICT:")
print("="*80)

diff = ml['net_pl'].sum() - rules['net_pl'].sum()
if diff < -100:
    print(f"\nRules strategy performs better by ${abs(diff):.2f}")
    print(f"ML needs improvement:")
    print(f"  - Generated {len(ml)} trades vs {len(rules)} (may be too aggressive)")
    print(f"  - Win rate is {ml['is_winner'].mean():.1%} vs {rules['is_winner'].mean():.1%}")
    print(f"\nNEXT STEPS:")
    print(f"  1. Add more features (play-by-play data when available)")
    print(f"  2. Tune ML threshold for entry (currently 0.5, try 0.6-0.7)")
    print(f"  3. Try different algorithms (XGBoost, Neural Networks)")
else:
    print(f"\nML strategy performs better by ${diff:.2f}!")

print("\n" + "="*80)





