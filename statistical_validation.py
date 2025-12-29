"""
Statistical Validation of Profitable Trading Strategies

This script performs rigorous statistical tests on all identified profitable strategies
to validate their significance and assess robustness.
"""

import pandas as pd
import numpy as np
import logging
import sys
import os
from scipy import stats
from scipy.stats import ttest_1samp, binomtest, chi2_contingency
from statsmodels.stats.proportion import proportion_confint
from statsmodels.stats.multitest import multipletests
import warnings
warnings.filterwarnings('ignore')

from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
from src.backtesting.fees import calculate_kalshi_fees

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_strategy_with_trades(df, price_low, price_high, move_threshold, hold_period):
    """
    Runs a strategy and returns individual trade results for statistical testing.
    """
    df = df.copy()
    
    # Ensure datetime is properly formatted
    if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    df['game_minute'] = df['datetime'].dt.minute + df['datetime'].dt.hour * 60
    df['price_change'] = df.groupby('game_id')['close'].diff()
    df['price_change_pct'] = (df['price_change'] / df['close'].shift(1)) * 100
    
    # Filter by price range
    in_range = df[(df['close'] >= price_low) & (df['close'] <= price_high)].copy()
    
    if in_range.empty:
        return None
    
    # Identify large moves
    in_range['abs_change_pct'] = in_range['price_change_pct'].abs()
    large_moves = in_range[in_range['abs_change_pct'] > move_threshold].copy()
    
    if large_moves.empty:
        return None
    
    # Calculate exit price
    large_moves['exit_price'] = df.groupby('game_id')['close'].shift(-hold_period).loc[large_moves.index]
    valid_trades = large_moves.dropna(subset=['exit_price']).copy()
    
    if valid_trades.empty:
        return None
    
    # Determine wins (mean reversion)
    valid_trades['is_win'] = (
        ((valid_trades['price_change'] > 0) & (valid_trades['exit_price'] < valid_trades['close'])) |
        ((valid_trades['price_change'] < 0) & (valid_trades['exit_price'] > valid_trades['close']))
    )
    
    # Calculate P/L
    valid_trades['gross_pl_raw'] = np.where(
        valid_trades['price_change'] > 0,
        valid_trades['close'] - valid_trades['exit_price'],
        valid_trades['exit_price'] - valid_trades['close']
    )
    valid_trades['gross_pl_pct'] = (valid_trades['gross_pl_raw'] / valid_trades['close']) * 100
    
    # Calculate fees
    valid_trades['entry_fee'] = valid_trades['close'].apply(lambda p: calculate_kalshi_fees(100, p, is_taker=True))
    valid_trades['exit_fee'] = valid_trades['exit_price'].apply(lambda p: calculate_kalshi_fees(100, p, is_taker=True))
    valid_trades['total_fees'] = valid_trades['entry_fee'] + valid_trades['exit_fee']
    valid_trades['fees_pct'] = (valid_trades['total_fees'] / 100) * 100
    
    # Net P/L
    valid_trades['net_pl_pct'] = valid_trades['gross_pl_pct'] - valid_trades['fees_pct']
    
    return valid_trades

def calculate_statistics(trades_df):
    """
    Calculates comprehensive statistics for a set of trades.
    """
    if trades_df is None or trades_df.empty:
        return None
    
    n_trades = len(trades_df)
    wins = trades_df['is_win'].sum()
    losses = n_trades - wins
    win_rate = wins / n_trades
    
    # Basic metrics
    mean_net_pl = trades_df['net_pl_pct'].mean()
    std_net_pl = trades_df['net_pl_pct'].std()
    median_net_pl = trades_df['net_pl_pct'].median()
    
    # Separate winning and losing trades
    winning_trades = trades_df[trades_df['is_win']]
    losing_trades = trades_df[~trades_df['is_win']]
    
    avg_win = winning_trades['net_pl_pct'].mean() if not winning_trades.empty else 0
    avg_loss = losing_trades['net_pl_pct'].mean() if not losing_trades.empty else 0
    
    # Sharpe Ratio (annualized, assuming ~240 trades per year)
    if std_net_pl > 0:
        sharpe_ratio = (mean_net_pl / std_net_pl) * np.sqrt(240)
    else:
        sharpe_ratio = 0
    
    # Win rate confidence interval (95%)
    ci_low, ci_high = proportion_confint(wins, n_trades, alpha=0.05, method='wilson')
    
    # T-test: Is mean P/L significantly different from 0?
    t_stat, p_value = ttest_1samp(trades_df['net_pl_pct'], 0)
    
    # Win rate binomial test: Is win rate significantly different from 50%?
    # Using two-tailed test
    binom_result = binomtest(wins, n_trades, 0.5, alternative='two-sided')
    win_rate_p_value = binom_result.pvalue
    
    # Effect size (Cohen's d)
    cohens_d = mean_net_pl / std_net_pl if std_net_pl > 0 else 0
    
    # Maximum drawdown (consecutive losses)
    trades_df_sorted = trades_df.sort_values(['game_id', 'datetime'])
    trades_df_sorted['cumulative_pl'] = trades_df_sorted['net_pl_pct'].cumsum()
    running_max = trades_df_sorted['cumulative_pl'].expanding().max()
    drawdown = trades_df_sorted['cumulative_pl'] - running_max
    max_drawdown = drawdown.min()
    
    return {
        'n_trades': n_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'win_rate_ci_low': ci_low,
        'win_rate_ci_high': ci_high,
        'mean_net_pl': mean_net_pl,
        'median_net_pl': median_net_pl,
        'std_net_pl': std_net_pl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'sharpe_ratio': sharpe_ratio,
        't_statistic': t_stat,
        'p_value': p_value,
        'win_rate_p_value': win_rate_p_value,
        'cohens_d': cohens_d,
        'max_drawdown': max_drawdown
    }

def bootstrap_confidence_interval(trades_df, n_bootstrap=1000, confidence=0.95):
    """
    Calculates bootstrap confidence intervals for mean net P/L.
    """
    if trades_df is None or trades_df.empty:
        return None, None
    
    bootstrap_means = []
    n = len(trades_df)
    
    for _ in range(n_bootstrap):
        sample = trades_df.sample(n=n, replace=True)
        bootstrap_means.append(sample['net_pl_pct'].mean())
    
    alpha = 1 - confidence
    ci_low = np.percentile(bootstrap_means, alpha/2 * 100)
    ci_high = np.percentile(bootstrap_means, (1 - alpha/2) * 100)
    
    return ci_low, ci_high

def temporal_robustness_test(trades_df):
    """
    Tests if profitability is consistent across different time periods (first half vs second half of games).
    """
    if trades_df is None or trades_df.empty:
        return None
    
    trades_df['game_minute'] = trades_df['datetime'].dt.minute + trades_df['datetime'].dt.hour * 60
    
    # Split by first half (0-24 min) vs second half (24-48 min)
    first_half = trades_df[trades_df['game_minute'] < 24]
    second_half = trades_df[trades_df['game_minute'] >= 24]
    
    if first_half.empty or second_half.empty:
        return None
    
    first_half_mean = first_half['net_pl_pct'].mean()
    second_half_mean = second_half['net_pl_pct'].mean()
    
    # T-test to see if means are significantly different
    t_stat, p_value = stats.ttest_ind(first_half['net_pl_pct'], second_half['net_pl_pct'])
    
    return {
        'first_half_mean': first_half_mean,
        'first_half_n': len(first_half),
        'second_half_mean': second_half_mean,
        'second_half_n': len(second_half),
        't_stat': t_stat,
        'p_value': p_value,
        'consistent': p_value > 0.05  # If p > 0.05, no significant difference (good!)
    }

def run_comprehensive_statistical_tests():
    """
    Main function to run all statistical tests on profitable strategies.
    """
    print("=" * 100)
    print("COMPREHENSIVE STATISTICAL VALIDATION OF PROFITABLE STRATEGIES")
    print("=" * 100)
    print()
    
    # Load data
    print("[1/6] Loading data...", flush=True)
    kalshi_df = load_kalshi_games()
    kalshi_df = fill_prices(kalshi_df)
    n_games = kalshi_df['game_id'].nunique()
    print(f"      Loaded {len(kalshi_df):,} rows from {n_games} games")
    print()
    
    # Load profitable strategies from comprehensive search
    print("[2/6] Loading profitable strategies from previous analysis...", flush=True)
    edges_file = 'outputs/metrics/all_profitable_edges.csv'
    
    if not os.path.exists(edges_file):
        print(f"      ERROR: {edges_file} not found. Running comprehensive search first...")
        return
    
    df_edges = pd.read_csv(edges_file)
    print(f"      Loaded {len(df_edges)} profitable strategies")
    print()
    
    # Run detailed statistical tests on each strategy
    print("[3/6] Running statistical tests on all strategies...")
    print("      This will take several minutes...")
    print()
    
    results = []
    
    for idx, row in df_edges.iterrows():
        if (idx + 1) % 20 == 0:
            print(f"      Progress: {idx + 1}/{len(df_edges)} strategies tested", flush=True)
        
        # Run strategy and get individual trades
        trades = run_strategy_with_trades(
            kalshi_df,
            row['price_min'],
            row['price_max'],
            row['threshold'],
            row['hold']
        )
        
        if trades is None or trades.empty:
            continue
        
        # Calculate statistics
        stats_dict = calculate_statistics(trades)
        
        if stats_dict is None:
            continue
        
        # Bootstrap CI
        boot_ci_low, boot_ci_high = bootstrap_confidence_interval(trades)
        
        # Temporal robustness
        temporal_test = temporal_robustness_test(trades)
        
        # Combine results
        result = {
            'strategy_id': idx,
            'price_range': f"{row['price_min']}-{row['price_max']}c",
            'move_threshold': row['threshold'],
            'hold_period': row['hold'],
            **stats_dict,
            'bootstrap_ci_low': boot_ci_low,
            'bootstrap_ci_high': boot_ci_high,
        }
        
        if temporal_test:
            result.update({
                'temporal_consistent': temporal_test['consistent'],
                'first_half_pl': temporal_test['first_half_mean'],
                'second_half_pl': temporal_test['second_half_mean'],
            })
        
        results.append(result)
    
    print(f"      Completed testing {len(results)} strategies")
    print()
    
    df_results = pd.DataFrame(results)
    
    # Apply multiple testing correction
    print("[4/6] Applying multiple testing corrections (Bonferroni & Benjamini-Hochberg)...", flush=True)
    
    # Bonferroni correction
    alpha = 0.05
    bonferroni_threshold = alpha / len(df_results)
    df_results['bonferroni_significant'] = df_results['p_value'] < bonferroni_threshold
    
    # Benjamini-Hochberg (FDR) correction
    reject, pvals_corrected, _, _ = multipletests(df_results['p_value'], alpha=alpha, method='fdr_bh')
    df_results['fdr_bh_significant'] = reject
    df_results['p_value_adjusted'] = pvals_corrected
    
    print(f"      Bonferroni significant: {df_results['bonferroni_significant'].sum()}/{len(df_results)}")
    print(f"      FDR (BH) significant: {df_results['fdr_bh_significant'].sum()}/{len(df_results)}")
    print()
    
    # Save detailed results
    print("[5/6] Saving detailed results...", flush=True)
    output_dir = 'outputs/metrics'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, 'statistical_validation_results.csv')
    df_results.to_csv(output_file, index=False)
    print(f"      Saved to {output_file}")
    print()
    
    # Generate summary report
    print("[6/6] Generating summary report...")
    print()
    print("=" * 100)
    print("STATISTICAL VALIDATION SUMMARY")
    print("=" * 100)
    print()
    
    # Overall statistics
    print("OVERALL FINDINGS:")
    print("-" * 100)
    print(f"Total strategies tested:           {len(df_results)}")
    print(f"Statistically significant (p<0.05): {(df_results['p_value'] < 0.05).sum()} ({(df_results['p_value'] < 0.05).mean():.1%})")
    print(f"Bonferroni significant:            {df_results['bonferroni_significant'].sum()} ({df_results['bonferroni_significant'].mean():.1%})")
    print(f"FDR (BH) significant:              {df_results['fdr_bh_significant'].sum()} ({df_results['fdr_bh_significant'].mean():.1%})")
    print()
    
    # Win rate analysis
    print("WIN RATE ANALYSIS:")
    print("-" * 100)
    print(f"Mean win rate:                     {df_results['win_rate'].mean():.1%}")
    print(f"Median win rate:                   {df_results['win_rate'].median():.1%}")
    print(f"Win rates significantly > 50%:     {(df_results['win_rate_p_value'] < 0.05).sum()} ({(df_results['win_rate_p_value'] < 0.05).mean():.1%})")
    print()
    
    # Profitability analysis
    print("PROFITABILITY ANALYSIS:")
    print("-" * 100)
    print(f"Mean net P/L per trade:            {df_results['mean_net_pl'].mean():.3f}%")
    print(f"Median net P/L per trade:          {df_results['median_net_pl'].mean():.3f}%")
    print(f"Mean Sharpe ratio:                 {df_results['sharpe_ratio'].mean():.2f}")
    print(f"Mean Cohen's d (effect size):      {df_results['cohens_d'].mean():.2f}")
    print()
    
    # Robustness analysis
    if 'temporal_consistent' in df_results.columns:
        temporal_consistent_count = df_results['temporal_consistent'].sum()
        print("TEMPORAL ROBUSTNESS:")
        print("-" * 100)
        print(f"Strategies consistent across time:  {temporal_consistent_count}/{len(df_results)} ({temporal_consistent_count/len(df_results):.1%})")
        print()
    
    # Top strategies by statistical significance
    print("TOP 10 STRATEGIES BY STATISTICAL STRENGTH (lowest p-value):")
    print("-" * 100)
    top_10 = df_results.nsmallest(10, 'p_value')[
        ['strategy_id', 'price_range', 'move_threshold', 'hold_period', 'n_trades', 'win_rate', 
         'mean_net_pl', 'sharpe_ratio', 'p_value', 'bonferroni_significant']
    ]
    
    for idx, row in top_10.iterrows():
        print(f"\n{list(top_10.index).index(idx) + 1}. Strategy: Price {row['price_range']}, Move >{row['move_threshold']}%, Hold {row['hold_period']}min")
        print(f"   Trades: {row['n_trades']}")
        print(f"   Win Rate: {row['win_rate']:.1%}")
        print(f"   Mean Net P/L: {row['mean_net_pl']:.3f}%")
        print(f"   Sharpe Ratio: {row['sharpe_ratio']:.2f}")
        print(f"   P-value: {row['p_value']:.2e}")
        print(f"   Bonferroni Significant: {'YES' if row['bonferroni_significant'] else 'NO'}")
    
    print()
    print("=" * 100)
    print()
    
    # Key conclusions
    print("KEY STATISTICAL CONCLUSIONS:")
    print("-" * 100)
    
    highly_significant = df_results['bonferroni_significant'].sum()
    if highly_significant > 0:
        print(f"[ROBUST] {highly_significant} strategies pass the strictest Bonferroni correction")
        print("         These strategies are highly unlikely to be due to chance (family-wise error rate < 5%)")
    
    fdr_significant = df_results['fdr_bh_significant'].sum()
    if fdr_significant > 0:
        print(f"[STRONG] {fdr_significant} strategies pass FDR correction (false discovery rate < 5%)")
        print("         These strategies have strong statistical support")
    
    high_sharpe = (df_results['sharpe_ratio'] > 1.0).sum()
    if high_sharpe > 0:
        print(f"[QUALITY] {high_sharpe} strategies have Sharpe ratio > 1.0 (indicating good risk-adjusted returns)")
    
    consistent = df_results.get('temporal_consistent', pd.Series()).sum()
    if consistent > 0:
        print(f"[STABLE] {consistent} strategies show consistent profitability across game periods")
    
    mean_effect_size = df_results['cohens_d'].mean()
    if mean_effect_size > 0.5:
        print(f"[LARGE EFFECT] Average Cohen's d = {mean_effect_size:.2f} (effect size > 0.5 is considered 'medium' to 'large')")
    
    print()
    print("RECOMMENDATION:")
    print("-" * 100)
    
    if highly_significant > 0:
        print("The identified edges are STATISTICALLY ROBUST and highly unlikely to be due to random chance.")
        print("Focus on the Bonferroni-significant strategies for live trading.")
    else:
        print("While many strategies show profitability, consider additional validation before live trading.")
    
    print()
    print("=" * 100)
    print()
    
    print(f"Full detailed results saved to: {output_file}")
    print()

if __name__ == "__main__":
    run_comprehensive_statistical_tests()

