"""
DEMO MODE - Live Trading Simulator with Relaxed Criteria
=========================================================

This version uses more relaxed strategy criteria to ensure trades are generated
for demonstration purposes.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trading_engine'))

from game_simulator import GameSimulator
from visualization.trade_visualizer import plot_game_trading, plot_multi_game_summary
from signals.signal_generator import Strategy


def create_demo_strategies():
    """Create strategies with RELAXED criteria for demonstration"""
    return [
        # Very lenient strategies to ensure we get trades
        Strategy(
            name="Demo: 1-20¢ Move>5% Hold 3min",
            price_min=1,
            price_max=20,
            move_threshold=5.0,  # Only 5% move needed
            hold_period=3,
            expected_pl=8.0,
            sharpe_ratio=1.5,
            win_rate=0.45
        ),
        Strategy(
            name="Demo: 1-30¢ Move>7% Hold 5min",
            price_min=1,
            price_max=30,
            move_threshold=7.0,
            hold_period=5,
            expected_pl=7.0,
            sharpe_ratio=1.3,
            win_rate=0.43
        ),
        Strategy(
            name="Demo: 10-40¢ Move>8% Hold 3min",
            price_min=10,
            price_max=40,
            move_threshold=8.0,
            hold_period=3,
            expected_pl=6.0,
            sharpe_ratio=1.2,
            win_rate=0.42
        ),
        Strategy(
            name="Demo: 20-50¢ Move>10% Hold 5min",
            price_min=20,
            price_max=50,
            move_threshold=10.0,
            hold_period=5,
            expected_pl=5.5,
            sharpe_ratio=1.1,
            win_rate=0.41
        ),
        Strategy(
            name="Demo: 80-99¢ Move>5% Hold 3min",
            price_min=80,
            price_max=99,
            move_threshold=5.0,
            hold_period=3,
            expected_pl=7.5,
            sharpe_ratio=1.4,
            win_rate=0.44
        ),
    ]


def run_demo_simulation(n_games: int = 3):
    """
    Run demo simulation with relaxed criteria to show how system works.
    """
    print("\n" + "="*100)
    print(" "*30 + "LIVE TRADING SIMULATOR - DEMO MODE")
    print("="*100)
    print("\n🎮 Demo Mode: Using RELAXED strategy criteria to demonstrate functionality")
    print("   (Real trading would use the validated strategies from backtest results)\n")
    
    # Load data
    print("[1/5] Loading Kalshi market data...")
    from src.data.loader import load_kalshi_games
    from src.data.preprocessor import fill_prices
    
    kalshi_df = load_kalshi_games()
    kalshi_df = fill_prices(kalshi_df)
    
    if not pd.api.types.is_datetime64_any_dtype(kalshi_df['datetime']):
        kalshi_df['datetime'] = pd.to_datetime(kalshi_df['datetime'])
    
    print(f"      Loaded {len(kalshi_df):,} observations from {kalshi_df['game_id'].nunique()} games")
    
    # Get games with good volatility (price changes)
    print(f"\n[2/5] Finding games with good price volatility...")
    kalshi_df['price_change'] = kalshi_df.groupby('game_id')['close'].diff()
    kalshi_df['abs_change'] = kalshi_df['price_change'].abs()
    
    # Find games with most volatility
    game_volatility = kalshi_df.groupby('game_id')['abs_change'].mean().sort_values(ascending=False)
    volatile_games = game_volatility.head(20).index.tolist()
    
    selected_games = np.random.choice(volatile_games, size=min(n_games, len(volatile_games)), replace=False)
    selected_games = [str(g) for g in selected_games]
    
    print(f"      Selected {len(selected_games)} games with high price volatility")
    print(f"      Games: {', '.join(selected_games)}")
    
    # Create demo strategies
    print(f"\n[3/5] Loading DEMO strategies (relaxed criteria)...")
    demo_strategies = create_demo_strategies()
    
    for i, s in enumerate(demo_strategies, 1):
        print(f"      {i}. {s.name}")
    
    # Run simulations
    print(f"\n[4/5] Running live trading simulations...\n")
    
    results = []
    
    for idx, game_id in enumerate(selected_games, 1):
        print(f"\n{'='*100}")
        print(f"GAME {idx}/{len(selected_games)}: {game_id}")
        print(f"{'='*100}")
        
        # Create simulator with demo strategies
        simulator = GameSimulator(strategies_to_use=5, position_size=100)
        simulator.strategies = demo_strategies  # Override with demo strategies
        simulator.signal_generator.strategies = demo_strategies
        
        # Simulate
        result = simulator.simulate_game(kalshi_df, game_id)
        results.append(result)
        
        # Create visualization
        if result['performance']['total_trades'] > 0:
            print(f"\n✓ Creating visualization with {result['performance']['total_trades']} trades...")
            fig = plot_game_trading(
                result,
                save_path=f'trading_engine/outputs/demo_game_{game_id}.png'
            )
            plt.close(fig)
        else:
            print(f"\n⚠ No trades generated for this game")
    
    # Aggregate results
    print(f"\n{'='*100}")
    print(f"[5/5] Generating aggregate summary...")
    print(f"{'='*100}\n")
    
    total_trades = sum(r['performance']['total_trades'] for r in results)
    
    if total_trades == 0:
        print("❌ No trades were generated even with relaxed criteria.")
        print("   This suggests the selected games didn't have the expected price patterns.")
        print("\n💡 Try running again - it will select different games.")
        return results
    
    total_wins = sum(r['performance']['wins'] for r in results)
    total_pl = sum(r['performance']['total_pl_dollars'] for r in results)
    total_fees = sum(r['performance']['total_fees'] for r in results)
    
    print("DEMO RESULTS:")
    print("-"*100)
    print(f"Games Simulated:      {len(results)}")
    print(f"Total Trades:         {total_trades}")
    print(f"Wins:                 {total_wins} ({total_wins/total_trades:.1%})")
    print(f"Losses:               {total_trades - total_wins}")
    print(f"Total P/L:            ${total_pl:+.2f}")
    print(f"Total Fees:           ${total_fees:.2f}")
    print(f"Avg P/L per Trade:    ${total_pl/total_trades:+.2f}")
    
    # Create multi-game summary
    if total_trades > 0:
        print(f"\n✓ Creating multi-game summary visualization...")
        fig = plot_multi_game_summary(
            results,
            save_path='trading_engine/outputs/demo_multi_game_summary.png'
        )
        plt.close(fig)
        
        # Save trades
        all_positions = pd.concat([r['positions'] for r in results if not r['positions'].empty])
        all_positions.to_csv('trading_engine/outputs/demo_all_trades.csv', index=False)
    
    # Print files
    print(f"\n{'='*100}")
    print("OUTPUT FILES CREATED:")
    print("-"*100)
    file_count = 0
    for game_id in selected_games:
        filepath = f'trading_engine/outputs/demo_game_{game_id}.png'
        if os.path.exists(filepath):
            file_count += 1
            print(f"  {file_count}. {filepath}")
    
    if os.path.exists('trading_engine/outputs/demo_multi_game_summary.png'):
        file_count += 1
        print(f"  {file_count}. trading_engine/outputs/demo_multi_game_summary.png")
    
    if os.path.exists('trading_engine/outputs/demo_all_trades.csv'):
        file_count += 1
        print(f"  {file_count}. trading_engine/outputs/demo_all_trades.csv")
    
    print(f"{'='*100}\n")
    
    if file_count > 0:
        print("✅ SUCCESS! Charts generated with trading signals")
        print("\n📊 Open the PNG files to see:")
        print("   • Price movements over time")
        print("   • Green ▲ = BUY signals")
        print("   • Red ▼ = SELL signals")
        print("   • Lines connecting trades (green=profit, red=loss)")
        print("   • Cumulative P/L graph")
    
    print()
    return results


if __name__ == "__main__":
    results = run_demo_simulation(n_games=3)

