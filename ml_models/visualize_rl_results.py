"""
Visualize RL vs Static exit strategy comparison results.

Generates charts and analysis to understand when and why RL performs differently.
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)


def load_results(output_dir='ml_models/outputs'):
    """Load comparison results from CSV files."""
    comparison_file = os.path.join(output_dir, 'rl_vs_static_comparison.csv')
    static_trades_file = os.path.join(output_dir, 'static_exit_trades.csv')
    rl_trades_file = os.path.join(output_dir, 'rl_exit_trades.csv')
    
    if not os.path.exists(comparison_file):
        raise FileNotFoundError(f"Results not found: {comparison_file}")
    
    comparison_df = pd.read_csv(comparison_file)
    static_trades = pd.read_csv(static_trades_file) if os.path.exists(static_trades_file) else pd.DataFrame()
    rl_trades = pd.read_csv(rl_trades_file) if os.path.exists(rl_trades_file) else pd.DataFrame()
    
    return comparison_df, static_trades, rl_trades


def plot_pl_distribution(static_trades, rl_trades, output_dir):
    """Plot P/L distribution comparison."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Histogram
    bins = np.linspace(
        min(static_trades['net_pl'].min(), rl_trades['net_pl'].min()),
        max(static_trades['net_pl'].max(), rl_trades['net_pl'].max()),
        50
    )
    
    ax1.hist(static_trades['net_pl'], bins=bins, alpha=0.5, label='Static', color='blue')
    ax1.hist(rl_trades['net_pl'], bins=bins, alpha=0.5, label='RL', color='orange')
    ax1.axvline(0, color='red', linestyle='--', alpha=0.5)
    ax1.set_xlabel('Net P/L ($)')
    ax1.set_ylabel('Frequency')
    ax1.set_title('P/L Distribution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Box plot
    data_to_plot = [static_trades['net_pl'], rl_trades['net_pl']]
    ax2.boxplot(data_to_plot, labels=['Static', 'RL'])
    ax2.axhline(0, color='red', linestyle='--', alpha=0.5)
    ax2.set_ylabel('Net P/L ($)')
    ax2.set_title('P/L Box Plot')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'pl_distribution.png'), dpi=300, bbox_inches='tight')
    print(f"[OK] Saved P/L distribution plot")
    plt.close()


def plot_cumulative_pl(static_trades, rl_trades, output_dir):
    """Plot cumulative P/L over time."""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    static_cumpl = np.cumsum(static_trades['net_pl'])
    rl_cumpl = np.cumsum(rl_trades['net_pl'])
    
    ax.plot(static_cumpl, label='Static', linewidth=2, alpha=0.7)
    ax.plot(rl_cumpl, label='RL', linewidth=2, alpha=0.7)
    ax.axhline(0, color='red', linestyle='--', alpha=0.3)
    ax.set_xlabel('Trade Number')
    ax.set_ylabel('Cumulative P/L ($)')
    ax.set_title('Cumulative P/L Comparison')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'cumulative_pl.png'), dpi=300, bbox_inches='tight')
    print(f"[OK] Saved cumulative P/L plot")
    plt.close()


def plot_exit_timing_analysis(static_trades, rl_trades, output_dir):
    """Analyze exit timing patterns."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. Hold time distribution
    ax = axes[0, 0]
    ax.hist(static_trades['minutes_held'], bins=30, alpha=0.5, label='Static', color='blue')
    ax.hist(rl_trades['minutes_held'], bins=30, alpha=0.5, label='RL', color='orange')
    ax.set_xlabel('Minutes Held')
    ax.set_ylabel('Frequency')
    ax.set_title('Hold Time Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. P/L vs Hold Time
    ax = axes[0, 1]
    ax.scatter(static_trades['minutes_held'], static_trades['net_pl'], alpha=0.3, label='Static', s=10)
    ax.scatter(rl_trades['minutes_held'], rl_trades['net_pl'], alpha=0.3, label='RL', s=10)
    ax.axhline(0, color='red', linestyle='--', alpha=0.3)
    ax.set_xlabel('Minutes Held')
    ax.set_ylabel('Net P/L ($)')
    ax.set_title('P/L vs Hold Time')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. Exit price distribution
    ax = axes[1, 0]
    ax.hist(static_trades['exit_price'], bins=30, alpha=0.5, label='Static', color='blue')
    ax.hist(rl_trades['exit_price'], bins=30, alpha=0.5, label='RL', color='orange')
    ax.set_xlabel('Exit Price (cents)')
    ax.set_ylabel('Frequency')
    ax.set_title('Exit Price Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 4. Entry price distribution
    ax = axes[1, 1]
    ax.hist(static_trades['entry_price'], bins=30, alpha=0.5, label='Static', color='blue')
    ax.hist(rl_trades['entry_price'], bins=30, alpha=0.5, label='RL', color='orange')
    ax.set_xlabel('Entry Price (cents)')
    ax.set_ylabel('Frequency')
    ax.set_title('Entry Price Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'exit_timing_analysis.png'), dpi=300, bbox_inches='tight')
    print(f"[OK] Saved exit timing analysis")
    plt.close()


def plot_win_rate_by_scenario(static_trades, rl_trades, output_dir):
    """Analyze win rate by different scenarios."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    # Categorize by entry price (low/mid/high)
    def categorize_price(price):
        if price < 30:
            return 'Low (0-30)'
        elif price < 70:
            return 'Mid (30-70)'
        else:
            return 'High (70-100)'
    
    static_trades['price_category'] = static_trades['entry_price'].apply(categorize_price)
    rl_trades['price_category'] = rl_trades['entry_price'].apply(categorize_price)
    
    # 1. Win rate by price category
    ax = axes[0]
    categories = ['Low (0-30)', 'Mid (30-70)', 'High (70-100)']
    static_winrates = []
    rl_winrates = []
    
    for cat in categories:
        static_wins = (static_trades[static_trades['price_category'] == cat]['net_pl'] > 0).mean()
        rl_wins = (rl_trades[rl_trades['price_category'] == cat]['net_pl'] > 0).mean()
        static_winrates.append(static_wins * 100)
        rl_winrates.append(rl_wins * 100)
    
    x = np.arange(len(categories))
    width = 0.35
    ax.bar(x - width/2, static_winrates, width, label='Static', alpha=0.8)
    ax.bar(x + width/2, rl_winrates, width, label='RL', alpha=0.8)
    ax.set_xlabel('Entry Price Category')
    ax.set_ylabel('Win Rate (%)')
    ax.set_title('Win Rate by Entry Price')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=15)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 2. Win rate by hold time
    ax = axes[1]
    def categorize_hold_time(minutes):
        if minutes < 5:
            return '0-5 min'
        elif minutes < 10:
            return '5-10 min'
        else:
            return '10+ min'
    
    static_trades['hold_category'] = static_trades['minutes_held'].apply(categorize_hold_time)
    rl_trades['hold_category'] = rl_trades['minutes_held'].apply(categorize_hold_time)
    
    hold_categories = ['0-5 min', '5-10 min', '10+ min']
    static_winrates = []
    rl_winrates = []
    
    for cat in hold_categories:
        static_wins = (static_trades[static_trades['hold_category'] == cat]['net_pl'] > 0).mean()
        rl_wins = (rl_trades[rl_trades['hold_category'] == cat]['net_pl'] > 0).mean()
        static_winrates.append(static_wins * 100)
        rl_winrates.append(rl_wins * 100)
    
    x = np.arange(len(hold_categories))
    ax.bar(x - width/2, static_winrates, width, label='Static', alpha=0.8)
    ax.bar(x + width/2, rl_winrates, width, label='RL', alpha=0.8)
    ax.set_xlabel('Hold Time')
    ax.set_ylabel('Win Rate (%)')
    ax.set_title('Win Rate by Hold Time')
    ax.set_xticks(x)
    ax.set_xticklabels(hold_categories)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3. Average P/L by scenario
    ax = axes[2]
    scenarios = ['All', 'Low Price', 'Mid Price', 'High Price']
    static_avg_pls = [
        static_trades['net_pl'].mean(),
        static_trades[static_trades['price_category'] == 'Low (0-30)']['net_pl'].mean(),
        static_trades[static_trades['price_category'] == 'Mid (30-70)']['net_pl'].mean(),
        static_trades[static_trades['price_category'] == 'High (70-100)']['net_pl'].mean()
    ]
    rl_avg_pls = [
        rl_trades['net_pl'].mean(),
        rl_trades[rl_trades['price_category'] == 'Low (0-30)']['net_pl'].mean(),
        rl_trades[rl_trades['price_category'] == 'Mid (30-70)']['net_pl'].mean(),
        rl_trades[rl_trades['price_category'] == 'High (70-100)']['net_pl'].mean()
    ]
    
    x = np.arange(len(scenarios))
    ax.bar(x - width/2, static_avg_pls, width, label='Static', alpha=0.8)
    ax.bar(x + width/2, rl_avg_pls, width, label='RL', alpha=0.8)
    ax.axhline(0, color='red', linestyle='--', alpha=0.3)
    ax.set_xlabel('Scenario')
    ax.set_ylabel('Avg P/L ($)')
    ax.set_title('Average P/L by Scenario')
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=15)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'win_rate_by_scenario.png'), dpi=300, bbox_inches='tight')
    print(f"[OK] Saved win rate by scenario analysis")
    plt.close()


def generate_summary_report(comparison_df, static_trades, rl_trades, output_dir):
    """Generate HTML summary report."""
    html = f"""
    <html>
    <head>
        <title>RL vs Static Exit Strategy Comparison</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: auto; background: white; padding: 30px; border-radius: 10px; }}
            h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #3498db; color: white; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .metric {{ display: inline-block; margin: 10px 20px; padding: 15px; background: #ecf0f1; border-radius: 5px; }}
            .metric-label {{ font-size: 12px; color: #7f8c8d; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
            .success {{ color: #27ae60; }}
            .fail {{ color: #e74c3c; }}
            img {{ max-width: 100%; height: auto; margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>RL vs Static Exit Strategy Comparison</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Performance Summary</h2>
            <div>
                <div class="metric">
                    <div class="metric-label">Total Trades (Static)</div>
                    <div class="metric-value">{comparison_df.loc[0, 'Total Trades']:.0f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Trades (RL)</div>
                    <div class="metric-value">{comparison_df.loc[1, 'Total Trades']:.0f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Win Rate (Static)</div>
                    <div class="metric-value">{comparison_df.loc[0, 'Win Rate']*100:.1f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Win Rate (RL)</div>
                    <div class="metric-value">{comparison_df.loc[1, 'Win Rate']*100:.1f}%</div>
                </div>
            </div>
            
            <h2>Detailed Metrics</h2>
            {comparison_df.to_html(index=False, classes='table')}
            
            <h2>Improvement Analysis</h2>
            <div class="metric">
                <div class="metric-label">P/L Improvement</div>
                <div class="metric-value {'success' if comparison_df.loc[1, 'Total P/L'] > comparison_df.loc[0, 'Total P/L'] else 'fail'}">
                    ${comparison_df.loc[1, 'Total P/L'] - comparison_df.loc[0, 'Total P/L']:+.2f}
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">Sharpe Improvement</div>
                <div class="metric-value {'success' if comparison_df.loc[1, 'Sharpe Ratio'] > comparison_df.loc[0, 'Sharpe Ratio'] else 'fail'}">
                    {comparison_df.loc[1, 'Sharpe Ratio'] - comparison_df.loc[0, 'Sharpe Ratio']:+.3f}
                </div>
            </div>
            
            <h2>Visualizations</h2>
            
            <h3>P/L Distribution</h3>
            <img src="pl_distribution.png" alt="P/L Distribution">
            
            <h3>Cumulative P/L</h3>
            <img src="cumulative_pl.png" alt="Cumulative P/L">
            
            <h3>Exit Timing Analysis</h3>
            <img src="exit_timing_analysis.png" alt="Exit Timing Analysis">
            
            <h3>Win Rate by Scenario</h3>
            <img src="win_rate_by_scenario.png" alt="Win Rate by Scenario">
            
            <h2>Conclusion</h2>
            <p style="font-size: 18px;">
                {'<span class="success">✓ RL strategy outperforms static exit!</span>' 
                 if (comparison_df.loc[1, 'Total P/L'] > comparison_df.loc[0, 'Total P/L'] and 
                     comparison_df.loc[1, 'Sharpe Ratio'] > comparison_df.loc[0, 'Sharpe Ratio'])
                 else '<span class="fail">✗ Static exit remains the better strategy</span>'}
            </p>
        </div>
    </body>
    </html>
    """
    
    report_file = os.path.join(output_dir, 'rl_comparison_report.html')
    with open(report_file, 'w') as f:
        f.write(html)
    
    print(f"[OK] Saved HTML report to {report_file}")


def visualize_results(output_dir='ml_models/outputs'):
    """Main visualization function."""
    print("="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)
    
    # Load results
    print("\nLoading results...")
    comparison_df, static_trades, rl_trades = load_results(output_dir)
    
    if len(static_trades) == 0 or len(rl_trades) == 0:
        print("[ERROR] No trade data found. Run comparison first.")
        return
    
    print(f"[OK] Loaded {len(static_trades)} static trades and {len(rl_trades)} RL trades")
    
    # Generate plots
    print("\nGenerating plots...")
    plot_pl_distribution(static_trades, rl_trades, output_dir)
    plot_cumulative_pl(static_trades, rl_trades, output_dir)
    plot_exit_timing_analysis(static_trades, rl_trades, output_dir)
    plot_win_rate_by_scenario(static_trades, rl_trades, output_dir)
    
    # Generate HTML report
    print("\nGenerating summary report...")
    generate_summary_report(comparison_df, static_trades, rl_trades, output_dir)
    
    print("\n" + "="*80)
    print("VISUALIZATION COMPLETE")
    print("="*80)
    print(f"\nView results:")
    print(f"  HTML Report: {output_dir}/rl_comparison_report.html")
    print(f"  Charts: {output_dir}/*.png")


if __name__ == "__main__":
    visualize_results()

