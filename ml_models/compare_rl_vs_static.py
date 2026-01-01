"""
Compare RL-based exit strategy vs static 5-minute exit strategy.

Backtests both strategies on the same test set and compares performance metrics.
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import pandas as pd
import numpy as np
import joblib
from glob import glob
from tqdm import tqdm
from stable_baselines3 import PPO
from ml_models.rl_data_split import load_split
from ml_models.rl_exit_env import NBAExitEnv
from src.backtesting.fees import calculate_kalshi_fees


def backtest_static_exit(game_file, entry_model, features_list, entry_threshold=0.60, contracts=500):
    """
    Backtest with static 5-minute exit rule.
    
    Args:
        game_file: Path to game CSV file
        entry_model: Trained entry prediction model
        features_list: List of feature names
        entry_threshold: Probability threshold for entry
        contracts: Number of contracts per trade
        
    Returns:
        List of trade dictionaries
    """
    try:
        df = pd.read_csv(game_file)
    except Exception as e:
        print(f"Error loading {game_file}: {e}")
        return []
    
    if len(df) < 15:
        return []
    
    # Create environment to reuse feature calculation
    env = NBAExitEnv([game_file], entry_threshold, contracts)
    trades = []
    
    current_minute = 10  # Start after warmup
    position = None
    
    while current_minute < len(df) - 1:
        env.current_game_df = df
        env.current_minute = current_minute
        
        # If no position, check for entry
        if position is None:
            if env._should_enter():
                entry_price = env._get_current_price()
                position = {
                    'entry_minute': current_minute,
                    'entry_price': entry_price,
                    'contracts': contracts
                }
        
        # If have position, check for exit
        elif position is not None:
            minutes_held = current_minute - position['entry_minute']
            current_price = env._get_current_price()
            
            # Static rule: exit after 5 minutes
            if minutes_held >= 5:
                # Check hold-to-expiration rule
                period = min(4, (current_minute // 12) + 1)
                time_remaining = 48 - current_minute
                
                score_home = df.iloc[current_minute].get('score_home', 0)
                score_away = df.iloc[current_minute].get('score_away', 0)
                score_diff = abs(score_home - score_away)
                
                hold_to_expiration = (
                    period >= 4 and
                    time_remaining <= 6 and
                    current_price >= 95 and
                    score_diff >= 11
                )
                
                if not hold_to_expiration:
                    # Normal exit
                    net_pl = env._calculate_pl(position['entry_price'], current_price, contracts)
                    trades.append({
                        'entry_minute': position['entry_minute'],
                        'exit_minute': current_minute,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'contracts': contracts,
                        'net_pl': net_pl,
                        'minutes_held': minutes_held,
                        'strategy': 'static',
                        'game': os.path.basename(game_file)
                    })
                    position = None
        
        current_minute += 1
    
    # Force exit at game end
    if position is not None:
        net_pl = env._calculate_pl_at_expiration(position['entry_price'], contracts)
        trades.append({
            'entry_minute': position['entry_minute'],
            'exit_minute': len(df) - 1,
            'entry_price': position['entry_price'],
            'exit_price': 100,
            'contracts': contracts,
            'net_pl': net_pl,
            'minutes_held': len(df) - 1 - position['entry_minute'],
            'strategy': 'static',
            'game': os.path.basename(game_file),
            'expiration': True
        })
    
    return trades


def backtest_rl_exit(game_file, rl_model, entry_model, features_list, entry_threshold=0.60, contracts=500):
    """
    Backtest with RL-based exit decisions.
    
    Args:
        game_file: Path to game CSV file
        rl_model: Trained RL agent
        entry_model: Trained entry prediction model
        features_list: List of feature names
        entry_threshold: Probability threshold for entry
        contracts: Number of contracts per trade
        
    Returns:
        List of trade dictionaries
    """
    try:
        df = pd.read_csv(game_file)
    except Exception as e:
        print(f"Error loading {game_file}: {e}")
        return []
    
    if len(df) < 15:
        return []
    
    # Create environment
    env = NBAExitEnv([game_file], entry_threshold, contracts)
    env.current_game_df = df
    env.current_minute = 10
    
    trades = []
    position = None
    
    current_minute = 10
    
    while current_minute < len(df) - 1:
        env.current_minute = current_minute
        
        # If no position, check for entry
        if position is None:
            if env._should_enter():
                entry_price = env._get_current_price()
                position = {
                    'entry_minute': current_minute,
                    'entry_price': entry_price,
                    'contracts': contracts
                }
                env.position = position
        
        # If have position, let RL decide
        elif position is not None:
            env.position = position
            state = env._get_state()
            action, _ = rl_model.predict(state, deterministic=True)
            
            minutes_held = current_minute - position['entry_minute']
            current_price = env._get_current_price()
            
            # Check hold-to-expiration rule first
            period = min(4, (current_minute // 12) + 1)
            time_remaining = 48 - current_minute
            
            score_home = df.iloc[current_minute].get('score_home', 0)
            score_away = df.iloc[current_minute].get('score_away', 0)
            score_diff = abs(score_home - score_away)
            
            hold_to_expiration = (
                period >= 4 and
                time_remaining <= 6 and
                current_price >= 95 and
                score_diff >= 11
            )
            
            # RL decides to exit or forced exit
            if (action == 1 and not hold_to_expiration) or minutes_held >= 30:
                net_pl = env._calculate_pl(position['entry_price'], current_price, contracts)
                trades.append({
                    'entry_minute': position['entry_minute'],
                    'exit_minute': current_minute,
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'contracts': contracts,
                    'net_pl': net_pl,
                    'minutes_held': minutes_held,
                    'strategy': 'rl',
                    'game': os.path.basename(game_file),
                    'rl_action': int(action),
                    'forced': minutes_held >= 30
                })
                position = None
                env.position = None
        
        current_minute += 1
    
    # Force exit at game end
    if position is not None:
        net_pl = env._calculate_pl_at_expiration(position['entry_price'], contracts)
        trades.append({
            'entry_minute': position['entry_minute'],
            'exit_minute': len(df) - 1,
            'entry_price': position['entry_price'],
            'exit_price': 100,
            'contracts': contracts,
            'net_pl': net_pl,
            'minutes_held': len(df) - 1 - position['entry_minute'],
            'strategy': 'rl',
            'game': os.path.basename(game_file),
            'expiration': True
        })
    
    return trades


def calculate_metrics(trades):
    """Calculate performance metrics from trades."""
    if len(trades) == 0:
        return {
            'total_trades': 0,
            'total_pl': 0,
            'avg_pl': 0,
            'win_rate': 0,
            'sharpe': 0,
            'avg_hold_time': 0,
            'max_drawdown': 0
        }
    
    total_pl = sum(t['net_pl'] for t in trades)
    wins = sum(1 for t in trades if t['net_pl'] > 0)
    win_rate = wins / len(trades)
    avg_pl = total_pl / len(trades)
    avg_hold_time = np.mean([t['minutes_held'] for t in trades])
    
    # Calculate Sharpe ratio
    pls = [t['net_pl'] for t in trades]
    if np.std(pls) > 0:
        sharpe = np.mean(pls) / np.std(pls) * np.sqrt(len(pls))
    else:
        sharpe = 0
    
    # Calculate max drawdown
    cumulative_pl = np.cumsum([t['net_pl'] for t in trades])
    running_max = np.maximum.accumulate(cumulative_pl)
    drawdown = running_max - cumulative_pl
    max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
    
    return {
        'total_trades': len(trades),
        'total_pl': total_pl,
        'avg_pl': avg_pl,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'avg_hold_time': avg_hold_time,
        'max_drawdown': max_drawdown
    }


def compare_strategies(test_games, rl_model_path, output_dir='ml_models/outputs'):
    """
    Compare static vs RL exit strategies on test set.
    
    Args:
        test_games: List of test game files
        rl_model_path: Path to trained RL model
        output_dir: Directory to save results
    """
    print("="*80)
    print("COMPARING EXIT STRATEGIES")
    print("="*80)
    
    # Load models
    print("\nLoading models...")
    entry_model = joblib.load('ml_models/outputs/advanced_model.pkl')
    features_list = joblib.load('ml_models/outputs/advanced_features.pkl')
    
    try:
        rl_model = PPO.load(rl_model_path)
        print(f"[OK] RL model loaded from {rl_model_path}")
    except Exception as e:
        print(f"[ERROR] Failed to load RL model: {e}")
        return
    
    print(f"[OK] Entry model loaded ({len(features_list)} features)")
    
    # Run backtests
    print(f"\nBacktesting on {len(test_games)} test games...")
    
    static_trades = []
    rl_trades = []
    
    for game_file in tqdm(test_games, desc="Backtesting"):
        static_trades.extend(backtest_static_exit(game_file, entry_model, features_list))
        rl_trades.extend(backtest_rl_exit(game_file, rl_model, entry_model, features_list))
    
    # Calculate metrics
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    static_metrics = calculate_metrics(static_trades)
    rl_metrics = calculate_metrics(rl_trades)
    
    # Print comparison
    print("\nStatic Exit (5-minute hold):")
    print(f"  Total trades:     {static_metrics['total_trades']}")
    print(f"  Win rate:         {static_metrics['win_rate']:.1%}")
    print(f"  Avg P/L per trade: ${static_metrics['avg_pl']:.2f}")
    print(f"  Total P/L:        ${static_metrics['total_pl']:.2f}")
    print(f"  Sharpe ratio:     {static_metrics['sharpe']:.3f}")
    print(f"  Avg hold time:    {static_metrics['avg_hold_time']:.1f} minutes")
    print(f"  Max drawdown:     ${static_metrics['max_drawdown']:.2f}")
    
    print("\nRL Exit (learned policy):")
    print(f"  Total trades:     {rl_metrics['total_trades']}")
    print(f"  Win rate:         {rl_metrics['win_rate']:.1%}")
    print(f"  Avg P/L per trade: ${rl_metrics['avg_pl']:.2f}")
    print(f"  Total P/L:        ${rl_metrics['total_pl']:.2f}")
    print(f"  Sharpe ratio:     {rl_metrics['sharpe']:.3f}")
    print(f"  Avg hold time:    {rl_metrics['avg_hold_time']:.1f} minutes")
    print(f"  Max drawdown:     ${rl_metrics['max_drawdown']:.2f}")
    
    print("\nImprovement (RL vs Static):")
    pl_improvement = rl_metrics['total_pl'] - static_metrics['total_pl']
    pl_pct = (pl_improvement / abs(static_metrics['total_pl']) * 100) if static_metrics['total_pl'] != 0 else 0
    sharpe_improvement = rl_metrics['sharpe'] - static_metrics['sharpe']
    
    print(f"  Total P/L:        ${pl_improvement:+.2f} ({pl_pct:+.1f}%)")
    print(f"  Sharpe ratio:     {sharpe_improvement:+.3f}")
    print(f"  Win rate:         {(rl_metrics['win_rate'] - static_metrics['win_rate'])*100:+.1f}pp")
    
    # Success criteria
    print("\n" + "="*80)
    print("SUCCESS CRITERIA")
    print("="*80)
    
    pl_success = rl_metrics['total_pl'] > static_metrics['total_pl']
    sharpe_success = rl_metrics['sharpe'] > static_metrics['sharpe']
    
    print(f"  P/L improvement:     {'PASS' if pl_success else 'FAIL'}")
    print(f"  Sharpe improvement:  {'PASS' if sharpe_success else 'FAIL'}")
    
    if pl_success and sharpe_success:
        print("\n  ✓ RL EXIT STRATEGY OUTPERFORMS STATIC EXIT!")
        recommendation = "Deploy RL exit strategy to production"
    else:
        print("\n  ✗ RL exit strategy does not outperform static")
        recommendation = "Continue with static 5-minute exit"
    
    print(f"\nRecommendation: {recommendation}")
    
    # Save results
    results_df = pd.DataFrame({
        'Strategy': ['Static', 'RL'],
        'Total Trades': [static_metrics['total_trades'], rl_metrics['total_trades']],
        'Win Rate': [static_metrics['win_rate'], rl_metrics['win_rate']],
        'Avg P/L': [static_metrics['avg_pl'], rl_metrics['avg_pl']],
        'Total P/L': [static_metrics['total_pl'], rl_metrics['total_pl']],
        'Sharpe Ratio': [static_metrics['sharpe'], rl_metrics['sharpe']],
        'Avg Hold Time': [static_metrics['avg_hold_time'], rl_metrics['avg_hold_time']],
        'Max Drawdown': [static_metrics['max_drawdown'], rl_metrics['max_drawdown']]
    })
    
    results_file = os.path.join(output_dir, 'rl_vs_static_comparison.csv')
    results_df.to_csv(results_file, index=False)
    print(f"\n[OK] Results saved to {results_file}")
    
    # Save trade details
    static_trades_df = pd.DataFrame(static_trades)
    rl_trades_df = pd.DataFrame(rl_trades)
    
    static_trades_file = os.path.join(output_dir, 'static_exit_trades.csv')
    rl_trades_file = os.path.join(output_dir, 'rl_exit_trades.csv')
    
    if len(static_trades) > 0:
        static_trades_df.to_csv(static_trades_file, index=False)
        print(f"[OK] Static trades saved to {static_trades_file}")
    
    if len(rl_trades) > 0:
        rl_trades_df.to_csv(rl_trades_file, index=False)
        print(f"[OK] RL trades saved to {rl_trades_file}")
    
    return {
        'static_metrics': static_metrics,
        'rl_metrics': rl_metrics,
        'static_trades': static_trades,
        'rl_trades': rl_trades,
        'success': pl_success and sharpe_success
    }


if __name__ == "__main__":
    # Load test set
    print("Loading test set...")
    test_games = load_split('test')
    print(f"Test set: {len(test_games)} games")
    
    # Compare strategies
    rl_model_path = 'ml_models/outputs/rl_exit_policy'
    
    if not os.path.exists(rl_model_path + '.zip'):
        print(f"\n[ERROR] RL model not found at {rl_model_path}.zip")
        print("Please train the RL model first:")
        print("  python ml_models/train_rl_exit.py")
    else:
        results = compare_strategies(test_games, rl_model_path)

