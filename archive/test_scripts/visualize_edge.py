"""Create visual proof of the edge"""
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style('darkgrid')
plt.rcParams['figure.figsize'] = (14, 10)

# Load data
print("Loading data for visualization...")
kalshi = load_kalshi_games()
kalshi = fill_prices(kalshi)

# Calculate price changes
kalshi['price_change'] = kalshi.groupby('game_id')['close'].diff()
kalshi['pc_next1'] = kalshi.groupby('game_id')['price_change'].shift(-1)
kalshi['pc_next2'] = kalshi.groupby('game_id')['price_change'].shift(-2)
kalshi['pc_next3'] = kalshi.groupby('game_id')['price_change'].shift(-3)

# Focus on large moves
large_moves = kalshi[kalshi['price_change'].abs() > 5].copy()

# Create figure
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# PLOT 1: Reversal Rate by Threshold
print("Creating plot 1: Reversal rates...")
ax1 = axes[0, 0]
thresholds = [3, 4, 5, 6, 7, 8, 9, 10]
reversal_rates = []
counts = []

for thresh in thresholds:
    subset = kalshi[kalshi['price_change'].abs() > thresh].copy()
    subset['reverses'] = np.sign(subset['price_change']) != np.sign(subset['pc_next3'])
    valid = subset[subset['pc_next3'].notna()]
    reversal_rates.append(valid['reverses'].mean() * 100)
    counts.append(len(valid))

ax1.bar(thresholds, reversal_rates, color='steelblue', alpha=0.7)
ax1.axhline(50, color='red', linestyle='--', linewidth=2, label='Random (50%)')
ax1.axhline(55, color='orange', linestyle='--', linewidth=1, label='Breakeven after fees')
ax1.set_xlabel('Move Threshold (%)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Reversal Rate (%)', fontsize=12, fontweight='bold')
ax1.set_title('Mean Reversion: Reversal Rate by Move Size\n(3-minute lag)', 
              fontsize=14, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Add count labels
for i, (thresh, rate, count) in enumerate(zip(thresholds, reversal_rates, counts)):
    ax1.text(thresh, rate + 1, f'{count:,}\ntrades', ha='center', fontsize=8)

# PLOT 2: Time evolution of reversal
print("Creating plot 2: Time evolution...")
ax2 = axes[0, 1]
lags = [1, 2, 3]
lag_reversals = []

subset = kalshi[kalshi['price_change'].abs() > 7].copy()
for lag in lags:
    col = f'pc_next{lag}'
    subset['reverses'] = np.sign(subset['price_change']) != np.sign(subset[col])
    valid = subset[subset[col].notna()]
    lag_reversals.append(valid['reverses'].mean() * 100)

ax2.plot(lags, lag_reversals, marker='o', linewidth=3, markersize=10, color='darkgreen')
ax2.axhline(50, color='red', linestyle='--', linewidth=2, label='Random')
ax2.fill_between(lags, 50, lag_reversals, alpha=0.3, color='green')
ax2.set_xlabel('Minutes After Large Move', fontsize=12, fontweight='bold')
ax2.set_ylabel('Reversal Rate (%)', fontsize=12, fontweight='bold')
ax2.set_title('Mean Reversion Strengthens Over Time\n(After 7%+ moves)', 
              fontsize=14, fontweight='bold')
ax2.set_xticks(lags)
ax2.legend()
ax2.grid(True, alpha=0.3)

# PLOT 3: P&L Distribution
print("Creating plot 3: P&L distribution...")
ax3 = axes[1, 0]

# Calculate actual trade P&L
subset = kalshi[kalshi['price_change'].abs() > 7].copy()
subset['future'] = subset['pc_next3']
subset['reverses'] = np.sign(subset['price_change']) != np.sign(subset['future'])
valid = subset[subset['future'].notna()].copy()

# P&L for each trade (before fees)
valid['gross_pl'] = np.where(valid['reverses'], 
                               valid['future'].abs(), 
                               -valid['future'].abs())

ax3.hist(valid['gross_pl'], bins=50, color='steelblue', alpha=0.7, edgecolor='black')
ax3.axvline(0, color='red', linestyle='--', linewidth=2, label='Breakeven')
ax3.axvline(valid['gross_pl'].mean(), color='green', linestyle='--', linewidth=2, 
            label=f"Mean: {valid['gross_pl'].mean():.2f}%")
ax3.set_xlabel('Gross P&L per Trade (%)', fontsize=12, fontweight='bold')
ax3.set_ylabel('Frequency', fontsize=12, fontweight='bold')
ax3.set_title('Distribution of Trade Outcomes\n(Before Fees)', 
              fontsize=14, fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3)

# PLOT 4: Profitability Analysis
print("Creating plot 4: Profitability breakdown...")
ax4 = axes[1, 1]

# Calculate expected P&L at different fee levels
fee_levels = np.linspace(0, 4, 20)
thresholds_to_test = [5, 6, 7, 8]
colors = ['blue', 'green', 'orange', 'red']

for thresh, color in zip(thresholds_to_test, colors):
    subset = kalshi[kalshi['price_change'].abs() > thresh].copy()
    subset['future'] = subset['pc_next3']
    subset['reverses'] = np.sign(subset['price_change']) != np.sign(subset['future'])
    valid = subset[subset['future'].notna()].copy()
    
    wins = valid[valid['reverses']]
    losses = valid[~valid['reverses']]
    
    win_rate = valid['reverses'].mean()
    avg_win = wins['future'].abs().mean() if len(wins) > 0 else 0
    avg_loss = losses['future'].abs().mean() if len(losses) > 0 else 0
    
    gross_pl = win_rate * avg_win - (1 - win_rate) * avg_loss
    
    net_pls = [gross_pl - fee for fee in fee_levels]
    
    ax4.plot(fee_levels, net_pls, linewidth=2, label=f'>{thresh}% moves', color=color)

ax4.axhline(0, color='black', linestyle='-', linewidth=2)
ax4.axvline(2.75, color='red', linestyle='--', linewidth=2, label='Current Kalshi fees')
ax4.fill_between(fee_levels, 0, -5, alpha=0.2, color='red')
ax4.set_xlabel('Round-Trip Fee (%)', fontsize=12, fontweight='bold')
ax4.set_ylabel('Expected Net P&L per Trade (%)', fontsize=12, fontweight='bold')
ax4.set_title('Profitability vs Fee Structure\n(3-minute hold period)', 
              fontsize=14, fontweight='bold')
ax4.legend()
ax4.grid(True, alpha=0.3)
ax4.set_ylim(-4, 2)

plt.tight_layout()
plt.savefig('outputs/figures/edge_analysis.png', dpi=300, bbox_inches='tight')
print("\nSaved visualization to: outputs/figures/edge_analysis.png")

# Print summary stats
print("\n" + "=" * 80)
print("VISUALIZATION SUMMARY")
print("=" * 80)
print(f"\nKey Statistics:")
print(f"  • Reversal rate (>7% moves, 3-min lag): {lag_reversals[-1]:.1f}%")
print(f"  • Number of opportunities: {len(valid):,} trades")
print(f"  • Mean gross P&L: {valid['gross_pl'].mean():.2f}%")
print(f"  • Std dev: {valid['gross_pl'].std():.2f}%")
print(f"  • Win rate: {win_rate:.1%}")
print(f"\nAt current Kalshi fees (2.75%):")
print(f"  • Expected net P/L: {gross_pl - 2.75:+.2f}%")
print(f"  • Status: {'PROFITABLE' if gross_pl - 2.75 > 0 else 'UNPROFITABLE'}")

plt.show()

print("\nVisualization complete!")

