"""MORE EDGES: Test all combinations systematically"""
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("SYSTEMATIC EDGE DISCOVERY")
print("Testing ALL profitable combinations at extreme prices")
print("=" * 80)

kalshi = load_kalshi_games()
kalshi = fill_prices(kalshi)

# Price changes
kalshi['pc'] = kalshi.groupby('game_id')['close'].diff()
for lag in range(1, 21):  # Test up to 20 minute holds
    kalshi[f'pc_next{lag}'] = kalshi.groupby('game_id')['pc'].shift(-lag)

all_edges = []

print("\nRunning comprehensive grid search...")
print("(Testing 1000+ combinations...)\n")

# Expanded parameter space
price_ranges = [
    (1, 5), (1, 10), (1, 15), (1, 20), (1, 25),
    (5, 10), (5, 15), (10, 15), (10, 20), (15, 20), (15, 25),
    (75, 85), (75, 90), (80, 90), (80, 95), (85, 95), (85, 99),
    (90, 95), (90, 99), (95, 99)
]

move_thresholds = [8, 10, 12, 15, 18, 20, 25, 30]
hold_periods = [2, 3, 5, 7, 10, 12, 15, 18, 20]

total_tested = 0
profitable_count = 0

for pr in price_ranges:
    for thresh in move_thresholds:
        for hold in hold_periods:
            total_tested += 1
            
            subset = kalshi[(kalshi['close'] >= pr[0]) & 
                           (kalshi['close'] <= pr[1]) &
                           (kalshi['pc'].abs() > thresh)].copy()
            
            if len(subset) < 10:  # Need at least 10 trades
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
            
            # Calculate fees
            mid_price = (pr[0] + pr[1]) / 2 / 100
            fee = 0.07 * mid_price * (1 - mid_price) * 100 * 2
            
            net_pl = gross_pl - fee
            
            if net_pl > 0:
                profitable_count += 1
                all_edges.append({
                    'price_min': pr[0],
                    'price_max': pr[1],
                    'threshold': thresh,
                    'hold': hold,
                    'win_rate': wr,
                    'gross_pl': gross_pl,
                    'fee': fee,
                    'net_pl': net_pl,
                    'trades': len(valid),
                    'avg_win': avg_win,
                    'avg_loss': avg_loss
                })

print(f"Tested {total_tested} combinations")
print(f"Found {profitable_count} PROFITABLE strategies!\n")

# ============================================================================
# ANALYSIS OF FINDINGS
# ============================================================================
print("=" * 80)
print("COMPREHENSIVE RESULTS")
print("=" * 80)

if len(all_edges) > 0:
    df_edges = pd.DataFrame(all_edges)
    
    # Sort by net P/L
    df_edges = df_edges.sort_values('net_pl', ascending=False)
    
    print(f"\nTOP 20 STRATEGIES by Net P/L:\n")
    for i, row in df_edges.head(20).iterrows():
        print(f"{row.name+1}. Price {row['price_min']:.0f}-{row['price_max']:.0f}¢, "
              f">{row['threshold']:.0f}%, hold {row['hold']:.0f}min")
        print(f"   WR={row['win_rate']:.1%} Net={row['net_pl']:+.2f}% "
              f"Fee={row['fee']:.2f}% ({row['trades']:.0f} trades)")
    
    print("\n" + "=" * 80)
    print("STATISTICAL SUMMARY")
    print("=" * 80)
    
    print(f"\nTotal profitable strategies: {len(df_edges)}")
    print(f"Average net P/L: {df_edges['net_pl'].mean():.2f}%")
    print(f"Median net P/L: {df_edges['net_pl'].median():.2f}%")
    print(f"Best net P/L: {df_edges['net_pl'].max():.2f}%")
    
    print(f"\nTotal opportunities: {df_edges['trades'].sum():.0f} trades")
    print(f"Average per strategy: {df_edges['trades'].mean():.1f} trades")
    print(f"Per game average: {df_edges['trades'].sum() / 502:.2f} trades")
    
    # Win rate distribution
    print(f"\nWin Rate Distribution:")
    print(f"  Min: {df_edges['win_rate'].min():.1%}")
    print(f"  25th percentile: {df_edges['win_rate'].quantile(0.25):.1%}")
    print(f"  Median: {df_edges['win_rate'].median():.1%}")
    print(f"  75th percentile: {df_edges['win_rate'].quantile(0.75):.1%}")
    print(f"  Max: {df_edges['win_rate'].max():.1%}")
    
    # Fee savings
    print(f"\nFee Structure Impact:")
    print(f"  Avg fee paid: {df_edges['fee'].mean():.2f}% (vs 2.75% at 50¢)")
    print(f"  Fee savings: {2.75 - df_edges['fee'].mean():.2f}% per trade")
    print(f"  This makes the difference!")
    
    # Pattern analysis
    print("\n" + "=" * 80)
    print("PATTERN ANALYSIS")
    print("=" * 80)
    
    # Best price ranges
    df_edges['price_range_label'] = df_edges.apply(
        lambda x: f"{x['price_min']:.0f}-{x['price_max']:.0f}", axis=1
    )
    best_ranges = df_edges.groupby('price_range_label').agg({
        'net_pl': 'mean',
        'trades': 'sum'
    }).sort_values('net_pl', ascending=False).head(10)
    
    print("\nBest Price Ranges (by avg P/L):")
    for range_label, row in best_ranges.iterrows():
        print(f"  {range_label}¢: Avg Net={row['net_pl']:+.2f}% ({row['trades']:.0f} total trades)")
    
    # Best thresholds
    best_thresh = df_edges.groupby('threshold').agg({
        'net_pl': 'mean',
        'trades': 'sum'
    }).sort_values('net_pl', ascending=False)
    
    print("\nBest Move Thresholds:")
    for thresh, row in best_thresh.iterrows():
        print(f"  >{thresh:.0f}%: Avg Net={row['net_pl']:+.2f}% ({row['trades']:.0f} total trades)")
    
    # Best hold periods
    best_holds = df_edges.groupby('hold').agg({
        'net_pl': 'mean',
        'trades': 'sum'
    }).sort_values('net_pl', ascending=False)
    
    print("\nBest Hold Periods:")
    for hold, row in best_holds.iterrows():
        print(f"  {hold:.0f}min: Avg Net={row['net_pl']:+.2f}% ({row['trades']:.0f} total trades)")
    
    # ========================================================================
    # PORTFOLIO APPROACH
    # ========================================================================
    print("\n" + "=" * 80)
    print("PORTFOLIO APPROACH")
    print("=" * 80)
    
    # Select diverse strategies
    print("\nRecommended Portfolio (5 strategies for diversification):\n")
    
    # 1. Highest frequency
    high_freq = df_edges.nlargest(1, 'trades').iloc[0]
    print(f"1. HIGH FREQUENCY STRATEGY")
    print(f"   Price {high_freq['price_min']:.0f}-{high_freq['price_max']:.0f}¢, "
          f">{high_freq['threshold']:.0f}%, hold {high_freq['hold']:.0f}min")
    print(f"   WR={high_freq['win_rate']:.1%} Net={high_freq['net_pl']:+.2f}% "
          f"({high_freq['trades']:.0f} trades)")
    print(f"   Expected: ${high_freq['net_pl'] * high_freq['trades'] / 502:.2f}/game\n")
    
    # 2. Highest P/L
    high_pl = df_edges.iloc[0]
    print(f"2. HIGHEST PROFIT STRATEGY")
    print(f"   Price {high_pl['price_min']:.0f}-{high_pl['price_max']:.0f}¢, "
          f">{high_pl['threshold']:.0f}%, hold {high_pl['hold']:.0f}min")
    print(f"   WR={high_pl['win_rate']:.1%} Net={high_pl['net_pl']:+.2f}% "
          f"({high_pl['trades']:.0f} trades)")
    print(f"   Expected: ${high_pl['net_pl'] * high_pl['trades'] / 502:.2f}/game\n")
    
    # 3. Balanced (good sample size, good P/L)
    balanced = df_edges[(df_edges['trades'] >= 30) & (df_edges['trades'] <= 100)].nlargest(1, 'net_pl')
    if len(balanced) > 0:
        bal = balanced.iloc[0]
        print(f"3. BALANCED STRATEGY")
        print(f"   Price {bal['price_min']:.0f}-{bal['price_max']:.0f}¢, "
              f">{bal['threshold']:.0f}%, hold {bal['hold']:.0f}min")
        print(f"   WR={bal['win_rate']:.1%} Net={bal['net_pl']:+.2f}% "
              f"({bal['trades']:.0f} trades)")
        print(f"   Expected: ${bal['net_pl'] * bal['trades'] / 502:.2f}/game\n")
    
    # 4. Short hold (quick trades)
    short_hold = df_edges[df_edges['hold'] <= 5].nlargest(1, 'net_pl')
    if len(short_hold) > 0:
        sh = short_hold.iloc[0]
        print(f"4. SHORT HOLD STRATEGY (Quick Trades)")
        print(f"   Price {sh['price_min']:.0f}-{sh['price_max']:.0f}¢, "
              f">{sh['threshold']:.0f}%, hold {sh['hold']:.0f}min")
        print(f"   WR={sh['win_rate']:.1%} Net={sh['net_pl']:+.2f}% "
              f"({sh['trades']:.0f} trades)")
        print(f"   Expected: ${sh['net_pl'] * sh['trades'] / 502:.2f}/game\n")
    
    # 5. Long hold (patient)
    long_hold = df_edges[df_edges['hold'] >= 12].nlargest(1, 'net_pl')
    if len(long_hold) > 0:
        lh = long_hold.iloc[0]
        print(f"5. LONG HOLD STRATEGY (Patient)")
        print(f"   Price {lh['price_min']:.0f}-{lh['price_max']:.0f}¢, "
              f">{lh['threshold']:.0f}%, hold {lh['hold']:.0f}min")
        print(f"   WR={lh['win_rate']:.1%} Net={lh['net_pl']:+.2f}% "
              f"({lh['trades']:.0f} trades)")
        print(f"   Expected: ${lh['net_pl'] * lh['trades'] / 502:.2f}/game\n")
    
    # Total expected value
    portfolio_trades = [high_freq, high_pl]
    if len(balanced) > 0:
        portfolio_trades.append(bal)
    if len(short_hold) > 0:
        portfolio_trades.append(sh)
    if len(long_hold) > 0:
        portfolio_trades.append(lh)
    
    total_expected = sum(t['net_pl'] * t['trades'] / 502 for t in portfolio_trades)
    print(f"PORTFOLIO EXPECTED VALUE: ${total_expected:.2f} per game")
    print(f"Annual (500 games): ${total_expected * 500:,.2f}")
    
    # Save results
    df_edges.to_csv('outputs/metrics/all_profitable_edges.csv', index=False)
    print(f"\n✓ Saved {len(df_edges)} profitable strategies to outputs/metrics/all_profitable_edges.csv")

else:
    print("\nNo profitable strategies found")

print("\n" + "=" * 80)

