"""Deep dive: Find edges using play-by-play event data"""
from src.data.loader import load_kalshi_games, connect_to_pbp_db, load_pbp_data
from src.data.preprocessor import fill_prices, add_team_to_kalshi
from src.data.aligner import align_pbp_to_minutes, merge_kalshi_pbp
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("DEEP DIVE: Play-by-Play Event Analysis")
print("Testing if specific events create better edges")
print("=" * 80)

# Load Kalshi data
print("\nLoading Kalshi data...")
kalshi = load_kalshi_games()
kalshi = fill_prices(kalshi)
kalshi = add_team_to_kalshi(kalshi)

# Load PBP data
print("Connecting to play-by-play database...")
conn = connect_to_pbp_db()
game_ids = kalshi['game_id'].unique()[:50]  # Start with 50 games for speed
print(f"Loading PBP data for {len(game_ids)} games...")

pbp = load_pbp_data(game_ids, conn)
conn.close()

# Align and merge
print("Aligning play-by-play to game minutes...")
pbp = align_pbp_to_minutes(pbp)
merged = merge_kalshi_pbp(kalshi[kalshi['game_id'].isin(game_ids)], pbp)

print(f"\nMerged dataset: {len(merged):,} rows")
print(f"Columns available: {merged.columns.tolist()}")

# Calculate price changes
merged['pc'] = merged.groupby('game_id')['close'].diff()
merged['pc_next3'] = merged.groupby('game_id')['pc'].shift(-3)

print("\n" + "=" * 80)
print("HYPOTHESIS 1: Event-Specific Reversals")
print("=" * 80)

# Get scoring events
scoring_events = pbp[pbp['action_type'].str.contains('Made Shot', na=False)].copy()
print(f"\nFound {len(scoring_events):,} scoring events")

# Test: Do large moves after 3-pointers reverse more?
three_pointers = scoring_events[scoring_events['shot_value'] == 3]
print(f"Found {len(three_pointers):,} three-pointers")

# Test: Do large moves after AND-1s reverse more?
and1_events = pbp[pbp['action_type'].str.contains('Free Throw', na=False) & 
                   pbp['action_type'].str.contains('1 of 1', na=False)]
print(f"Found {len(and1_events):,} AND-1 free throws")

# Test: Do large moves after turnovers reverse more?
turnovers = pbp[pbp['action_type'].str.contains('Turnover', na=False)]
print(f"Found {len(turnovers):,} turnovers")

# Tag Kalshi data with event types
merged['has_3pt'] = merged['game_minute'].isin(
    three_pointers.groupby(['game_id', 'game_minute']).size().reset_index()
    .apply(lambda x: (x['game_id'], x['game_minute']), axis=1)
)

merged['has_turnover'] = merged['game_minute'].isin(
    turnovers.groupby(['game_id', 'game_minute']).size().reset_index()
    .apply(lambda x: (x['game_id'], x['game_minute']), axis=1)
)

# Test reversals after large moves with different event types
print("\n" + "-" * 80)
print("After large moves (>7%) with 3-pointer:")
large_w_3pt = merged[(merged['pc'].abs() > 7) & (merged['has_3pt'])]
if len(large_w_3pt) > 10:
    large_w_3pt['reverses'] = np.sign(large_w_3pt['pc']) != np.sign(large_w_3pt['pc_next3'])
    valid = large_w_3pt[large_w_3pt['pc_next3'].notna()]
    if len(valid) > 0:
        wr = valid['reverses'].mean()
        print(f"  Win rate: {wr:.1%} ({len(valid)} trades)")
        if wr > 0.60:
            print("  <- POTENTIAL EDGE!")

print("\nAfter large moves (>7%) with turnover:")
large_w_to = merged[(merged['pc'].abs() > 7) & (merged['has_turnover'])]
if len(large_w_to) > 10:
    large_w_to['reverses'] = np.sign(large_w_to['pc']) != np.sign(large_w_to['pc_next3'])
    valid = large_w_to[large_w_to['pc_next3'].notna()]
    if len(valid) > 0:
        wr = valid['reverses'].mean()
        print(f"  Win rate: {wr:.1%} ({len(valid)} trades)")
        if wr > 0.60:
            print("  <- POTENTIAL EDGE!")

print("\n" + "=" * 80)
print("HYPOTHESIS 2: Extreme Price Levels")
print("=" * 80)

# Test if edges exist at extreme prices
kalshi_full = kalshi.copy()
kalshi_full['pc'] = kalshi_full.groupby('game_id')['close'].diff()
kalshi_full['pc_next3'] = kalshi_full.groupby('game_id')['pc'].shift(-3)

for price_range in [(1, 20), (20, 40), (40, 60), (60, 80), (80, 99)]:
    subset = kalshi_full[(kalshi_full['close'] >= price_range[0]) & 
                         (kalshi_full['close'] <= price_range[1]) &
                         (kalshi_full['pc'].abs() > 7)].copy()
    
    if len(subset) > 50:
        subset['reverses'] = np.sign(subset['pc']) != np.sign(subset['pc_next3'])
        valid = subset[subset['pc_next3'].notna()]
        
        if len(valid) > 0:
            wr = valid['reverses'].mean()
            
            # Calculate P&L
            wins = valid[valid['reverses']]
            losses = valid[~valid['reverses']]
            avg_win = wins['pc_next3'].abs().mean() if len(wins) > 0 else 0
            avg_loss = losses['pc_next3'].abs().mean() if len(losses) > 0 else 0
            gross_pl = wr * avg_win - (1 - wr) * avg_loss
            
            # Fees at different prices
            mid_price = (price_range[0] + price_range[1]) / 2 / 100
            fee_pct = 0.07 * mid_price * (1 - mid_price) * 100 * 2  # Round trip
            
            net_pl = gross_pl - fee_pct
            
            status = "PROFIT" if net_pl > 0 else "LOSS"
            special = " <- EDGE FOUND!" if net_pl > 0 else ""
            
            print(f"\nPrice {price_range[0]}-{price_range[1]}¢:")
            print(f"  Win rate: {wr:.1%}, Net P/L: {net_pl:+.2f}% {status} ({len(valid)} trades){special}")

print("\n" + "=" * 80)
print("HYPOTHESIS 3: Extreme Moves (>15%)")
print("=" * 80)

for threshold in [10, 12, 15, 20]:
    subset = kalshi_full[kalshi_full['pc'].abs() > threshold].copy()
    
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
            net_pl = gross_pl - 2.75
            
            status = "PROFIT" if net_pl > 0 else "LOSS"
            special = " <- EDGE!" if net_pl > 0 else ""
            
            print(f"\n>{threshold}% moves: {wr:.1%} win, Net={net_pl:+.2f}% {status} ({len(valid)} trades){special}")

print("\n" + "=" * 80)
print("HYPOTHESIS 4: Longer Hold Periods")
print("=" * 80)

kalshi_full['pc_next5'] = kalshi_full.groupby('game_id')['pc'].shift(-5)
kalshi_full['pc_next10'] = kalshi_full.groupby('game_id')['pc'].shift(-10)

large = kalshi_full[kalshi_full['pc'].abs() > 7].copy()

for hold_period, col in [(3, 'pc_next3'), (5, 'pc_next5'), (10, 'pc_next10')]:
    large['reverses'] = np.sign(large['pc']) != np.sign(large[col])
    valid = large[large[col].notna()]
    
    if len(valid) > 0:
        wr = valid['reverses'].mean()
        wins = valid[valid['reverses']]
        losses = valid[~valid['reverses']]
        avg_win = wins[col].abs().mean() if len(wins) > 0 else 0
        avg_loss = losses[col].abs().mean() if len(losses) > 0 else 0
        gross_pl = wr * avg_win - (1 - wr) * avg_loss
        net_pl = gross_pl - 2.75
        
        status = "PROFIT" if net_pl > 0 else "LOSS"
        special = " <- EDGE!" if net_pl > 0 else ""
        
        print(f"\n{hold_period}-minute hold: {wr:.1%} win, Net={net_pl:+.2f}% {status} ({len(valid)} trades){special}")

print("\n" + "=" * 80)
print("Searching for profitable combinations...")
print("=" * 80)

