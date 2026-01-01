"""
Visualize threshold performance
"""
import pandas as pd
import matplotlib.pyplot as plt

# Load results
df = pd.read_csv('ml_models/outputs/advanced_threshold_results.csv')

# Create figure
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

# Plot 1: Trades vs Threshold
ax1.bar(df['threshold'], df['trades'], color='steelblue', edgecolor='navy', linewidth=1.5)
ax1.set_xlabel('Threshold', fontsize=12, fontweight='bold')
ax1.set_ylabel('Number of Trades', fontsize=12, fontweight='bold')
ax1.set_title('Trade Volume by Threshold', fontsize=14, fontweight='bold')
ax1.grid(axis='y', alpha=0.3)
for i, (t, v) in enumerate(zip(df['threshold'], df['trades'])):
    ax1.text(t, v + 50, str(v), ha='center', va='bottom', fontweight='bold')

# Plot 2: Win Rate vs Threshold
colors = ['red' if wr < 0.5 else 'green' for wr in df['win_rate']]
ax2.bar(df['threshold'], df['win_rate'] * 100, color=colors, edgecolor='darkgreen', linewidth=1.5, alpha=0.7)
ax2.axhline(y=50, color='black', linestyle='--', linewidth=2, label='Break-even (50%)')
ax2.set_xlabel('Threshold', fontsize=12, fontweight='bold')
ax2.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
ax2.set_title('Win Rate by Threshold', fontsize=14, fontweight='bold')
ax2.legend()
ax2.grid(axis='y', alpha=0.3)
for i, (t, v) in enumerate(zip(df['threshold'], df['win_rate'])):
    ax2.text(t, v * 100 + 1, f"{v*100:.1f}%", ha='center', va='bottom', fontweight='bold', fontsize=9)

# Plot 3: P/L at different contract sizes
ax3.plot(df['threshold'], df['total_pl_100'], 'o-', linewidth=2, markersize=8, label='100 contracts', color='blue')
ax3.plot(df['threshold'], df['total_pl_500'], 's-', linewidth=2, markersize=8, label='500 contracts', color='green')
ax3.plot(df['threshold'], df['total_pl_1000'], '^-', linewidth=2, markersize=8, label='1000 contracts', color='red')
ax3.axhline(y=0, color='black', linestyle='--', linewidth=1)
ax3.set_xlabel('Threshold', fontsize=12, fontweight='bold')
ax3.set_ylabel('Total P/L ($)', fontsize=12, fontweight='bold')
ax3.set_title('Profit/Loss by Threshold & Position Size', fontsize=14, fontweight='bold')
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3)

# Plot 4: Risk-Reward
efficiency = df['total_pl_500'] / df['trades']  # Profit per trade at 500 contracts
colors_eff = ['red' if e < 0 else 'green' for e in efficiency]
ax4.bar(df['threshold'], efficiency, color=colors_eff, edgecolor='black', linewidth=1.5, alpha=0.7)
ax4.axhline(y=0, color='black', linestyle='--', linewidth=2)
ax4.set_xlabel('Threshold', fontsize=12, fontweight='bold')
ax4.set_ylabel('Profit per Trade ($)', fontsize=12, fontweight='bold')
ax4.set_title('Efficiency: P/L per Trade (500 contracts)', fontsize=14, fontweight='bold')
ax4.grid(axis='y', alpha=0.3)
for i, (t, v) in enumerate(zip(df['threshold'], efficiency)):
    ax4.text(t, v + (0.5 if v > 0 else -0.5), f"${v:.2f}", ha='center', 
             va='bottom' if v > 0 else 'top', fontweight='bold', fontsize=9)

plt.suptitle('Advanced PBP Model: Threshold Analysis', fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig('ml_models/outputs/threshold_analysis.png', dpi=200, bbox_inches='tight')
print("Saved: ml_models/outputs/threshold_analysis.png")

# Also create summary stats
print("\n" + "="*100)
print("THRESHOLD ANALYSIS SUMMARY")
print("="*100)
print(df.to_string(index=False))





