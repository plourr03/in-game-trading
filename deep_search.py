"""Deep dive: Test MORE hypotheses for profitable edge"""
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("COMPREHENSIVE EDGE SEARCH - Testing All Angles")
print("=" * 80)

# Load
kalshi = load_kalshi_games()
kalshi = fill_prices(kalshi)

# Price changes
kalshi['pc'] = kalshi.groupby('game_id')['close'].diff()
for lag in range(1, 11):
    kalshi[f'pc_next{lag}'] = kalshi.groupby('game_id')['pc'].shift(-lag)

edges_found = []

# ============================================================================
# TEST 1: Extreme Price Levels (Low fees!)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: Extreme Price Levels (where fees are lower)")
print("=" * 80)

for price_range in [(1, 15), (15, 25), (25, 40), (40, 60), (60, 75), (75, 85), (85, 99)]:
    subset = kalshi[(kalshi['close'] >= price_range[0]) & 
                    (kalshi['close'] <= price_range[1]) &
                    (kalshi['pc'].abs() > 7)].copy()
    
    if len(subset) > 50:
        subset['reverses'] = np.sign(subset['pc']) != np.sign(subset['pc_next3'])
        valid = subset[subset['pc_next3'].notna()]
        
        if len(valid) > 0:
            wr = valid['reverses'].mean()
            wins = valid[valid['reverses']]
            losses = valid[~valid['reverses']]
            avg_win = wins['pc_next3'].abs().mean() if len(wins) > 0 else 0
            avg_loss = losses['pc_next3'].abs().mean() if len(losses) > 0 else 0
            gross_pl = wr * avg_win - (1 - wr) * avg_loss
            
            # Calculate actual fees at this price level
            mid_price = (price_range[0] + price_range[1]) / 2 / 100
            fee_rate = 0.07 * mid_price * (1 - mid_price) * 100 * 2  # Round trip
            
            net_pl = gross_pl - fee_rate
            
            status = "[PROFIT]" if net_pl > 0 else "[LOSS]"
            
            print(f"Price {price_range[0]:2d}-{price_range[1]:2d}: "
                  f"WR={wr:.1%} Fee={fee_rate:.2f}% Net={net_pl:+.2f}% "
                  f"{status} ({len(valid)} trades)")
            
            if net_pl > 0:
                edges_found.append({
                    'strategy': f'Price {price_range[0]}-{price_range[1]}',
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                })

# ============================================================================
# TEST 2: Extreme Moves (bigger reversals?)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: Extreme Moves (>10%, >15%, >20%)")
print("=" * 80)

for threshold in [10, 12, 15, 20, 25]:
    subset = kalshi[kalshi['pc'].abs() > threshold].copy()
    
    if len(subset) > 20:
        for hold in [3, 5, 10]:
            col = f'pc_next{hold}'
            subset['reverses'] = np.sign(subset['pc']) != np.sign(subset[col])
            valid = subset[subset[col].notna()]
            
            if len(valid) > 0:
                wr = valid['reverses'].mean()
                wins = valid[valid['reverses']]
                losses = valid[~valid['reverses']]
                avg_win = wins[col].abs().mean() if len(wins) > 0 else 0
                avg_loss = losses[col].abs().mean() if len(losses) > 0 else 0
                gross_pl = wr * avg_win - (1 - wr) * avg_loss
                net_pl = gross_pl - 2.75
                
                status = "[PROFIT]" if net_pl > 0 else "[LOSS]"
                
                print(f">{threshold:2d}% hold {hold:2d}min: "
                      f"WR={wr:.1%} Gross={gross_pl:+.2f}% Net={net_pl:+.2f}% "
                      f"{status} ({len(valid)} trades)")
                
                if net_pl > 0:
                    edges_found.append({
                        'strategy': f'>{threshold}% hold {hold}min',
                        'win_rate': wr,
                        'net_pl': net_pl,
                        'trades': len(valid)
                    })

# ============================================================================
# TEST 3: Volume Patterns
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: Volume-Based Edges")
print("=" * 80)

kalshi['vol_pct'] = kalshi.groupby('game_id')['volume'].rank(pct=True)

for vol_range in [(0, 0.25), (0.75, 1.0)]:
    label = "Low Volume" if vol_range[0] == 0 else "High Volume"
    subset = kalshi[(kalshi['vol_pct'] >= vol_range[0]) & 
                    (kalshi['vol_pct'] <= vol_range[1]) &
                    (kalshi['pc'].abs() > 7)].copy()
    
    if len(subset) > 50:
        subset['reverses'] = np.sign(subset['pc']) != np.sign(subset['pc_next3'])
        valid = subset[subset['pc_next3'].notna()]
        
        if len(valid) > 0:
            wr = valid['reverses'].mean()
            wins = valid[valid['reverses']]
            losses = valid[~valid['reverses']]
            avg_win = wins['pc_next3'].abs().mean() if len(wins) > 0 else 0
            avg_loss = losses['pc_next3'].abs().mean() if len(losses) > 0 else 0
            gross_pl = wr * avg_win - (1 - wr) * avg_loss
            net_pl = gross_pl - 2.75
            
            status = "[PROFIT]" if net_pl > 0 else "[LOSS]"
            
            print(f"{label}: WR={wr:.1%} Net={net_pl:+.2f}% {status} ({len(valid)} trades)")
            
            if net_pl > 0:
                edges_found.append({
                    'strategy': label,
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                })

# ============================================================================
# TEST 4: Combined Signals (multiple filters)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 4: Combined Signal Strategies")
print("=" * 80)

# Extreme move + low price (lower fees)
subset = kalshi[(kalshi['pc'].abs() > 10) & (kalshi['close'] < 25)].copy()
if len(subset) > 20:
    subset['reverses'] = np.sign(subset['pc']) != np.sign(subset['pc_next5'])
    valid = subset[subset['pc_next5'].notna()]
    if len(valid) > 0:
        wr = valid['reverses'].mean()
        wins = valid[valid['reverses']]
        losses = valid[~valid['reverses']]
        avg_win = wins['pc_next5'].abs().mean() if len(wins) > 0 else 0
        avg_loss = losses['pc_next5'].abs().mean() if len(losses) > 0 else 0
        gross_pl = wr * avg_win - (1 - wr) * avg_loss
        
        # Lower fees at 20¢ average
        fee = 0.07 * 0.2 * 0.8 * 100 * 2
        net_pl = gross_pl - fee
        
        status = "[PROFIT]" if net_pl > 0 else "[LOSS]"
        print(f"Extreme move + Low price: WR={wr:.1%} Fee={fee:.2f}% Net={net_pl:+.2f}% {status} ({len(valid)} trades)")
        
        if net_pl > 0:
            edges_found.append({
                'strategy': 'Extreme + Low Price',
                'win_rate': wr,
                'net_pl': net_pl,
                'trades': len(valid)
            })

# Extreme move + high price (lower fees)
subset = kalshi[(kalshi['pc'].abs() > 10) & (kalshi['close'] > 75)].copy()
if len(subset) > 20:
    subset['reverses'] = np.sign(subset['pc']) != np.sign(subset['pc_next5'])
    valid = subset[subset['pc_next5'].notna()]
    if len(valid) > 0:
        wr = valid['reverses'].mean()
        wins = valid[valid['reverses']]
        losses = valid[~valid['reverses']]
        avg_win = wins['pc_next5'].abs().mean() if len(wins) > 0 else 0
        avg_loss = losses['pc_next5'].abs().mean() if len(losses) > 0 else 0
        gross_pl = wr * avg_win - (1 - wr) * avg_loss
        
        # Lower fees at 80¢ average
        fee = 0.07 * 0.8 * 0.2 * 100 * 2
        net_pl = gross_pl - fee
        
        status = "[PROFIT]" if net_pl > 0 else "[LOSS]"
        print(f"Extreme move + High price: WR={wr:.1%} Fee={fee:.2f}% Net={net_pl:+.2f}% {status} ({len(valid)} trades)")
        
        if net_pl > 0:
            edges_found.append({
                'strategy': 'Extreme + High Price',
                'win_rate': wr,
                'net_pl': net_pl,
                'trades': len(valid)
            })

# ============================================================================
# RESULTS
# ============================================================================
print("\n" + "=" * 80)
print("SEARCH RESULTS")
print("=" * 80)

if len(edges_found) > 0:
    print(f"\n[SUCCESS] FOUND {len(edges_found)} PROFITABLE EDGES!\n")
    for i, edge in enumerate(edges_found, 1):
        print(f"{i}. {edge['strategy']}")
        print(f"   Win Rate: {edge['win_rate']:.1%}")
        print(f"   Net P/L: {edge['net_pl']:+.2f}%")
        print(f"   Trades: {edge['trades']}")
        print()
    
    # Best edge
    best = max(edges_found, key=lambda x: x['net_pl'])
    print(f"BEST STRATEGY: {best['strategy']}")
    print(f"  Expected profit: ${best['net_pl']:.2f} per $100 position")
    print(f"  Per game: ~${best['net_pl'] * best['trades'] / 502:.2f}")
else:
    print("\n[STILL SEARCHING] No profitable edge found yet...")
    print("\nBest performing (still unprofitable):")
    # Find closest to breakeven
    kalshi['reverses'] = np.sign(kalshi['pc']) != np.sign(kalshi['pc_next3'])
    print("  Need different approach or lower fees")

print("\n" + "=" * 80)

