"""Advanced Strategy Search: Find even MORE profitable edges"""
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("ADVANCED STRATEGY SEARCH")
print("Testing complex combinations and new patterns")
print("=" * 80)

kalshi = load_kalshi_games()
kalshi = fill_prices(kalshi)

# Calculate all price changes
kalshi['pc'] = kalshi.groupby('game_id')['close'].diff()
for lag in range(1, 21):
    kalshi[f'pc_next{lag}'] = kalshi.groupby('game_id')['pc'].shift(-lag)

# Additional features
kalshi['spread'] = kalshi['high'] - kalshi['low']
kalshi['vol_pct'] = kalshi.groupby('game_id')['volume'].rank(pct=True)
kalshi['price_from_50'] = abs(kalshi['close'] - 50)

new_edges = []

print("\nSearching for advanced patterns...\n")

# ============================================================================
# STRATEGY TYPE 1: Ultra-Extreme Prices (even lower fees!)
# ============================================================================
print("=" * 80)
print("TEST 1: Ultra-Extreme Prices (1-3¢ and 97-99¢)")
print("=" * 80)

for pr in [(1, 3), (97, 99)]:
    for thresh in [10, 15, 20, 25]:
        for hold in [3, 5, 7, 12, 15]:
            subset = kalshi[(kalshi['close'] >= pr[0]) & 
                           (kalshi['close'] <= pr[1]) &
                           (kalshi['pc'].abs() > thresh)].copy()
            
            if len(subset) < 5:
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
            
            # Ultra-low fees
            mid_price = (pr[0] + pr[1]) / 2 / 100
            fee = 0.07 * mid_price * (1 - mid_price) * 100 * 2
            net_pl = gross_pl - fee
            
            if net_pl > 5.0:  # Looking for VERY profitable (>5%)
                print(f"  Price {pr[0]}-{pr[1]}¢, >{thresh}%, {hold}min: "
                      f"WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
                new_edges.append({
                    'type': 'Ultra-Extreme',
                    'price_range': f"{pr[0]}-{pr[1]}",
                    'threshold': thresh,
                    'hold': hold,
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                })

# ============================================================================
# STRATEGY TYPE 2: Asymmetric (Different rules for up vs down)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: Asymmetric Strategies (Up vs Down moves)")
print("=" * 80)

# Test if UP moves reverse better than DOWN moves
up_moves = kalshi[(kalshi['close'] <= 20) & (kalshi['pc'] > 12)].copy()
down_moves = kalshi[(kalshi['close'] <= 20) & (kalshi['pc'] < -12)].copy()

for moves, label in [(up_moves, "Up"), (down_moves, "Down")]:
    if len(moves) > 20:
        moves['reverses'] = np.sign(moves['pc']) != np.sign(moves['pc_next3'])
        valid = moves[moves['pc_next3'].notna()]
        
        if len(valid) > 0:
            wr = valid['reverses'].mean()
            wins = valid[valid['reverses']]
            losses = valid[~valid['reverses']]
            avg_win = wins['pc_next3'].abs().mean() if len(wins) > 0 else 0
            avg_loss = losses['pc_next3'].abs().mean() if len(losses) > 0 else 0
            gross_pl = wr * avg_win - (1 - wr) * avg_loss
            net_pl = gross_pl - 1.5
            
            if net_pl > 1.0:
                print(f"  {label} moves at low prices: WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
                new_edges.append({
                    'type': f'Asymmetric-{label}',
                    'price_range': '1-20',
                    'threshold': 12,
                    'hold': 3,
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                })

# ============================================================================
# STRATEGY TYPE 3: Sequential Moves (2-3 in same direction)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: Sequential Move Exhaustion")
print("=" * 80)

kalshi['pc_prev'] = kalshi.groupby('game_id')['pc'].shift(1)
kalshi['pc_prev2'] = kalshi.groupby('game_id')['pc'].shift(2)

# 2 consecutive moves in same direction
kalshi['consec_2'] = (np.sign(kalshi['pc']) == np.sign(kalshi['pc_prev'])) & \
                      (kalshi['pc'].abs() > 10) & (kalshi['pc_prev'].abs() > 10)

# 3 consecutive moves
kalshi['consec_3'] = (np.sign(kalshi['pc']) == np.sign(kalshi['pc_prev'])) & \
                      (np.sign(kalshi['pc']) == np.sign(kalshi['pc_prev2'])) & \
                      (kalshi['pc'].abs() > 8) & (kalshi['pc_prev'].abs() > 8) & \
                      (kalshi['pc_prev2'].abs() > 8)

for pattern, label in [('consec_2', '2-Move'), ('consec_3', '3-Move')]:
    subset = kalshi[(kalshi['close'] <= 20) & (kalshi[pattern] == True)].copy()
    
    if len(subset) > 10:
        for hold in [3, 5, 7]:
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
                net_pl = gross_pl - 1.5
                
                if net_pl > 1.0:
                    print(f"  {label} exhaustion, {hold}min: WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
                    new_edges.append({
                        'type': f'Sequential-{label}',
                        'price_range': '1-20',
                        'pattern': pattern,
                        'hold': hold,
                        'win_rate': wr,
                        'net_pl': net_pl,
                        'trades': len(valid)
                    })

# ============================================================================
# STRATEGY TYPE 4: High Volume Spikes
# ============================================================================
print("\n" + "=" * 80)
print("TEST 4: High Volume Spike Reversals")
print("=" * 80)

# Volume spike = top 10% volume
high_vol = kalshi[(kalshi['vol_pct'] > 0.9) & 
                  (kalshi['close'] <= 20) & 
                  (kalshi['pc'].abs() > 12)].copy()

if len(high_vol) > 10:
    for hold in [3, 5, 7, 10]:
        col = f'pc_next{hold}'
        high_vol['reverses'] = np.sign(high_vol['pc']) != np.sign(high_vol[col])
        valid = high_vol[high_vol[col].notna()]
        
        if len(valid) > 0:
            wr = valid['reverses'].mean()
            wins = valid[valid['reverses']]
            losses = valid[~valid['reverses']]
            avg_win = wins[col].abs().mean() if len(wins) > 0 else 0
            avg_loss = losses[col].abs().mean() if len(losses) > 0 else 0
            gross_pl = wr * avg_win - (1 - wr) * avg_loss
            net_pl = gross_pl - 1.5
            
            if net_pl > 1.0:
                print(f"  High vol spike, {hold}min: WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
                new_edges.append({
                    'type': 'High-Volume-Spike',
                    'price_range': '1-20',
                    'threshold': 12,
                    'hold': hold,
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                })

# ============================================================================
# STRATEGY TYPE 5: Wide Spread Opportunities
# ============================================================================
print("\n" + "=" * 80)
print("TEST 5: Wide Spread (High-Low) Patterns")
print("=" * 80)

wide_spread = kalshi[(kalshi['spread'] > 5) & 
                     (kalshi['close'] <= 20) & 
                     (kalshi['pc'].abs() > 12)].copy()

if len(wide_spread) > 10:
    for hold in [3, 5, 7]:
        col = f'pc_next{hold}'
        wide_spread['reverses'] = np.sign(wide_spread['pc']) != np.sign(wide_spread[col])
        valid = wide_spread[wide_spread[col].notna()]
        
        if len(valid) > 0:
            wr = valid['reverses'].mean()
            wins = valid[valid['reverses']]
            losses = valid[~valid['reverses']]
            avg_win = wins[col].abs().mean() if len(wins) > 0 else 0
            avg_loss = losses[col].abs().mean() if len(losses) > 0 else 0
            gross_pl = wr * avg_win - (1 - wr) * avg_loss
            net_pl = gross_pl - 1.5
            
            if net_pl > 1.0:
                print(f"  Wide spread (>5%), {hold}min: WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
                new_edges.append({
                    'type': 'Wide-Spread',
                    'price_range': '1-20',
                    'threshold': 12,
                    'hold': hold,
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                })

# ============================================================================
# STRATEGY TYPE 6: Larger Moves at Mid-Range Prices
# ============================================================================
print("\n" + "=" * 80)
print("TEST 6: Very Large Moves (>30%) at Any Price")
print("=" * 80)

for pr in [(1, 30), (70, 99)]:
    for thresh in [30, 35, 40, 50]:
        for hold in [5, 10, 15, 20]:
            subset = kalshi[(kalshi['close'] >= pr[0]) & 
                           (kalshi['close'] <= pr[1]) &
                           (kalshi['pc'].abs() > thresh)].copy()
            
            if len(subset) < 5:
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
            
            mid_price = (pr[0] + pr[1]) / 2 / 100
            fee = 0.07 * mid_price * (1 - mid_price) * 100 * 2
            net_pl = gross_pl - fee
            
            if net_pl > 3.0:
                print(f"  Price {pr[0]}-{pr[1]}¢, >{thresh}%, {hold}min: "
                      f"WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
                new_edges.append({
                    'type': 'Extreme-Move',
                    'price_range': f"{pr[0]}-{pr[1]}",
                    'threshold': thresh,
                    'hold': hold,
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                })

# ============================================================================
# STRATEGY TYPE 7: Longer Holds (15-20 minutes)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 7: Extended Hold Periods (15-20 minutes)")
print("=" * 80)

for pr in [(1, 10), (90, 99)]:
    for thresh in [12, 15, 20]:
        for hold in [15, 18, 20]:
            subset = kalshi[(kalshi['close'] >= pr[0]) & 
                           (kalshi['close'] <= pr[1]) &
                           (kalshi['pc'].abs() > thresh)].copy()
            
            if len(subset) < 5:
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
            
            mid_price = (pr[0] + pr[1]) / 2 / 100
            fee = 0.07 * mid_price * (1 - mid_price) * 100 * 2
            net_pl = gross_pl - fee
            
            if net_pl > 3.0:
                print(f"  Price {pr[0]}-{pr[1]}¢, >{thresh}%, {hold}min: "
                      f"WR={wr:.1%} Net={net_pl:+.2f}% ({len(valid)} trades)")
                new_edges.append({
                    'type': 'Extended-Hold',
                    'price_range': f"{pr[0]}-{pr[1]}",
                    'threshold': thresh,
                    'hold': hold,
                    'win_rate': wr,
                    'net_pl': net_pl,
                    'trades': len(valid)
                })

# ============================================================================
# RESULTS
# ============================================================================
print("\n" + "=" * 80)
print("ADVANCED STRATEGY RESULTS")
print("=" * 80)

if len(new_edges) > 0:
    df_new = pd.DataFrame(new_edges)
    df_new = df_new.sort_values('net_pl', ascending=False)
    
    print(f"\nFound {len(df_new)} additional high-profit strategies!\n")
    
    print("TOP 20 MOST PROFITABLE:\n")
    for i, row in df_new.head(20).iterrows():
        print(f"{i+1}. {row['type']}: {row.get('price_range', 'N/A')}, "
              f"WR={row['win_rate']:.1%}, Net={row['net_pl']:+.2f}%, "
              f"{row['trades']} trades")
    
    # Compare to original findings
    print(f"\nComparison to original 195 strategies:")
    print(f"  Original best: +12.93%")
    print(f"  New best: +{df_new['net_pl'].max():.2f}%")
    
    if df_new['net_pl'].max() > 12.93:
        print(f"  *** FOUND BETTER STRATEGY! ***")
    
    # Save
    df_new.to_csv('outputs/metrics/advanced_profitable_edges.csv', index=False)
    print(f"\n✓ Saved to outputs/metrics/advanced_profitable_edges.csv")
    
else:
    print("\nNo new high-profit strategies found beyond the original 195")
    print("Original strategies remain the best!")

print("\n" + "=" * 80)

