"""
LIVE TRADING SIMULATOR - MAIN RUNNER
=====================================

Simulates live trading on NBA games, generates buy/sell signals,
tracks P/L, and creates visualizations.

This simulates what the live system will do, but using historical data.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# Add trading_engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trading_engine'))

from game_simulator import GameSimulator
from visualization.trade_visualizer import plot_game_trading, plot_multi_game_summary


def run_live_trading_simulation(n_games: int = 5):
    """
    Run complete live trading simulation.
    
    Args:
        n_games: Number of random games to simulate
    """
    print("\n" + "="*100)
    print(" "*35 + "LIVE TRADING SIMULATOR")
    print("="*100)
    print("\nThis simulates live trading during NBA games using your validated strategies.")
    print("It watches for price movements, generates buy/sell signals, and tracks P/L.\n")
    
    # Step 1: Load data
    print("[Step 1/5] Loading Kalshi market data...")
    from src.data.loader import load_kalshi_games
    from src.data.preprocessor import fill_prices
    
    kalshi_df = load_kalshi_games()
    kalshi_df = fill_prices(kalshi_df)
    
    if not pd.api.types.is_datetime64_any_dtype(kalshi_df['datetime']):
        kalshi_df['datetime'] = pd.to_datetime(kalshi_df['datetime'])
    
    print(f"           Loaded {len(kalshi_df):,} price observations from {kalshi_df['game_id'].nunique()} games")
    
    # Step 2: Load strategies
    print("\n[Step 2/5] Loading validated profitable strategies...")
    from signals.signal_generator import load_validated_strategies
    
    strategies = load_validated_strategies()
    top_strategies = sorted(strategies, key=lambda x: x.sharpe_ratio, reverse=True)[:5]
    
    print(f"           Using top 5 strategies by Sharpe ratio:")
    for i, s in enumerate(top_strategies, 1):
        print(f"           {i}. {s.name} - Sharpe: {s.sharpe_ratio:.2f}, Expected P/L: {s.expected_pl:.2f}%")
    
    # Step 3: Select random games (filter to games with actual data)
    print(f"\n[Step 3/5] Selecting {n_games} random games to simulate...")
    
    # Get games with sufficient data (at least 30 minutes of price data)
    game_lengths = kalshi_df.groupby('game_id').size()
    valid_games = game_lengths[game_lengths >= 30].index.tolist()
    
    if len(valid_games) < n_games:
        print(f"           Warning: Only {len(valid_games)} games have sufficient data")
        n_games = len(valid_games)
    
    selected_games = np.random.choice(valid_games, size=min(n_games, len(valid_games)), replace=False)
    selected_games = [str(g) for g in selected_games]  # Convert to strings
    print(f"           Selected games: {', '.join(selected_games)}")
    
    # Step 4: Run simulations
    print(f"\n[Step 4/5] Running live trading simulations...")
    print("           (This simulates minute-by-minute trading as if watching live)\n")
    
    results = []
    
    for idx, game_id in enumerate(selected_games, 1):
        print(f"\n{'='*100}")
        print(f"GAME {idx}/{len(selected_games)}: {game_id}")
        print(f"{'='*100}")
        
        # Create new simulator for each game
        simulator = GameSimulator(strategies_to_use=5, position_size=100)
        
        # Simulate the game
        result = simulator.simulate_game(kalshi_df, game_id)
        results.append(result)
        
        # Create individual game visualization
        print(f"\nGenerating visualization for game {game_id}...")
        fig = plot_game_trading(
            result,
            save_path=f'trading_engine/outputs/game_{game_id}_trading.png'
        )
        plt.close(fig)
    
    # Step 5: Aggregate results and create summary
    print(f"\n{'='*100}")
    print(f"[Step 5/5] Generating aggregate summary across all {len(results)} games...")
    print(f"{'='*100}\n")
    
    # Aggregate statistics
    total_trades = sum(r['performance']['total_trades'] for r in results)
    total_wins = sum(r['performance']['wins'] for r in results)
    total_pl = sum(r['performance']['total_pl_dollars'] for r in results)
    total_fees = sum(r['performance']['total_fees'] for r in results)
    
    if total_trades == 0:
        print("\n[WARNING] No trades were generated!")
        print("   This can happen if:")
        print("   1. Selected games didn't have price movements meeting strategy thresholds")
        print("   2. Prices stayed outside the target ranges (1-20c or 80-99c)")
        print("\n   Try running again with different random games, or increase n_games.")
        return results
    
    print("AGGREGATE RESULTS:")
    print("-"*100)
    print(f"Total Games Simulated:     {len(results)}")
    print(f"Total Trades Executed:     {total_trades}")
    print(f"Total Wins:                {total_wins} ({total_wins/total_trades:.1%} win rate)")
    print(f"Total Losses:              {total_trades - total_wins}")
    print(f"\nTotal Gross P/L:           ${total_pl:+.2f}")
    print(f"Total Fees Paid:           ${total_fees:.2f}")
    print(f"Net P/L:                   ${total_pl:+.2f}")
    print(f"Avg P/L per Game:          ${total_pl/len(results):+.2f}")
    print(f"Avg P/L per Trade:         ${total_pl/total_trades:+.2f}")
    
    # Create multi-game summary visualization
    print(f"\nGenerating multi-game summary visualization...")
    fig = plot_multi_game_summary(
        results,
        save_path='trading_engine/outputs/multi_game_summary.png'
    )
    plt.close(fig)
    
    # Save detailed results to CSV
    print(f"\nSaving detailed results...")
    all_positions = pd.concat([r['positions'] for r in results if not r['positions'].empty])
    all_positions.to_csv('trading_engine/outputs/all_trades.csv', index=False)
    print(f"           Saved all trades to: trading_engine/outputs/all_trades.csv")
    
    # Print file locations
    print(f"\n{'='*100}")
    print("OUTPUT FILES CREATED:")
    print("-"*100)
    for i, game_id in enumerate(selected_games, 1):
        print(f"  {i}. trading_engine/outputs/game_{game_id}_trading.png")
    print(f"  {len(selected_games)+1}. trading_engine/outputs/multi_game_summary.png")
    print(f"  {len(selected_games)+2}. trading_engine/outputs/all_trades.csv")
    print(f"{'='*100}\n")
    
    print("✓ SIMULATION COMPLETE!")
    print("\nYou can now:")
    print("  1. View the individual game charts to see buy/sell signals")
    print("  2. Check the multi-game summary for overall performance")
    print("  3. Open all_trades.csv in Excel for detailed trade-by-trade analysis")
    print("\nThis is what the live system will do in real-time during actual games!")
    print()
    
    return results


if __name__ == "__main__":
    # Run simulation on 5 random games (increased from 3 for better chance of finding trades)
    results = run_live_trading_simulation(n_games=5)

