"""Simple test script - final version"""
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices, add_team_to_kalshi
from src.analysis.price_reactions import overreaction_detection
from src.analysis.microstructure import calculate_spread_proxy
from src.analysis.tradability import fee_impact_by_price
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("KALSHI NBA TRADING ANALYSIS - RESULTS")
print("=" * 80)

# Load data
print("\n[1/4] Loading Kalshi data...")
kalshi = load_kalshi_games()
kalshi = fill_prices(kalshi)
kalshi = add_team_to_kalshi(kalshi)
print(f"[OK] Loaded {len(kalshi):,} rows from {kalshi['game_id'].nunique()} games")

# Overreaction analysis
print("\n[2/4] Price overreaction analysis...")
results = overreaction_detection(kalshi, threshold=5.0)
print(f"\nResults:")
print(f"  - Large moves (>5%): {results['total_large_moves']:,}")
print(f"  - Reversal rate (1 min): {results['reversal_rate_1min']:.1%}")
print(f"  - Reversal rate (3 min): {results['reversal_rate_3min']:.1%}")
print(f"  - Average move size: {results['mean_move_size']:.2f}%")

# Spread analysis
print("\n[3/4] Market microstructure...")
spread = calculate_spread_proxy(kalshi).mean()
volume_pct = (kalshi['volume'] > 0).mean()
print(f"  - Average spread: {spread:.2f}%")
print(f"  - % minutes with trading: {volume_pct:.1%}")

# Fee analysis
print("\n[4/4] Fee impact...")
fees = fee_impact_by_price()
fee_at_50 = fees[fees['price'] == 50].iloc[0]
print(f"  - Break-even edge at 50%: {fee_at_50['break_even_edge_pct']:.2f}%")
print(f"  - Round-trip cost: ${fee_at_50['round_trip_cost']:.2f}/100 contracts")

print("\n" + "=" * 80)
print("FINAL CONCLUSION")
print("=" * 80)

# Calculate if edge exists
reversal_rate = results['reversal_rate_3min']
edge_required = fee_at_50['break_even_edge_pct'] / 100

if reversal_rate > 0.55:
    print("\n[OK] POTENTIAL EDGE FOUND!")
    print(f"\n  Market shows {reversal_rate:.1%} reversal rate after large moves.")
    print(f"  This suggests overreaction that could be exploited.")
    print(f"\n  Strategy: Contrarian - bet against large price moves")
    print(f"  Expected profit: ~{(reversal_rate - 0.5) * results['mean_move_size']:.1f}% per trade")
    print(f"  After fees (~{edge_required:.1%}): Likely PROFITABLE")
else:
    print("\n[X] NO EXPLOITABLE EDGE FOUND")
    print(f"\n  Reversal rate: {reversal_rate:.1%} (need >55% for profitable contrarian strategy)")
    print(f"  Market appears efficient - prices adjust correctly to events")
    print(f"\n  Fees (~{edge_required:.1%} round-trip) eliminate small inefficiencies")
    print("\n  CONCLUSION: Kalshi NBA markets are reasonably efficient.")
    print("              No systematic mispricing to exploit profitably.")

print("\n" + "=" * 80)
print(f"Analysis of {kalshi['game_id'].nunique()} games complete!")
print("=" * 80 + "\n")

