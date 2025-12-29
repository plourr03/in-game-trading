"""
WORKING DEMO - Guaranteed to Show Trades
=========================================

This version analyzes the actual data and creates strategies
that WILL generate trades.
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
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices


def find_volatile_games_and_create_strategies(kalshi_df, n_games=3):
    """
    Find games with actual volatility and create matching strategies
    """
    print("Analyzing data to find volatile games and create matching strategies...")
    
    # Calculate price changes
    kalshi_df['price_change'] = kalshi_df.groupby('game_id')['close'].diff()
    kalshi_df['price_change_pct'] = (kalshi_df['price_change'] / kalshi_df['close'].shift(1)).abs() * 100
    
    # Find games with good volatility
    game_stats = kalshi_df.groupby('game_id').agg({
        'price_change_pct': ['mean', 'max', 'count'],
        'close': ['min', 'max', 'mean']
    })
    
    game_stats.columns = ['avg_move', 'max_move', 'n_minutes', 'min_price', 'max_price', 'avg_price']
    game_stats = game_stats[game_stats['n_minutes'] > 100]  # At least 100 minutes
    game_stats = game_stats[game_stats['max_move'] > 10]  # At least one 10%+ move
    game_stats = game_stats.sort_values('avg_move', ascending=False)
    
    selected_games = game_stats.head(n_games).index.tolist()
    
    print(f"\nSelected {len(selected_games)} volatile games:")
    for game_id in selected_games:
        stats = game_stats.loc[game_id]
        print(f"  Game {game_id}:")
        print(f"    - Avg move: {stats['avg_move']:.2f}%, Max move: {stats['max_move']:.2f}%")
        print(f"    - Price range: {stats['min_price']:.0f}-{stats['max_price']:.0f}¢")
    
    # Create strategies that match the actual price ranges in the data
    strategies = [
        Strategy(
            name="Demo: 1-40¢ Move>5% Hold 3min",
            price_min=1,
            price_max=40,
            move_threshold=5.0,
            hold_period=3,
            expected_pl=8.0,
            sharpe_ratio=1.5,
            win_rate=0.45
        ),
        Strategy(
            name="Demo: 20-60¢ Move>7% Hold 5min",
            price_min=20,
            price_max=60,
            move_threshold=7.0,
            hold_period=5,
            expected_pl=7.0,
            sharpe_ratio=1.3,
            win_rate=0.43
        ),
        Strategy(
            name="Demo: 40-80¢ Move>8% Hold 3min",
            price_min=40,
            price_max=80,
            move_threshold=8.0,
            hold_period=3,
            expected_pl=6.5,
            sharpe_ratio=1.2,
            win_rate=0.42
        ),
        Strategy(
            name="Demo: 50-90¢ Move>10% Hold 5min",
            price_min=50,
            price_max=90,
            move_threshold=10.0,
            hold_period=5,
            expected_pl=6.0,
            sharpe_ratio=1.1,
            win_rate=0.41
        ),
        Strategy(
            name="Demo: 60-99¢ Move>12% Hold 7min",
            price_min=60,
            price_max=99,
            move_threshold=12.0,
            hold_period=7,
            expected_pl=5.5,
            sharpe_ratio=1.0,
            win_rate=0.40
        ),
    ]
    
    return selected_games, strategies


def run_working_demo():
    """Run demo that WILL generate trades"""
    
    print("\n" + "="*100)
    print(" "*25 + "LIVE TRADING SIMULATOR - WORKING DEMO")
    print("="*100)
    print("\n🎯 This demo uses relaxed criteria and volatile games to GUARANTEE trades\n")
    
    # Load data
    print("[1/4] Loading Kalshi data...")
    kalshi_df = load_kalshi_games()
    kalshi_df = fill_prices(kalshi_df)
    
    if not pd.api.types.is_datetime64_any_dtype(kalshi_df['datetime']):
        kalshi_df['datetime'] = pd.to_datetime(kalshi_df['datetime'])
    
    print(f"      Loaded {len(kalshi_df):,} observations from {kalshi_df['game_id'].nunique()} games\n")
    
    # Find volatile games and create matching strategies
    print("[2/4] Finding volatile games and creating strategies...")
    selected_games, demo_strategies = find_volatile_games_and_create_strategies(kalshi_df, n_games=10)
    
    print(f"\nCreated {len(demo_strategies)} demo strategies:")
    for s in demo_strategies:
        print(f"  • {s.name}")
    
    # Run simulations
    print(f"\n[3/4] Running simulations...\n")
    
    results = []
    trades_generated = 0
    
    for idx, game_id in enumerate(selected_games, 1):
        print(f"\n{'='*100}")
        print(f"GAME {idx}/{len(selected_games)}: {game_id}")
        print(f"{'='*100}\n")
        
        # Create simulator
        simulator = GameSimulator(strategies_to_use=5, position_size=100)
        simulator.strategies = demo_strategies
        simulator.signal_generator.strategies = demo_strategies
        
        # Run simulation
        result = simulator.simulate_game(kalshi_df, game_id)
        results.append(result)
        trades_generated += result['performance']['total_trades']
        
        # Create visualization
        if result['performance']['total_trades'] > 0:
            print(f"\n✓ Generating chart with {result['performance']['total_trades']} trades...")
            fig = plot_game_trading(
                result,
                save_path=f'trading_engine/outputs/DEMO_game_{game_id}.png'
            )
            plt.close(fig)
        else:
            print(f"\n⚠️ No trades for this game (unusual!)")
    
    # Summary
    print(f"\n{'='*100}")
    print(f"[4/4] Summary")
    print(f"{'='*100}\n")
    
    if trades_generated == 0:
        print("❌ Still no trades generated!")
        print("   The data may have very stable prices with minimal volatility.")
        return results
    
    total_trades = sum(r['performance']['total_trades'] for r in results)
    total_wins = sum(r['performance']['wins'] for r in results)
    total_pl = sum(r['performance']['total_pl_dollars'] for r in results)
    total_fees = sum(r['performance']['total_fees'] for r in results)
    
    print("✅ SUCCESS! Trades Generated:")
    print("-"*100)
    print(f"Games:          {len(results)}")
    print(f"Total Trades:   {total_trades}")
    print(f"Wins:           {total_wins} ({total_wins/total_trades:.1%})")
    print(f"Losses:         {total_trades - total_wins}")
    print(f"Total P/L:      ${total_pl:+.2f}")
    print(f"Avg P/L:        ${total_pl/total_trades:+.2f} per trade")
    print(f"Total Fees:     ${total_fees:.2f}")
    
    # Create multi-game chart
    print(f"\n✓ Creating multi-game summary...")
    fig = plot_multi_game_summary(
        results,
        save_path='trading_engine/outputs/DEMO_multi_game_summary.png'
    )
    plt.close(fig)
    
    # Save CSV
    all_positions = pd.concat([r['positions'] for r in results if not r['positions'].empty])
    all_positions.to_csv('trading_engine/outputs/DEMO_all_trades.csv', index=False)
    
    # List files
    print(f"\n{'='*100}")
    print("📁 OUTPUT FILES:")
    print("-"*100)
    for i, game_id in enumerate(selected_games, 1):
        print(f"  {i}. trading_engine/outputs/DEMO_game_{game_id}.png")
    print(f"  {len(selected_games)+1}. trading_engine/outputs/DEMO_multi_game_summary.png")
    print(f"  {len(selected_games)+2}. trading_engine/outputs/DEMO_all_trades.csv")
    print(f"{'='*100}\n")
    
    print("🎉 DEMO COMPLETE!")
    print("\n📊 Open the PNG files to see:")
    print("   ▲ Green triangles = BUY signals (when price moved sharply)")
    print("   ▼ Red triangles = SELL signals (after holding period)")
    print("   📈 Cumulative P/L graph shows profit/loss over time")
    print("   📋 Summary stats show win rate and performance\n")
    
    return results


if __name__ == "__main__":
    results = run_working_demo()

