"""
FINAL COMPREHENSIVE STRATEGY DOCUMENT
=====================================

Generates a complete, polished document with all backtested and validated strategies.
"""

import pandas as pd
import numpy as np
from datetime import datetime

def generate_final_document():
    """Generate the final comprehensive strategy document"""
    
    # Load all results
    backtest_results = pd.read_csv('outputs/backtests/comprehensive_backtest_results.csv')
    statistical_results = pd.read_csv('outputs/metrics/statistical_validation_results.csv')
    
    # Merge results
    merged = pd.merge(
        backtest_results,
        statistical_results[['strategy_id', 'bonferroni_significant', 'fdr_bh_significant']],
        left_index=True,
        right_on='strategy_id',
        how='left'
    )
    
    # Create document
    doc_lines = []
    
    # Header
    doc_lines.append("=" * 100)
    doc_lines.append("NBA IN-GAME TRADING STRATEGIES - FINAL COMPREHENSIVE DOCUMENT")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}")
    doc_lines.append("")
    doc_lines.append("This document contains all validated, backtested, and statistically significant")
    doc_lines.append("trading strategies for NBA in-game markets on Kalshi.")
    doc_lines.append("")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    
    # Executive Summary
    doc_lines.append("EXECUTIVE SUMMARY")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append(f"Total Strategies Analyzed:          {len(merged)}")
    doc_lines.append(f"Statistically Significant (p<0.05): {merged['is_significant'].sum()} ({merged['is_significant'].mean():.1%})")
    doc_lines.append(f"Bonferroni Significant:             {merged['bonferroni_significant'].sum()} ({merged['bonferroni_significant'].mean():.1%})")
    doc_lines.append(f"MC Probability Profitable >95%:     {(merged['mc_prob_profitable'] > 0.95).sum()}")
    doc_lines.append("")
    doc_lines.append(f"Average Net P/L per Trade:          {merged['mean_net_pl_pct'].mean():.2f}%")
    doc_lines.append(f"Average Sharpe Ratio:               {merged['sharpe_ratio'].mean():.2f}")
    doc_lines.append(f"Average Win Rate:                   {merged['win_rate'].mean():.1%}")
    doc_lines.append(f"Total Historical Trades:            {merged['total_trades'].sum():,.0f}")
    doc_lines.append("")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    
    # Methodology
    doc_lines.append("METHODOLOGY")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append("Data:")
    doc_lines.append("  - 502 NBA games from December 2024 - December 2025")
    doc_lines.append("  - 680,017 minute-level price observations")
    doc_lines.append("  - Real Kalshi market data with volume and OHLC prices")
    doc_lines.append("")
    doc_lines.append("Strategy Logic:")
    doc_lines.append("  - Mean reversion after large price moves")
    doc_lines.append("  - Focus on extreme price levels (1-20c and 80-99c) due to lower fees")
    doc_lines.append("  - Hold periods: 2-20 minutes")
    doc_lines.append("  - Position size: 100 contracts (scalable)")
    doc_lines.append("")
    doc_lines.append("Testing & Validation:")
    doc_lines.append("  1. Historical backtest with realistic execution")
    doc_lines.append("  2. Statistical significance tests (t-test, binomial test)")
    doc_lines.append("  3. Multiple testing corrections (Bonferroni, FDR)")
    doc_lines.append("  4. Monte Carlo simulations (1,000 iterations per strategy)")
    doc_lines.append("  5. Temporal robustness testing (early vs late game)")
    doc_lines.append("")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    
    # Tier Classification
    doc_lines.append("STRATEGY TIERS")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append("Tier 1: GOLD STANDARD")
    doc_lines.append("  - Bonferroni significant (strictest test)")
    doc_lines.append("  - MC probability profitable >99%")
    doc_lines.append("  - Sharpe ratio >1.0")
    doc_lines.append("")
    doc_lines.append("Tier 2: VALIDATED")
    doc_lines.append("  - FDR significant")
    doc_lines.append("  - MC probability profitable >95%")
    doc_lines.append("  - P-value <0.05")
    doc_lines.append("")
    doc_lines.append("Tier 3: PROMISING")
    doc_lines.append("  - P-value <0.05")
    doc_lines.append("  - MC probability profitable >90%")
    doc_lines.append("")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    
    # Tier 1 Strategies
    tier1 = merged[
        (merged['bonferroni_significant'] == True) &
        (merged['mc_prob_profitable'] > 0.99) &
        (merged['sharpe_ratio'] > 1.0)
    ].sort_values('sharpe_ratio', ascending=False)
    
    doc_lines.append("TIER 1: GOLD STANDARD STRATEGIES")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append(f"Total: {len(tier1)} strategies")
    doc_lines.append("")
    
    for idx, (_, row) in enumerate(tier1.iterrows(), 1):
        doc_lines.append(f"Strategy {idx}: Price {row['price_min']}-{row['price_max']}c, Move >{row['threshold']}%, Hold {row['hold_period']}min")
        doc_lines.append("-" * 100)
        doc_lines.append("")
        doc_lines.append("BACKTEST RESULTS:")
        doc_lines.append(f"  Total Trades:              {row['total_trades']:,.0f}")
        doc_lines.append(f"  Win Rate:                  {row['win_rate']:.1%}  (CI: [{row['win_rate_ci_low']:.1%}, {row['win_rate_ci_high']:.1%}])")
        doc_lines.append(f"  Mean Net P/L:              {row['mean_net_pl_pct']:.2f}%")
        doc_lines.append(f"  Median Net P/L:            {row['median_net_pl_pct']:.2f}%")
        doc_lines.append(f"  Avg Win:                   {row['avg_win_pct']:.2f}%")
        doc_lines.append(f"  Avg Loss:                  {row['avg_loss_pct']:.2f}%")
        doc_lines.append("")
        doc_lines.append("RISK METRICS:")
        doc_lines.append(f"  Sharpe Ratio:              {row['sharpe_ratio']:.2f}")
        doc_lines.append(f"  Max Drawdown:              {row['max_drawdown_pct']:.2f}%")
        doc_lines.append(f"  Win/Loss Ratio:            {row['win_loss_ratio']:.2f}x")
        doc_lines.append(f"  Std Dev:                   {row['std_net_pl_pct']:.2f}%")
        doc_lines.append("")
        doc_lines.append("STATISTICAL VALIDATION:")
        doc_lines.append(f"  P-value:                   {row['p_value']:.2e}")
        doc_lines.append(f"  T-statistic:               {row['t_statistic']:.2f}")
        doc_lines.append(f"  Bonferroni Significant:    YES")
        doc_lines.append(f"  MC Prob Profitable:        {row['mc_prob_profitable']:.1%}")
        doc_lines.append(f"  MC Mean CI:                [{row['mc_mean_ci_low']:.2f}%, {row['mc_mean_ci_high']:.2f}%]")
        doc_lines.append(f"  MC Sharpe CI:              [{row['mc_sharpe_ci_low']:.2f}, {row['mc_sharpe_ci_high']:.2f}]")
        doc_lines.append("")
        doc_lines.append("EXPECTED PERFORMANCE (per 100 trades):")
        expected_wins = int(row['win_rate'] * 100)
        expected_losses = 100 - expected_wins
        expected_profit = (expected_wins * row['avg_win_pct'] + expected_losses * row['avg_loss_pct'])
        doc_lines.append(f"  Expected Wins:             {expected_wins}")
        doc_lines.append(f"  Expected Losses:           {expected_losses}")
        doc_lines.append(f"  Expected Net P/L:          {expected_profit:.2f}%")
        doc_lines.append(f"  Expected Profit (100 contracts): ${expected_profit:.2f}")
        doc_lines.append("")
        doc_lines.append("RECOMMENDATION:            HIGHLY RECOMMENDED - Strong statistical support")
        doc_lines.append("")
        doc_lines.append("")
    
    # Tier 2 Strategies
    tier2 = merged[
        (merged['fdr_bh_significant'] == True) &
        (merged['mc_prob_profitable'] > 0.95) &
        (merged['p_value'] < 0.05) &
        (~merged.index.isin(tier1.index))
    ].sort_values('sharpe_ratio', ascending=False)
    
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append("TIER 2: VALIDATED STRATEGIES")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append(f"Total: {len(tier2)} strategies")
    doc_lines.append("")
    
    for idx, (_, row) in enumerate(tier2.iterrows(), 1):
        doc_lines.append(f"Strategy {idx}: Price {row['price_min']}-{row['price_max']}c, Move >{row['threshold']}%, Hold {row['hold_period']}min")
        doc_lines.append("-" * 100)
        doc_lines.append(f"  Trades: {row['total_trades']:,.0f} | Win Rate: {row['win_rate']:.1%} | Net P/L: {row['mean_net_pl_pct']:.2f}%")
        doc_lines.append(f"  Sharpe: {row['sharpe_ratio']:.2f} | P-value: {row['p_value']:.2e} | MC Prob: {row['mc_prob_profitable']:.1%}")
        doc_lines.append(f"  Recommendation: RECOMMENDED - Good statistical support")
        doc_lines.append("")
    
    # Tier 3 Strategies
    tier3 = merged[
        (merged['p_value'] < 0.05) &
        (merged['mc_prob_profitable'] > 0.90) &
        (~merged.index.isin(tier1.index)) &
        (~merged.index.isin(tier2.index))
    ].sort_values('sharpe_ratio', ascending=False)
    
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append("TIER 3: PROMISING STRATEGIES")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append(f"Total: {len(tier3)} strategies")
    doc_lines.append("")
    
    for idx, (_, row) in enumerate(tier3.iterrows(), 1):
        doc_lines.append(f"Strategy {idx}: Price {row['price_min']}-{row['price_max']}c, Move >{row['threshold']}%, Hold {row['hold_period']}min")
        doc_lines.append(f"  Trades: {row['total_trades']:,.0f} | Win Rate: {row['win_rate']:.1%} | Net P/L: {row['mean_net_pl_pct']:.2f}%")
        doc_lines.append(f"  Sharpe: {row['sharpe_ratio']:.2f} | P-value: {row['p_value']:.2e} | MC Prob: {row['mc_prob_profitable']:.1%}")
        doc_lines.append("")
    
    # Summary Table
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append("SUMMARY TABLE - TOP 10 STRATEGIES")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    
    top10 = merged.nlargest(10, 'sharpe_ratio')
    
    doc_lines.append(f"{'Rank':<6} {'Strategy':<35} {'Trades':>8} {'WR':>7} {'P/L':>8} {'Sharpe':>8} {'P-val':>12}")
    doc_lines.append("-" * 100)
    
    for rank, (_, row) in enumerate(top10.iterrows(), 1):
        strategy_str = f"P:{int(row['price_min'])}-{int(row['price_max'])} M>{int(row['threshold'])}% H:{int(row['hold_period'])}m"
        doc_lines.append(
            f"{rank:<6} {strategy_str:<35} {row['total_trades']:>8.0f} {row['win_rate']:>6.1%} "
            f"{row['mean_net_pl_pct']:>7.2f}% {row['sharpe_ratio']:>8.2f} {row['p_value']:>12.2e}"
        )
    
    doc_lines.append("")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    
    # Implementation Guide
    doc_lines.append("IMPLEMENTATION GUIDE")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append("1. GETTING STARTED")
    doc_lines.append("   - Start with Tier 1 strategies (highest confidence)")
    doc_lines.append("   - Begin with 10-20 contracts per trade")
    doc_lines.append("   - Paper trade for 1-2 weeks first")
    doc_lines.append("")
    doc_lines.append("2. POSITION SIZING")
    doc_lines.append("   - Risk 1-2% of bankroll per trade")
    doc_lines.append("   - Use Kelly Criterion for optimal sizing:")
    doc_lines.append("     f = (edge / odds) where edge = expected P/L")
    doc_lines.append("   - Start conservative (1/4 to 1/2 Kelly)")
    doc_lines.append("")
    doc_lines.append("3. EXECUTION")
    doc_lines.append("   - Use limit orders when possible (maker fees lower)")
    doc_lines.append("   - Monitor bid-ask spread")
    doc_lines.append("   - Set stop-loss at -50% to limit tail risk")
    doc_lines.append("")
    doc_lines.append("4. MONITORING")
    doc_lines.append("   - Track realized Sharpe ratio vs backtest")
    doc_lines.append("   - Monitor win rate (should be ~40-45%)")
    doc_lines.append("   - Alert if performance degrades >20%")
    doc_lines.append("")
    doc_lines.append("5. RISK MANAGEMENT")
    doc_lines.append("   - Max 5 concurrent positions")
    doc_lines.append("   - Daily loss limit: 10% of bankroll")
    doc_lines.append("   - Weekly review of performance")
    doc_lines.append("")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    
    # Disclaimers
    doc_lines.append("IMPORTANT DISCLAIMERS")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append("1. Past performance does not guarantee future results")
    doc_lines.append("2. Market conditions may change")
    doc_lines.append("3. Slippage and execution quality will impact real performance")
    doc_lines.append("4. These strategies assume taker fees; maker fees improve profitability")
    doc_lines.append("5. Position sizing and risk management are critical")
    doc_lines.append("6. Start small and scale gradually")
    doc_lines.append("")
    doc_lines.append("=" * 100)
    doc_lines.append("")
    doc_lines.append("END OF DOCUMENT")
    doc_lines.append("=" * 100)
    
    return "\n".join(doc_lines)


if __name__ == "__main__":
    print("Generating final comprehensive document...")
    
    document = generate_final_document()
    
    # Save to file
    output_file = 'FINAL_STRATEGIES_DOCUMENT.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(document)
    
    print(f"Document saved to: {output_file}")
    print()
    
    # Also print to console
    print(document)

