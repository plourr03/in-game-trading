"""Comprehensive edge detection - test ALL hypotheses"""
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices, add_team_to_kalshi
from src.analysis.price_reactions import overreaction_detection, price_change_after_event
from src.analysis.efficiency import autocorrelation_analysis
from src.analysis.segmentation import segment_by_pregame_odds, segment_by_final_margin
from src.backtesting.fees import calculate_round_trip_cost
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("COMPREHENSIVE EDGE DETECTION ANALYSIS")
print("Testing Multiple Hypotheses Across 502 Games")
print("=" * 80)

# Load data
print("\nLoading data...")
kalshi = load_kalshi_games()
kalshi = fill_prices(kalshi)
kalshi = add_team_to_kalshi(kalshi)
print(f"Loaded {len(kalshi):,} rows from {kalshi['game_id'].nunique()} games")

edges_found = []

# ============================================================================
# HYPOTHESIS 1: Overreaction at Different Thresholds
# ============================================================================
print("\n" + "=" * 80)
print("HYPOTHESIS 1: Overreaction Thresholds")
print("=" * 80)

for threshold in [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]:
    results = overreaction_detection(kalshi, threshold=threshold)
    reversal_rate = results['reversal_rate_3min']
    n_moves = results['total_large_moves']
    
    print(f"\nThreshold {threshold}%: {n_moves:,} moves, {reversal_rate:.1%} reversal rate", end="")
    
    if reversal_rate > 0.55 and n_moves > 100:
        print(" <- EDGE!")
        edges_found.append({
            'strategy': f'Contrarian {threshold}%',
            'reversal_rate': reversal_rate,
            'opportunities': n_moves,
            'edge_type': 'Mean Reversion'
        })
    elif reversal_rate < 0.45 and n_moves > 100:
        print(" <- MOMENTUM EDGE!")
        edges_found.append({
            'strategy': f'Momentum {threshold}%',
            'reversal_rate': reversal_rate,
            'opportunities': n_moves,
            'edge_type': 'Momentum'
        })

# ============================================================================
# HYPOTHESIS 2: Autocorrelation (Price Momentum/Mean Reversion)
# ============================================================================
print("\n" + "=" * 80)
print("HYPOTHESIS 2: Price Autocorrelation")
print("=" * 80)

ac_results = autocorrelation_analysis(kalshi, lags=5)
print("\nPrice change correlations:")
for lag, data in ac_results['lags'].items():
    corr = data['correlation']
    sig = data['significant']
    interp = data['interpretation']
    
    print(f"  Lag {lag}: {corr:+.4f} ({interp})", end="")
    if sig:
        print(" <- SIGNIFICANT!", end="")
        if abs(corr) > 0.05:
            print(" STRONG!", end="")
            edges_found.append({
                'strategy': f'{interp.title()} Lag-{lag}',
                'correlation': corr,
                'opportunities': 'Continuous',
                'edge_type': interp.title()
            })
    print()

# ============================================================================
# HYPOTHESIS 3: Time-Delayed Price Reactions
# ============================================================================
print("\n" + "=" * 80)
print("HYPOTHESIS 3: Delayed Price Discovery")
print("=" * 80)

# Calculate price changes at different lags
kalshi['price_change'] = kalshi.groupby('game_id')['close'].diff()
kalshi['price_change_lag1'] = kalshi.groupby('game_id')['price_change'].shift(-1)
kalshi['price_change_lag2'] = kalshi.groupby('game_id')['price_change'].shift(-2)
kalshi['price_change_lag3'] = kalshi.groupby('game_id')['price_change'].shift(-3)

# Test if large moves predict future moves in same direction
large_up_moves = kalshi[kalshi['price_change'] > 3].copy()
large_down_moves = kalshi[kalshi['price_change'] < -3].copy()

print("\nAfter large UP moves:")
for lag in [1, 2, 3]:
    continuation = (large_up_moves[f'price_change_lag{lag}'] > 0).mean()
    print(f"  Lag {lag}: {continuation:.1%} continue up", end="")
    if continuation > 0.55:
        print(" <- MOMENTUM EDGE!")
        edges_found.append({
            'strategy': f'Follow Momentum Up Lag-{lag}',
            'win_rate': continuation,
            'opportunities': len(large_up_moves),
            'edge_type': 'Momentum Continuation'
        })
    elif continuation < 0.45:
        print(" <- REVERSAL EDGE!")
        edges_found.append({
            'strategy': f'Fade Up Move Lag-{lag}',
            'win_rate': 1 - continuation,
            'opportunities': len(large_up_moves),
            'edge_type': 'Mean Reversion'
        })
    else:
        print()

print("\nAfter large DOWN moves:")
for lag in [1, 2, 3]:
    continuation = (large_down_moves[f'price_change_lag{lag}'] < 0).mean()
    print(f"  Lag {lag}: {continuation:.1%} continue down", end="")
    if continuation > 0.55:
        print(" <- MOMENTUM EDGE!")
    elif continuation < 0.45:
        print(" <- REVERSAL EDGE!")
    else:
        print()

# ============================================================================
# HYPOTHESIS 4: Segmentation - Different Game Types
# ============================================================================
print("\n" + "=" * 80)
print("HYPOTHESIS 4: Game Type Segmentation")
print("=" * 80)

# By pre-game odds
segments = segment_by_pregame_odds(kalshi)
print("\nBy pre-game odds:")
for seg_name, seg_df in segments.items():
    if len(seg_df) > 1000:
        results = overreaction_detection(seg_df, threshold=5.0)
        print(f"  {seg_name}: {results['reversal_rate_3min']:.1%} reversal ({results['total_large_moves']} moves)", end="")
        if results['reversal_rate_3min'] > 0.55:
            print(" <- EDGE!")
            edges_found.append({
                'strategy': f'Contrarian in {seg_name}',
                'reversal_rate': results['reversal_rate_3min'],
                'opportunities': results['total_large_moves'],
                'edge_type': 'Segment-Specific'
            })
        else:
            print()

# By final margin
segments = segment_by_final_margin(kalshi)
print("\nBy final margin:")
for seg_name, seg_df in segments.items():
    if len(seg_df) > 1000:
        results = overreaction_detection(seg_df, threshold=5.0)
        print(f"  {seg_name}: {results['reversal_rate_3min']:.1%} reversal ({results['total_large_moves']} moves)", end="")
        if results['reversal_rate_3min'] > 0.55:
            print(" <- EDGE!")
            edges_found.append({
                'strategy': f'Contrarian in {seg_name}',
                'reversal_rate': results['reversal_rate_3min'],
                'opportunities': results['total_large_moves'],
                'edge_type': 'Segment-Specific'
            })
        else:
            print()

# ============================================================================
# HYPOTHESIS 5: Volume-Based Patterns
# ============================================================================
print("\n" + "=" * 80)
print("HYPOTHESIS 5: Volume Patterns")
print("=" * 80)

# Low volume vs high volume
kalshi['volume_percentile'] = kalshi.groupby('game_id')['volume'].rank(pct=True)

low_vol = kalshi[kalshi['volume_percentile'] < 0.25]
high_vol = kalshi[kalshi['volume_percentile'] > 0.75]

print("\nLow volume periods:")
low_vol_results = overreaction_detection(low_vol, threshold=5.0)
print(f"  Reversal rate: {low_vol_results['reversal_rate_3min']:.1%} ({low_vol_results['total_large_moves']} moves)", end="")
if low_vol_results['reversal_rate_3min'] > 0.55:
    print(" <- EDGE IN LOW LIQUIDITY!")
    edges_found.append({
        'strategy': 'Contrarian Low Volume',
        'reversal_rate': low_vol_results['reversal_rate_3min'],
        'opportunities': low_vol_results['total_large_moves'],
        'edge_type': 'Liquidity-Based'
    })
else:
    print()

print("High volume periods:")
high_vol_results = overreaction_detection(high_vol, threshold=5.0)
print(f"  Reversal rate: {high_vol_results['reversal_rate_3min']:.1%} ({high_vol_results['total_large_moves']} moves)", end="")
if high_vol_results['reversal_rate_3min'] > 0.55:
    print(" <- EDGE IN HIGH LIQUIDITY!")
else:
    print()

# ============================================================================
# HYPOTHESIS 6: Time of Game Effects
# ============================================================================
print("\n" + "=" * 80)
print("HYPOTHESIS 6: Game Time Effects")
print("=" * 80)

# Early game vs late game
early_game = kalshi[kalshi['game_minute'] < 12]  # Q1
late_game = kalshi[kalshi['game_minute'] > 36]   # Q4

print("\nEarly game (Q1):")
early_results = overreaction_detection(early_game, threshold=5.0)
print(f"  Reversal rate: {early_results['reversal_rate_3min']:.1%} ({early_results['total_large_moves']} moves)", end="")
if early_results['reversal_rate_3min'] > 0.55:
    print(" <- Q1 EDGE!")
    edges_found.append({
        'strategy': 'Contrarian Q1',
        'reversal_rate': early_results['reversal_rate_3min'],
        'opportunities': early_results['total_large_moves'],
        'edge_type': 'Time-Based'
    })
else:
    print()

print("Late game (Q4):")
late_results = overreaction_detection(late_game, threshold=5.0)
print(f"  Reversal rate: {late_results['reversal_rate_3min']:.1%} ({late_results['total_large_moves']} moves)", end="")
if late_results['reversal_rate_3min'] > 0.55:
    print(" <- Q4 EDGE!")
    edges_found.append({
        'strategy': 'Contrarian Q4',
        'reversal_rate': late_results['reversal_rate_3min'],
        'opportunities': late_results['total_large_moves'],
        'edge_type': 'Time-Based'
    })
else:
    print()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("EDGE DETECTION SUMMARY")
print("=" * 80)

if len(edges_found) > 0:
    print(f"\n[OK] FOUND {len(edges_found)} POTENTIAL EDGES!\n")
    
    for i, edge in enumerate(edges_found, 1):
        print(f"{i}. {edge['strategy']}")
        print(f"   Type: {edge['edge_type']}")
        if 'reversal_rate' in edge:
            print(f"   Win Rate: {edge['reversal_rate']:.1%}")
        elif 'win_rate' in edge:
            print(f"   Win Rate: {edge['win_rate']:.1%}")
        elif 'correlation' in edge:
            print(f"   Correlation: {edge['correlation']:+.4f}")
        print(f"   Opportunities: {edge['opportunities']}")
        
        # Calculate expected profit
        if 'reversal_rate' in edge and edge['reversal_rate'] > 0.55:
            expected_edge = (edge['reversal_rate'] - 0.5) * 2  # Rough estimate
            fees = 0.035  # ~3.5% round-trip
            net_edge = expected_edge - fees
            print(f"   Expected Edge: {expected_edge:.1%} (after fees: {net_edge:.1%})")
        print()
    
    # Recommend best strategy
    print("RECOMMENDED STRATEGY:")
    best = max(edges_found, key=lambda x: x.get('reversal_rate', x.get('win_rate', 0.5)))
    print(f"  {best['strategy']}")
    print(f"  This shows the strongest statistical edge in the data.")
    
else:
    print("\n[X] NO STATISTICALLY SIGNIFICANT EDGES FOUND")
    print("\nMarket appears efficient across all tested dimensions:")
    print("  - No overreaction at any threshold")
    print("  - No autocorrelation in price changes")
    print("  - No delayed price discovery")
    print("  - No segment-specific inefficiencies")
    print("  - No volume or time-based patterns")
    print("\nConclusion: Kalshi NBA markets efficiently incorporate information.")

print("\n" + "=" * 80)

