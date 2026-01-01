"""CONTINUED SEARCH: Find additional edges with context"""
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("EXTENDED EDGE SEARCH")
print("Testing extreme prices + game context combinations")
print("=" * 80)

kalshi = load_kalshi_games()
kalshi = fill_prices(kalshi)

# Price changes
kalshi['pc'] = kalshi.groupby('game_id')['close'].diff()
for lag in range(1, 16):
    kalshi[f'pc_next{lag}'] = kalshi.groupby('game_id')['pc'].shift(-lag)

edges_found = []

# ============================================================================
# NEW TEST 1: Game Time + Extreme Prices
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: Extreme Prices by Quarter")
print("=" * 80)

for quarter in [1, 2, 3, 4]:
    q_data = kalshi[kalshi['game_minute'].between((quarter-1)*12, quarter*12)]
    
    # Low prices
    subset = q_data[(q_data['close'] <= 20) & (q_data['pc'].abs() > 12)].copy()
    if len(subset) > 20:
        subset['reverses'] = np.sign(subset['pc']) != np.sign(subset['pc_next3'])
        valid = subset[subset['pc_next3'].notna()]
        if len(valid) > 0:
            wr = valid['reverses'].mean()
            wins = valid[valid['reverses']]
            losses = valid[~valid['reverses']]
            avg_win = wins['pc_next3'].abs().mean() if len(wins) > 0 else 0
            avg_loss = losses['pc_next3'].abs().mean() if len(losses) > 0 else 0
            gross_pl = wr * avg_win - (1 - wr) * avg_loss
            net_pl = gross_pl - 1.5  # Lower fees at extreme prices
            
            if net_pl > 0:
                print(f"  Q{quarter} Low Prices: WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades) [PROFIT!]")
                edges_found.append({
                    'strategy': f'Q{quarter} Low Prices',
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                })
    
    # High prices
    subset = q_data[(q_data['close'] >= 80) & (q_data['pc'].abs() > 12)].copy()
    if len(subset) > 20:
        subset['reverses'] = np.sign(subset['pc']) != np.sign(subset['pc_next3'])
        valid = subset[subset['pc_next3'].notna()]
        if len(valid) > 0:
            wr = valid['reverses'].mean()
            wins = valid[valid['reverses']]
            losses = valid[~valid['reverses']]
            avg_win = wins['pc_next3'].abs().mean() if len(wins) > 0 else 0
            avg_loss = losses['pc_next3'].abs().mean() if len(losses) > 0 else 0
            gross_pl = wr * avg_win - (1 - wr) * avg_loss
            net_pl = gross_pl - 1.5
            
            if net_pl > 0:
                print(f"  Q{quarter} High Prices: WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades) [PROFIT!]")
                edges_found.append({
                    'strategy': f'Q{quarter} High Prices',
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                })

# ============================================================================
# NEW TEST 2: Consecutive Large Moves (Momentum Exhaustion)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: Multiple Consecutive Moves (Exhaustion Pattern)")
print("=" * 80)

kalshi['pc_prev'] = kalshi.groupby('game_id')['pc'].shift(1)
kalshi['same_direction'] = np.sign(kalshi['pc']) == np.sign(kalshi['pc_prev'])

# After 2 consecutive large moves in same direction at extreme prices
subset = kalshi[(kalshi['close'] <= 20) & 
                (kalshi['pc'].abs() > 10) & 
                (kalshi['same_direction'] == True)].copy()

if len(subset) > 20:
    subset['reverses'] = np.sign(subset['pc']) != np.sign(subset['pc_next3'])
    valid = subset[subset['pc_next3'].notna()]
    if len(valid) > 0:
        wr = valid['reverses'].mean()
        wins = valid[valid['reverses']]
        losses = valid[~valid['reverses']]
        avg_win = wins['pc_next3'].abs().mean() if len(wins) > 0 else 0
        avg_loss = losses['pc_next3'].abs().mean() if len(losses) > 0 else 0
        gross_pl = wr * avg_win - (1 - wr) * avg_loss
        net_pl = gross_pl - 1.5
        
        print(f"Low Price Exhaustion: WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
        if net_pl > 0:
            print("  [PROFIT!]")
            edges_found.append({
                'strategy': 'Low Price Exhaustion',
                'win_rate': wr,
                'net_pl': net_pl,
                'trades': len(valid)
            })

# ============================================================================
# NEW TEST 3: Volume Spikes at Extreme Prices
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: High Volume + Extreme Prices")
print("=" * 80)

kalshi['vol_pct'] = kalshi.groupby('game_id')['volume'].rank(pct=True)

subset = kalshi[(kalshi['close'] <= 20) & 
                (kalshi['pc'].abs() > 10) & 
                (kalshi['vol_pct'] > 0.8)].copy()

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
        net_pl = gross_pl - 1.5
        
        print(f"High Vol + Low Price: WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
        if net_pl > 0:
            print("  [PROFIT!]")
            edges_found.append({
                'strategy': 'High Vol + Low Price',
                'win_rate': wr,
                'net_pl': net_pl,
                'trades': len(valid)
            })

# ============================================================================
# NEW TEST 4: Spread Analysis at Extreme Prices
# ============================================================================
print("\n" + "=" * 80)
print("TEST 4: Wide Spreads (High-Low) at Extreme Prices")
print("=" * 80)

kalshi['spread'] = kalshi['high'] - kalshi['low']

subset = kalshi[(kalshi['close'] <= 20) & 
                (kalshi['spread'] > 3) &
                (kalshi['pc'].abs() > 10)].copy()

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
        net_pl = gross_pl - 1.5
        
        print(f"Wide Spread + Low Price: WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
        if net_pl > 0:
            print("  [PROFIT!]")
            edges_found.append({
                'strategy': 'Wide Spread + Low Price',
                'win_rate': wr,
                'net_pl': net_pl,
                'trades': len(valid)
            })

# ============================================================================
# NEW TEST 5: Different Hold Periods for Different Price Ranges
# ============================================================================
print("\n" + "=" * 80)
print("TEST 5: Optimized Holds by Price Range")
print("=" * 80)

price_ranges = [(1, 10), (10, 20), (20, 30), (70, 80), (80, 90), (90, 99)]
thresholds = [10, 15, 20]
holds = [3, 5, 7, 10, 12, 15]

best_per_range = {}

for pr in price_ranges:
    best_net = -999
    best_config = None
    
    for thresh in thresholds:
        for hold in holds:
            subset = kalshi[(kalshi['close'] >= pr[0]) & 
                           (kalshi['close'] <= pr[1]) &
                           (kalshi['pc'].abs() > thresh)].copy()
            
            if len(subset) < 15:
                continue
            
            col = f'pc_next{hold}'
            subset['reverses'] = np.sign(subset['pc']) != np.sign(subset[col])
            valid = subset[subset[col].notna()]
            
            if len(valid) == 0:
                continue
            
            wr = valid['reverses'].mean()
            wins = valid[valid['reverses']]
            losses = valid[~valid['reverses']]
            avg_win = wins[col].abs().mean() if len(wins) > 0 else 0
            avg_loss = losses[col].abs().mean() if len(losses) > 0 else 0
            gross_pl = wr * avg_win - (1 - wr) * avg_loss
            
            # Dynamic fee based on price
            mid_price = (pr[0] + pr[1]) / 2 / 100
            fee = 0.07 * mid_price * (1 - mid_price) * 100 * 2
            
            net_pl = gross_pl - fee
            
            if net_pl > best_net:
                best_net = net_pl
                best_config = {
                    'price_range': pr,
                    'threshold': thresh,
                    'hold': hold,
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                }
    
    if best_config and best_config['net_pl'] > 0:
        print(f"Price {pr[0]}-{pr[1]}: >{best_config['threshold']}% hold {best_config['hold']}min")
        print(f"  WR={best_config['win_rate']:.1%} Net={best_config['net_pl']:+.2f}% ({best_config['trades']} trades) [PROFIT!]")
        edges_found.append(best_config)
        best_per_range[f"{pr[0]}-{pr[1]}"] = best_config

# ============================================================================
# NEW TEST 6: Momentum vs Mean Reversion by Price Level
# ============================================================================
print("\n" + "=" * 80)
print("TEST 6: Test Momentum (instead of reversion) at Extremes")
print("=" * 80)

# Maybe at extreme prices, momentum works?
subset = kalshi[(kalshi['close'] <= 15) & (kalshi['pc'].abs() > 15)].copy()
if len(subset) > 20:
    # Test momentum (follow the move)
    subset['continues'] = np.sign(subset['pc']) == np.sign(subset['pc_next3'])
    valid = subset[subset['pc_next3'].notna()]
    if len(valid) > 0:
        wr = valid['continues'].mean()
        wins = valid[valid['continues']]
        losses = valid[~valid['continues']]
        avg_win = wins['pc_next3'].abs().mean() if len(wins) > 0 else 0
        avg_loss = losses['pc_next3'].abs().mean() if len(losses) > 0 else 0
        gross_pl = wr * avg_win - (1 - wr) * avg_loss
        net_pl = gross_pl - 1.0
        
        print(f"Momentum (follow) at low prices: WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
        if net_pl > 0:
            print("  [PROFIT!]")
            edges_found.append({
                'strategy': 'Momentum Low Price',
                'win_rate': wr,
                'net_pl': net_pl,
                'trades': len(valid)
            })

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("EXTENDED SEARCH RESULTS")
print("=" * 80)

print(f"\nFound {len(edges_found)} additional profitable strategies!")

if len(edges_found) > 0:
    print("\nTop 10 by Net P/L:")
    sorted_edges = sorted(edges_found, key=lambda x: x['net_pl'], reverse=True)[:10]
    for i, edge in enumerate(sorted_edges, 1):
        print(f"{i}. {edge['strategy']}")
        print(f"   WR={edge['win_rate']:.1%} Net={edge['net_pl']:+.2f}% ({edge['trades']} trades)")
    
    # Total expected profit
    total_trades = sum(e['trades'] for e in edges_found)
    weighted_pl = sum(e['net_pl'] * e['trades'] for e in edges_found) / total_trades if total_trades > 0 else 0
    
    print(f"\nCombined Statistics:")
    print(f"  Total opportunities: {total_trades} trades")
    print(f"  Weighted avg P/L: {weighted_pl:+.2f}%")
    print(f"  Per game: {total_trades / 502:.2f} trades")
    print(f"  Expected profit ($100/trade): ${weighted_pl * total_trades / 502:.2f} per game")

print("\n" + "=" * 80)

