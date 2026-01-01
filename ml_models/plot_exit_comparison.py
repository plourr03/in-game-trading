"""
Plot Exit Strategy Comparison
Creates visualizations comparing static vs dynamic exit strategies
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load results
results = pd.read_csv('ml_models/exit_strategy_comparison.csv')

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# 1. Win Rate Comparison
strategies = results['strategy'].str.upper()
win_rates = results['win_rate'] * 100

ax1.bar(strategies, win_rates, color=['#3498db', '#e74c3c'], alpha=0.7, edgecolor='black', linewidth=2)
ax1.set_ylabel('Win Rate (%)', fontsize=12)
ax1.set_title('Win Rate Comparison', fontsize=14, fontweight='bold')
ax1.grid(axis='y', alpha=0.3)
for i, v in enumerate(win_rates):
    ax1.text(i, v + 0.1, f'{v:.1f}%', ha='center', fontweight='bold')

# 2. Total P/L Comparison
total_pls = results['total_pl']
colors = ['red' if x < 0 else 'green' for x in total_pls]

ax2.bar(strategies, total_pls, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax2.set_ylabel('Total P/L ($)', fontsize=12)
ax2.set_title('Total Profit/Loss', fontsize=14, fontweight='bold')
ax2.grid(axis='y', alpha=0.3)
for i, v in enumerate(total_pls):
    ax2.text(i, v + (5000 if v > 0 else -5000), f'${v:,.0f}', ha='center', fontweight='bold')

# 3. Average Hold Time
hold_times = results['avg_hold']

ax3.bar(strategies, hold_times, color=['#9b59b6', '#f39c12'], alpha=0.7, edgecolor='black', linewidth=2)
ax3.set_ylabel('Minutes', fontsize=12)
ax3.set_title('Average Hold Duration', fontsize=14, fontweight='bold')
ax3.grid(axis='y', alpha=0.3)
for i, v in enumerate(hold_times):
    ax3.text(i, v + 0.3, f'{v:.1f}m', ha='center', fontweight='bold')

# 4. Sharpe Ratio
sharpes = results['sharpe']

ax4.bar(strategies, sharpes, color=['#1abc9c', '#e67e22'], alpha=0.7, edgecolor='black', linewidth=2)
ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax4.set_ylabel('Sharpe Ratio', fontsize=12)
ax4.set_title('Risk-Adjusted Returns (Sharpe)', fontsize=14, fontweight='bold')
ax4.grid(axis='y', alpha=0.3)
for i, v in enumerate(sharpes):
    ax4.text(i, v + (5 if v > 0 else -5), f'{v:.2f}', ha='center', fontweight='bold')

plt.suptitle('Exit Strategy Comparison: Static vs Dynamic ML', fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig('ml_models/exit_strategy_comparison.png', dpi=300, bbox_inches='tight')
print("[OK] Comparison chart saved: ml_models/exit_strategy_comparison.png")

# Additional chart: Trade count
fig2, ax = plt.subplots(figsize=(8, 6))
trade_counts = results['trades']
ax.bar(strategies, trade_counts, color='#34495e', alpha=0.7, edgecolor='black', linewidth=2)
ax.set_ylabel('Number of Trades', fontsize=12)
ax.set_title('Total Trades Executed', fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
for i, v in enumerate(trade_counts):
    ax.text(i, v + 200, f'{v:,}', ha='center', fontweight='bold')
plt.tight_layout()
plt.savefig('ml_models/exit_strategy_trades.png', dpi=300, bbox_inches='tight')
print("[OK] Trade count chart saved: ml_models/exit_strategy_trades.png")

print("\n[COMPLETE] All visualizations created!")

