"""
Trading Engine - Game Simulator
================================

Simulates live trading during games, generating buy/sell signals
and tracking performance.
"""

import pandas as pd
import numpy as np
from typing import List, Dict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals.signal_generator import SignalGenerator, load_validated_strategies, Signal
from execution.position_manager import PositionManager
from execution.order_executor import OrderExecutor


class GameSimulator:
    """
    Simulates live trading during a game.
    """
    
    def __init__(self, strategies_to_use: int = 5, position_size: int = 100):
        """
        Initialize simulator.
        
        Args:
            strategies_to_use: Number of top strategies to trade
            position_size: Number of contracts per trade
        """
        # Load strategies
        all_strategies = load_validated_strategies()
        self.strategies = sorted(all_strategies, key=lambda x: x.sharpe_ratio, reverse=True)[:strategies_to_use]
        
        # Initialize components
        self.signal_generator = SignalGenerator(self.strategies)
        self.position_manager = PositionManager()
        self.order_executor = OrderExecutor(default_size=position_size)
        
        # Tracking
        self.signals_generated = []
        self.trade_log = []
        
    def simulate_game(self, kalshi_df: pd.DataFrame, game_id: str) -> Dict:
        """
        Simulate trading for a single game.
        
        Args:
            kalshi_df: Full Kalshi DataFrame
            game_id: Game to simulate
            
        Returns:
            Dict with simulation results
        """
        print(f"\n{'='*80}")
        print(f"SIMULATING GAME: {game_id}")
        print(f"{'='*80}\n")
        
        # Get game data
        game_data = kalshi_df[kalshi_df['game_id'] == game_id].copy()
        game_data = game_data.sort_values('datetime').reset_index(drop=True)
        
        # Calculate price changes
        game_data['price_change'] = game_data['close'].diff()
        game_data['price_change_pct'] = (game_data['price_change'] / game_data['close'].shift(1)).abs() * 100
        
        print(f"Game duration: {len(game_data)} minutes")
        print(f"Price range: {game_data['close'].min():.0f}c - {game_data['close'].max():.0f}c\n")
        
        # Simulate minute by minute
        for idx, row in game_data.iterrows():
            if idx == 0:
                continue  # Skip first minute
            
            current_time = row['datetime']
            current_price = row['close']
            price_move = row['price_change_pct']
            volume = row['volume']
            
            # Update existing positions
            self.position_manager.update_positions(game_data, current_time)
            
            # Check for exits
            positions_to_exit = self.position_manager.check_exits(current_time)
            
            for position in positions_to_exit:
                # Execute sell order
                execution = self.order_executor.execute_sell(
                    game_id, current_time, current_price, volume, position.size
                )
                
                # Close position
                self.position_manager.close_position(
                    position, execution['executed_price'], current_time
                )
                
                print(f"[{current_time}] SELL {position.strategy_name} @ {execution['executed_price']:.1f}c | "
                      f"P/L: {position.realized_pl_pct:+.2f}% (${position.realized_pl_dollars:+.2f})")
            
            # Check for new signals
            for strategy in self.strategies:
                # Check if price is in range
                if not (strategy.price_min <= current_price <= strategy.price_max):
                    continue
                
                # Check if move exceeds threshold
                if price_move > strategy.move_threshold:
                    # Generate signal
                    signal = Signal(
                        timestamp=current_time,
                        game_id=game_id,
                        strategy_name=strategy.name,
                        action='BUY',
                        entry_price=current_price,
                        target_exit_time=current_time + pd.Timedelta(minutes=strategy.hold_period),
                        expected_pl=strategy.expected_pl,
                        confidence=strategy.win_rate,
                        reason=f"Price moved {price_move:.1f}%"
                    )
                    
                    self.signals_generated.append(signal)
                    
                    # Execute buy order
                    execution = self.order_executor.execute_buy(
                        game_id, current_time, current_price, volume
                    )
                    
                    # Open position
                    position = self.position_manager.open_position(
                        game_id=game_id,
                        strategy_name=strategy.name,
                        entry_time=current_time,
                        entry_price=execution['executed_price'],
                        hold_period=strategy.hold_period,
                        expected_pl=strategy.expected_pl,
                        size=execution['executed_size']
                    )
                    
                    print(f"[{current_time}] BUY {strategy.name} @ {execution['executed_price']:.1f}c | "
                          f"Price moved {price_move:.1f}% | Hold {strategy.hold_period}min")
        
        # Force close any remaining open positions at end of game
        for position in self.position_manager.get_open_positions():
            final_price = game_data.iloc[-1]['close']
            final_time = game_data.iloc[-1]['datetime']
            self.position_manager.close_position(position, final_price, final_time)
            print(f"[END] Force closed {position.strategy_name} @ {final_price:.1f}c")
        
        # Get results
        results = self._compile_results(game_id, game_data)
        return results
    
    def _compile_results(self, game_id: str, game_data: pd.DataFrame) -> Dict:
        """Compile simulation results"""
        performance = self.position_manager.get_performance_summary()
        positions_df = self.position_manager.get_positions_dataframe()
        
        print(f"\n{'='*80}")
        print(f"GAME {game_id} RESULTS")
        print(f"{'='*80}\n")
        
        print(f"Total Trades:       {performance['total_trades']}")
        print(f"Wins:               {performance['wins']} ({performance['win_rate']:.1%})")
        print(f"Losses:             {performance['losses']}")
        print(f"Total P/L:          ${performance['total_pl_dollars']:+.2f}")
        print(f"Avg P/L:            {performance['avg_pl_pct']:+.2f}%")
        print(f"Total Fees:         ${performance['total_fees']:.2f}")
        
        return {
            'game_id': game_id,
            'game_data': game_data,
            'performance': performance,
            'positions': positions_df,
            'signals': pd.DataFrame([
                {
                    'timestamp': s.timestamp,
                    'strategy': s.strategy_name,
                    'action': s.action,
                    'price': s.entry_price,
                    'reason': s.reason
                } for s in self.signals_generated
            ])
        }


def simulate_random_games(n_games: int = 3):
    """
    Simulate trading on N random games.
    
    Args:
        n_games: Number of games to simulate
    """
    print("\n" + "="*80)
    print("LIVE TRADING SIMULATOR - RANDOM GAMES")
    print("="*80)
    
    # Load data
    print("\nLoading Kalshi data...")
    from src.data.loader import load_kalshi_games
    from src.data.preprocessor import fill_prices
    
    kalshi_df = load_kalshi_games()
    kalshi_df = fill_prices(kalshi_df)
    
    # Ensure datetime is proper type
    if not pd.api.types.is_datetime64_any_dtype(kalshi_df['datetime']):
        kalshi_df['datetime'] = pd.to_datetime(kalshi_df['datetime'])
    
    # Select random games
    all_games = kalshi_df['game_id'].unique()
    selected_games = np.random.choice(all_games, size=min(n_games, len(all_games)), replace=False)
    
    print(f"Selected {len(selected_games)} random games to simulate\n")
    
    # Run simulations
    results = []
    
    for game_id in selected_games:
        simulator = GameSimulator(strategies_to_use=5, position_size=100)
        result = simulator.simulate_game(kalshi_df, game_id)
        results.append(result)
    
    # Aggregate results
    print("\n" + "="*80)
    print("AGGREGATE RESULTS ACROSS ALL GAMES")
    print("="*80 + "\n")
    
    total_trades = sum(r['performance']['total_trades'] for r in results)
    total_wins = sum(r['performance']['wins'] for r in results)
    total_pl = sum(r['performance']['total_pl_dollars'] for r in results)
    total_fees = sum(r['performance']['total_fees'] for r in results)
    
    print(f"Total Games:        {len(results)}")
    print(f"Total Trades:       {total_trades}")
    print(f"Total Wins:         {total_wins} ({total_wins/total_trades:.1%} win rate)")
    print(f"Total P/L:          ${total_pl:+.2f}")
    print(f"Avg P/L per game:   ${total_pl/len(results):+.2f}")
    print(f"Total Fees Paid:    ${total_fees:.2f}\n")
    
    return results


if __name__ == "__main__":
    # Run simulation on 3 random games
    results = simulate_random_games(n_games=3)

