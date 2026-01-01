"""
Live Trading Simulator with Real-Time PBP Data

Simulates live trading using:
1. Historical Kalshi price data (minute-by-minute)
2. Real-time NBA API play-by-play data (for scores)
3. ML model for entry/exit signals
"""
import pandas as pd
import numpy as np
import sys
import os
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_engine.signals.ml_signal_generator import MLSignalGenerator
from src.data.loader import load_kalshi_games
from src.data.realtime_pbp import RealTimePBPFetcher
from src.backtesting.fees import calculate_kalshi_fees
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def simulate_live_game(game_id: str, kalshi_df: pd.DataFrame, pbp_fetcher: RealTimePBPFetcher, ml_gen: MLSignalGenerator) -> Dict:
    """
    Simulate live trading on one game
    
    Args:
        game_id: Game ID to simulate
        kalshi_df: Kalshi price data
        pbp_fetcher: Real-time PBP fetcher
        ml_gen: ML signal generator
        
    Returns:
        Dictionary with results
    """
    # Get game data
    game_df = kalshi_df[kalshi_df['game_id'] == game_id].sort_values('game_minute').reset_index(drop=True)
    
    if len(game_df) == 0:
        return None
    
    # Fetch real-time PBP data
    pbp_data = pbp_fetcher.fetch_game_pbp(game_id)
    
    if not pbp_data:
        logger.warning(f"  No PBP data for game {game_id}")
        return None
    
    # Convert PBP to DataFrame and merge with Kalshi data
    pbp_df = pbp_fetcher.convert_to_dataframe(pbp_data)
    
    if len(pbp_df) == 0:
        logger.warning(f"  Empty PBP data for game {game_id}")
        return None
    
    # Create minute-by-minute score data
    pbp_df['game_minute'] = 0  # We'll calculate this based on period/clock
    
    # Simple mapping: period and clock to game_minute
    for idx, row in pbp_df.iterrows():
        period = row.get('period', 1)
        clock_str = row.get('clock', 'PT12M00.00S')
        
        try:
            # Parse clock
            clock_str = clock_str.replace('PT', '').replace('S', '')
            if 'M' in clock_str:
                parts = clock_str.split('M')
                minutes = int(parts[0])
                seconds = float(parts[1]) if len(parts) > 1 else 0
            else:
                minutes = 0
                seconds = float(clock_str)
            
            # Calculate game minute
            seconds_elapsed_in_period = (12 * 60) - (minutes * 60 + seconds)
            game_minute = (period - 1) * 12 + int(seconds_elapsed_in_period / 60)
            pbp_df.at[idx, 'game_minute'] = game_minute
        except:
            pbp_df.at[idx, 'game_minute'] = 0
    
    # Get score at each minute
    minute_scores = pbp_df.groupby('game_minute').agg({
        'score_home': 'last',
        'score_away': 'last'
    }).reset_index()
    
    # Merge scores into game_df
    game_df = pd.merge(
        game_df,
        minute_scores,
        on='game_minute',
        how='left'
    )
    
    # Forward fill scores
    game_df['score_home'] = game_df['score_home'].ffill().bfill().fillna(0)
    game_df['score_away'] = game_df['score_away'].ffill().bfill().fillna(0)
    
    # Simulate trading
    trades = []
    open_positions = []
    
    for minute in game_df['game_minute'].unique():
        if minute < 10:  # Need some history
            continue
        
        minute_data = game_df[game_df['game_minute'] <= minute]
        current_price = game_df[game_df['game_minute'] == minute]['close'].iloc[0]
        
        # Generate signal
        signal = ml_gen.generate_signal(minute_data, minute)
        
        if signal:
            # Open position
            position = {
                'game_id': game_id,
                'entry_minute': minute,
                'entry_price': signal['price'],
                'contracts': signal['contracts'],
                'hold_until': minute + signal['hold_minutes'],
                'probability': signal['probability']
            }
            open_positions.append(position)
        
        # Check exits
        for pos in open_positions[:]:
            if minute >= pos['hold_until']:
                # Close position
                exit_price = current_price
                
                # Calculate P/L
                buy_fee = calculate_kalshi_fees(pos['contracts'], pos['entry_price'], is_taker=True)
                sell_fee = calculate_kalshi_fees(pos['contracts'], exit_price, is_taker=True)
                
                gross_profit_cents = (exit_price - pos['entry_price']) * pos['contracts']
                net_profit = (gross_profit_cents / 100) - buy_fee - sell_fee
                
                trade = {
                    'game_id': game_id,
                    'entry_minute': pos['entry_minute'],
                    'exit_minute': minute,
                    'entry_price': pos['entry_price'],
                    'exit_price': exit_price,
                    'contracts': pos['contracts'],
                    'net_profit': net_profit,
                    'probability': pos['probability']
                }
                trades.append(trade)
                open_positions.remove(pos)
    
    # Close remaining positions
    if len(open_positions) > 0:
        final_price = game_df['close'].iloc[-1]
        final_minute = game_df['game_minute'].iloc[-1]
        
        for pos in open_positions:
            buy_fee = calculate_kalshi_fees(pos['contracts'], pos['entry_price'], is_taker=True)
            sell_fee = calculate_kalshi_fees(pos['contracts'], final_price, is_taker=True)
            
            gross_profit_cents = (final_price - pos['entry_price']) * pos['contracts']
            net_profit = (gross_profit_cents / 100) - buy_fee - sell_fee
            
            trade = {
                'game_id': game_id,
                'entry_minute': pos['entry_minute'],
                'exit_minute': final_minute,
                'entry_price': pos['entry_price'],
                'exit_price': final_price,
                'contracts': pos['contracts'],
                'net_profit': net_profit,
                'probability': pos['probability']
            }
            trades.append(trade)
    
    return {
        'game_id': game_id,
        'trades': trades,
        'total_pl': sum(t['net_profit'] for t in trades),
        'num_trades': len(trades)
    }


def run_live_simulation(n_games=10):
    """
    Run live simulation with real-time PBP data
    
    Args:
        n_games: Number of games to simulate
    """
    logger.info("="*100)
    logger.info("LIVE TRADING SIMULATION - ML MODEL WITH REAL-TIME PBP")
    logger.info("="*100)
    
    # Load Kalshi data
    logger.info("\n[1/4] Loading Kalshi data...")
    df = load_kalshi_games()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values(['game_id', 'datetime'])
    df['game_minute'] = df.groupby('game_id').cumcount()
    
    # Select games with good data
    game_summary = df.groupby('game_id').agg({
        'game_minute': 'max',
        'close': ['min', 'max']
    }).reset_index()
    game_summary.columns = ['game_id', 'max_minute', 'price_min', 'price_max']
    
    valid_games = game_summary[
        (game_summary['max_minute'] >= 40) &
        (game_summary['price_max'] - game_summary['price_min'] >= 5)
    ]['game_id'].values
    
    logger.info(f"  Found {len(valid_games)} valid games")
    
    # Select random games
    np.random.seed(42)
    selected_games = np.random.choice(valid_games, min(n_games, len(valid_games)), replace=False)
    logger.info(f"  Selected {len(selected_games)} games for simulation")
    
    # Initialize components
    logger.info("\n[2/4] Initializing components...")
    pbp_fetcher = RealTimePBPFetcher()
    ml_gen = MLSignalGenerator()
    logger.info("  [OK] ML Signal Generator loaded")
    logger.info("  [OK] Real-time PBP Fetcher initialized")
    
    # Run simulations
    logger.info(f"\n[3/4] Running simulations...")
    
    all_results = []
    
    for i, game_id in enumerate(selected_games, 1):
        logger.info(f"  [{i}/{len(selected_games)}] Simulating game {game_id}...")
        
        result = simulate_live_game(game_id, df, pbp_fetcher, ml_gen)
        
        if result:
            all_results.append(result)
            logger.info(f"      {result['num_trades']} trades, ${result['total_pl']:,.2f} P/L")
    
    # Display results
    logger.info(f"\n[4/4] Results Summary")
    logger.info("="*100)
    
    if len(all_results) == 0:
        logger.info("  No results - no trades generated")
        return
    
    all_trades = []
    for result in all_results:
        all_trades.extend(result['trades'])
    
    if len(all_trades) == 0:
        logger.info("  No trades executed")
        return
    
    total_profit = sum(t['net_profit'] for t in all_trades)
    wins = sum(1 for t in all_trades if t['net_profit'] > 0)
    win_rate = wins / len(all_trades)
    
    logger.info(f"\nML MODEL WITH REAL-TIME PBP:")
    logger.info(f"  Games: {len(all_results)}")
    logger.info(f"  Total Trades: {len(all_trades):,}")
    logger.info(f"  Win Rate: {win_rate:.1%}")
    logger.info(f"  Total P/L: ${total_profit:,.2f}")
    logger.info(f"  Avg P/L per Trade: ${total_profit/len(all_trades):.2f}")
    logger.info(f"  Avg Trades per Game: {len(all_trades)/len(all_results):.1f}")
    
    # Scale to 502 games
    scale_factor = 502 / len(all_results)
    logger.info(f"\n  SCALED TO 502 GAMES:")
    logger.info(f"    Estimated Trades: {int(len(all_trades) * scale_factor):,}")
    logger.info(f"    Estimated P/L: ${total_profit * scale_factor:,.2f}")
    
    # Top games
    top_results = sorted(all_results, key=lambda x: x['total_pl'], reverse=True)[:5]
    logger.info(f"\n  TOP 5 MOST PROFITABLE GAMES:")
    for i, result in enumerate(top_results, 1):
        logger.info(f"    {i}. Game {result['game_id']}: ${result['total_pl']:,.2f} ({result['num_trades']} trades)")
    
    return all_trades, all_results


if __name__ == "__main__":
    print("\n" + "="*100)
    print("LIVE TRADING SIMULATOR - ML MODEL + REAL-TIME NBA API")
    print("="*100)
    
    trades, results = run_live_simulation(n_games=20)
    
    print("\n" + "="*100)
    print("[OK] Simulation complete!")
    print("="*100)





