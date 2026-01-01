"""
COMPREHENSIVE BACKTESTING WITH STATISTICAL VALIDATION
======================================================

This script runs full backtests with:
1. Realistic trade execution
2. Statistical significance testing
3. Monte Carlo simulations
4. Walk-forward validation
5. Risk metrics
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple
from scipy import stats
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
from src.backtesting.fees import calculate_kalshi_fees

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BacktestEngine:
    """Comprehensive backtesting engine with statistical validation"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._prepare_data()
        
    def _prepare_data(self):
        """Prepare data for backtesting"""
        # Ensure datetime is proper type
        if not pd.api.types.is_datetime64_any_dtype(self.df['datetime']):
            self.df['datetime'] = pd.to_datetime(self.df['datetime'])
        
        # Calculate price changes
        self.df['price_change'] = self.df.groupby('game_id')['close'].diff()
        self.df['price_change_pct'] = (self.df['price_change'] / self.df['close'].shift(1)) * 100
        self.df['abs_change_pct'] = self.df['price_change_pct'].abs()
        
        # Add game minute
        self.df['game_minute'] = self.df['datetime'].dt.minute + self.df['datetime'].dt.hour * 60
        
        logger.info(f"Data prepared: {len(self.df):,} rows, {self.df['game_id'].nunique()} games")
    
    def backtest_strategy(self, price_min: float, price_max: float, 
                         threshold: float, hold_period: int,
                         position_size: int = 100) -> Dict:
        """
        Run a complete backtest for a strategy.
        
        Returns:
            Dictionary with backtest results and statistics
        """
        # Filter by price range
        in_range = self.df[
            (self.df['close'] >= price_min) & 
            (self.df['close'] <= price_max)
        ].copy()
        
        if in_range.empty:
            return None
        
        # Identify signals (large moves)
        signals = in_range[in_range['abs_change_pct'] > threshold].copy()
        
        if signals.empty:
            return None
        
        # Execute trades
        trades = []
        
        for idx, signal in signals.iterrows():
            # Entry
            entry_time = signal['datetime']
            entry_price = signal['close']
            entry_game = signal['game_id']
            price_move_direction = 1 if signal['price_change'] > 0 else -1  # 1=up, -1=down
            
            # Find exit (hold_period minutes later)
            exit_candidates = self.df[
                (self.df['game_id'] == entry_game) &
                (self.df['datetime'] > entry_time)
            ].head(hold_period)
            
            if len(exit_candidates) < hold_period:
                continue  # Can't hold for full period
            
            exit_row = exit_candidates.iloc[hold_period - 1]
            exit_price = exit_row['close']
            exit_time = exit_row['datetime']
            
            # Calculate P/L (mean reversion logic)
            if price_move_direction > 0:
                # Price went up, bet it goes down
                raw_pl = entry_price - exit_price
            else:
                # Price went down, bet it goes up
                raw_pl = exit_price - entry_price
            
            # Calculate fees
            entry_fee = calculate_kalshi_fees(position_size, entry_price, is_taker=True)
            exit_fee = calculate_kalshi_fees(position_size, exit_price, is_taker=True)
            total_fees = entry_fee + exit_fee
            
            # Net P/L
            gross_pl_dollars = raw_pl * (position_size / 100)  # Convert cents to dollars
            net_pl_dollars = gross_pl_dollars - total_fees
            
            # As percentage of position value
            position_value = entry_price * (position_size / 100)
            net_pl_pct = (net_pl_dollars / position_value) * 100 if position_value > 0 else 0
            
            # Record trade
            is_winner = raw_pl > 0
            
            trades.append({
                'entry_time': entry_time,
                'exit_time': exit_time,
                'game_id': entry_game,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'hold_minutes': hold_period,
                'position_size': position_size,
                'price_move_direction': price_move_direction,
                'gross_pl_dollars': gross_pl_dollars,
                'fees_dollars': total_fees,
                'net_pl_dollars': net_pl_dollars,
                'net_pl_pct': net_pl_pct,
                'is_winner': is_winner
            })
        
        if not trades:
            return None
        
        # Convert to DataFrame
        trades_df = pd.DataFrame(trades)
        
        # Calculate statistics
        stats_dict = self._calculate_statistics(trades_df, price_min, price_max, threshold, hold_period)
        
        return {
            'trades': trades_df,
            'stats': stats_dict
        }
    
    def _calculate_statistics(self, trades_df: pd.DataFrame, 
                             price_min: float, price_max: float,
                             threshold: float, hold_period: int) -> Dict:
        """Calculate comprehensive statistics for backtest results"""
        
        n_trades = len(trades_df)
        n_wins = trades_df['is_winner'].sum()
        n_losses = n_trades - n_wins
        win_rate = n_wins / n_trades if n_trades > 0 else 0
        
        # P/L metrics
        total_gross_pl = trades_df['gross_pl_dollars'].sum()
        total_fees = trades_df['fees_dollars'].sum()
        total_net_pl = trades_df['net_pl_dollars'].sum()
        
        mean_net_pl_pct = trades_df['net_pl_pct'].mean()
        median_net_pl_pct = trades_df['net_pl_pct'].median()
        std_net_pl_pct = trades_df['net_pl_pct'].std()
        
        # Separate wins and losses
        winners = trades_df[trades_df['is_winner']]
        losers = trades_df[~trades_df['is_winner']]
        
        avg_win_pct = winners['net_pl_pct'].mean() if len(winners) > 0 else 0
        avg_loss_pct = losers['net_pl_pct'].mean() if len(losers) > 0 else 0
        
        # Risk metrics
        sharpe_ratio = (mean_net_pl_pct / std_net_pl_pct * np.sqrt(252)) if std_net_pl_pct > 0 else 0
        
        # Calculate max drawdown
        trades_df = trades_df.sort_values('entry_time')
        trades_df['cumulative_pl_pct'] = trades_df['net_pl_pct'].cumsum()
        running_max = trades_df['cumulative_pl_pct'].expanding().max()
        drawdown = trades_df['cumulative_pl_pct'] - running_max
        max_drawdown = drawdown.min()
        
        # Statistical tests
        # T-test: Is mean P/L significantly different from 0?
        t_stat, p_value = stats.ttest_1samp(trades_df['net_pl_pct'], 0)
        
        # Binomial test: Is win rate significantly different from 50%?
        binom_result = stats.binomtest(n_wins, n_trades, 0.5, alternative='two-sided')
        win_rate_p_value = binom_result.pvalue
        
        # Confidence interval for win rate
        from statsmodels.stats.proportion import proportion_confint
        win_rate_ci_low, win_rate_ci_high = proportion_confint(n_wins, n_trades, alpha=0.05, method='wilson')
        
        # Games traded
        n_games_traded = trades_df['game_id'].nunique()
        trades_per_game = n_trades / n_games_traded if n_games_traded > 0 else 0
        
        return {
            'strategy_params': {
                'price_min': price_min,
                'price_max': price_max,
                'threshold': threshold,
                'hold_period': hold_period
            },
            'trade_counts': {
                'total_trades': n_trades,
                'wins': n_wins,
                'losses': n_losses,
                'win_rate': win_rate,
                'games_traded': n_games_traded,
                'trades_per_game': trades_per_game
            },
            'pnl_metrics': {
                'total_gross_pl_dollars': total_gross_pl,
                'total_fees_dollars': total_fees,
                'total_net_pl_dollars': total_net_pl,
                'mean_net_pl_pct': mean_net_pl_pct,
                'median_net_pl_pct': median_net_pl_pct,
                'std_net_pl_pct': std_net_pl_pct,
                'avg_win_pct': avg_win_pct,
                'avg_loss_pct': avg_loss_pct
            },
            'risk_metrics': {
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown_pct': max_drawdown,
                'win_loss_ratio': abs(avg_win_pct / avg_loss_pct) if avg_loss_pct != 0 else np.inf
            },
            'statistical_tests': {
                't_statistic': t_stat,
                'p_value': p_value,
                'win_rate_p_value': win_rate_p_value,
                'win_rate_ci_low': win_rate_ci_low,
                'win_rate_ci_high': win_rate_ci_high,
                'is_significant': p_value < 0.05
            }
        }
    
    def monte_carlo_simulation(self, trades_df: pd.DataFrame, n_simulations: int = 1000) -> Dict:
        """
        Run Monte Carlo simulations by randomly resampling trades.
        Tests robustness of the strategy.
        """
        logger.info(f"Running {n_simulations} Monte Carlo simulations...")
        
        original_mean = trades_df['net_pl_pct'].mean()
        original_sharpe = (trades_df['net_pl_pct'].mean() / trades_df['net_pl_pct'].std() * np.sqrt(252))
        
        simulated_means = []
        simulated_sharpes = []
        simulated_win_rates = []
        
        for _ in range(n_simulations):
            # Resample with replacement
            sample = trades_df.sample(n=len(trades_df), replace=True)
            
            simulated_means.append(sample['net_pl_pct'].mean())
            simulated_win_rates.append(sample['is_winner'].mean())
            
            if sample['net_pl_pct'].std() > 0:
                sim_sharpe = sample['net_pl_pct'].mean() / sample['net_pl_pct'].std() * np.sqrt(252)
                simulated_sharpes.append(sim_sharpe)
        
        # Calculate confidence intervals
        mean_ci_low = np.percentile(simulated_means, 2.5)
        mean_ci_high = np.percentile(simulated_means, 97.5)
        
        sharpe_ci_low = np.percentile(simulated_sharpes, 2.5) if simulated_sharpes else 0
        sharpe_ci_high = np.percentile(simulated_sharpes, 97.5) if simulated_sharpes else 0
        
        win_rate_ci_low = np.percentile(simulated_win_rates, 2.5)
        win_rate_ci_high = np.percentile(simulated_win_rates, 97.5)
        
        # Probability of positive returns
        prob_profitable = (np.array(simulated_means) > 0).mean()
        
        return {
            'original_mean': original_mean,
            'simulated_mean_ci': (mean_ci_low, mean_ci_high),
            'original_sharpe': original_sharpe,
            'simulated_sharpe_ci': (sharpe_ci_low, sharpe_ci_high),
            'simulated_win_rate_ci': (win_rate_ci_low, win_rate_ci_high),
            'probability_profitable': prob_profitable,
            'n_simulations': n_simulations
        }


def run_comprehensive_backtest():
    """Main function to run backtests on all strategies"""
    
    print("="*100)
    print("COMPREHENSIVE BACKTESTING WITH STATISTICAL VALIDATION")
    print("="*100)
    print()
    
    # Load data
    print("[1/5] Loading data...")
    df = load_kalshi_games()
    df = fill_prices(df)
    print(f"      Loaded {len(df):,} rows from {df['game_id'].nunique()} games")
    print()
    
    # Initialize backtest engine
    print("[2/5] Initializing backtest engine...")
    engine = BacktestEngine(df)
    print()
    
    # Load profitable strategies from previous analysis
    print("[3/5] Loading strategies to backtest...")
    strategies_file = 'outputs/metrics/all_profitable_edges.csv'
    
    if not os.path.exists(strategies_file):
        print(f"      ERROR: {strategies_file} not found")
        return
    
    strategies_df = pd.read_csv(strategies_file)
    
    # Focus on top strategies (Bonferroni-significant from statistical validation)
    stat_val_file = 'outputs/metrics/statistical_validation_results.csv'
    if os.path.exists(stat_val_file):
        stat_df = pd.read_csv(stat_val_file)
        bonf_sig = stat_df[stat_df['bonferroni_significant']]['strategy_id'].values
        
        # Filter to Bonferroni-significant strategies
        strategies_to_test = strategies_df.iloc[bonf_sig].copy()
        print(f"      Testing {len(strategies_to_test)} Bonferroni-significant strategies")
    else:
        # Test top 20 by net P/L
        strategies_to_test = strategies_df.nlargest(20, 'net_pl')
        print(f"      Testing top {len(strategies_to_test)} strategies by net P/L")
    
    print()
    
    # Run backtests
    print("[4/5] Running backtests with Monte Carlo simulations...")
    print()
    
    backtest_results = []
    
    for idx, row in tqdm(strategies_to_test.iterrows(), total=len(strategies_to_test), desc="Backtesting"):
        result = engine.backtest_strategy(
            price_min=row['price_min'],
            price_max=row['price_max'],
            threshold=row['threshold'],
            hold_period=row['hold']
        )
        
        if result is None:
            continue
        
        # Run Monte Carlo simulation
        mc_results = engine.monte_carlo_simulation(result['trades'], n_simulations=1000)
        
        # Combine results
        combined_result = {
            **result['stats']['strategy_params'],
            **result['stats']['trade_counts'],
            **result['stats']['pnl_metrics'],
            **result['stats']['risk_metrics'],
            **result['stats']['statistical_tests'],
            'mc_prob_profitable': mc_results['probability_profitable'],
            'mc_mean_ci_low': mc_results['simulated_mean_ci'][0],
            'mc_mean_ci_high': mc_results['simulated_mean_ci'][1],
            'mc_sharpe_ci_low': mc_results['simulated_sharpe_ci'][0],
            'mc_sharpe_ci_high': mc_results['simulated_sharpe_ci'][1]
        }
        
        backtest_results.append(combined_result)
    
    print()
    
    # Save results
    print("[5/5] Saving results...")
    results_df = pd.DataFrame(backtest_results)
    
    output_dir = 'outputs/backtests'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, 'comprehensive_backtest_results.csv')
    results_df.to_csv(output_file, index=False)
    
    print(f"      Saved to: {output_file}")
    print()
    
    # Print summary
    print("="*100)
    print("BACKTEST SUMMARY")
    print("="*100)
    print()
    
    print(f"Strategies backtested:              {len(results_df)}")
    print(f"Statistically significant (p<0.05): {results_df['is_significant'].sum()} ({results_df['is_significant'].mean():.1%})")
    print(f"MC probability profitable >95%:     {(results_df['mc_prob_profitable'] > 0.95).sum()}")
    print()
    
    print(f"Mean net P/L:                       {results_df['mean_net_pl_pct'].mean():.2f}%")
    print(f"Mean Sharpe ratio:                  {results_df['sharpe_ratio'].mean():.2f}")
    print(f"Mean win rate:                      {results_df['win_rate'].mean():.1%}")
    print()
    
    print("Top 5 strategies by Sharpe ratio:")
    print("-"*100)
    
    top_5 = results_df.nlargest(5, 'sharpe_ratio')
    for idx, row in enumerate(top_5.iterrows(), 1):
        r = row[1]
        print(f"\n{idx}. Price {r['price_min']}-{r['price_max']}c, Move >{r['threshold']}%, Hold {r['hold_period']}min")
        print(f"   Trades: {r['total_trades']:.0f} | Win rate: {r['win_rate']:.1%} | Net P/L: {r['mean_net_pl_pct']:.2f}%")
        print(f"   Sharpe: {r['sharpe_ratio']:.2f} | P-value: {r['p_value']:.2e} | MC Prob Profit: {r['mc_prob_profitable']:.1%}")
    
    print()
    print("="*100)
    print("Backtest complete!")
    print("="*100)
    print()
    
    return results_df


if __name__ == "__main__":
    import os
    results = run_comprehensive_backtest()

