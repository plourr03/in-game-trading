"""
Run live trading simulator with ML model

Compares ML-based vs Rule-based strategies
"""
import pandas as pd
import numpy as np
import sys
import os
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_engine.signals.signal_generator import SignalGenerator
from trading_engine.signals.ml_signal_generator import MLSignalGenerator
from trading_engine.execution.position_manager import PositionManager
from trading_engine.execution.order_executor import OrderExecutor
from trading_engine.visualization.trade_visualizer import TradeVisualizer
from src.data.loader import load_kalshi_games, connect_to_pbp_db, load_pbp_data
from src.data.aligner import align_pbp_to_minutes
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def run_ml_simulation(n_games=10, use_ml=True, visualize_top=3):
    """
    Run trading simulation with ML model
    
    Args:
        n_games: Number of games to simulate
        use_ml: If True, use ML signals. If False, use rule-based signals
        visualize_top: Number of top profitable games to visualize
    """
    logger.info("="*100)
    logger.info("LIVE TRADING SIMULATOR - ML vs RULES COMPARISON")
    logger.info("="*100)
    
    # Load data
    logger.info("\n[1/5] Loading Kalshi data...")
    df = load_kalshi_games()
    
    # Calculate game_minute
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values(['game_id', 'datetime'])
    df['game_minute'] = df.groupby('game_id').cumcount()
    
    # Add empty score columns for compatibility (will be filled by PBP if available)
    df['score_home'] = np.nan
    df['score_away'] = np.nan
    
    # Filter for complete games
    game_summary = df.groupby('game_id').agg({
        'game_minute': 'max',
        'close': ['min', 'max', 'mean']
    }).reset_index()
    game_summary.columns = ['game_id', 'max_minute', 'price_min', 'price_max', 'price_mean']
    
    # Select games with full data and price movement
    valid_games = game_summary[
        (game_summary['max_minute'] >= 40) &
        (game_summary['price_max'] - game_summary['price_min'] >= 5)
    ]['game_id'].values
    
    logger.info(f"  Found {len(valid_games)} valid games")
    
    # Select random games
    np.random.seed(42)
    selected_games = np.random.choice(valid_games, min(n_games, len(valid_games)), replace=False)
    logger.info(f"  Selected {len(selected_games)} games for simulation")
    
    # Load PBP data
    logger.info("\n[2/5] Loading play-by-play data...")
    try:
        import yaml
        config_path = 'config/config.yaml'
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        db_config = config['database']
        conn = connect_to_pbp_db(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password']
        )
        
        # Load PBP data for selected games
        pbp_df = load_pbp_data(selected_games.tolist(), conn)
        logger.info(f"  Loaded {len(pbp_df)} play-by-play events")
        
        # Merge PBP data with Kalshi data
        if not pbp_df.empty:
            pbp_by_minute = align_pbp_to_minutes(pbp_df)
            
            # Merge for each selected game
            for game_id in selected_games:
                game_pbp = pbp_by_minute[pbp_by_minute['game_id'] == str(game_id).zfill(10)]
                if not game_pbp.empty:
                    # Merge scores into main dataframe
                    game_mask = df['game_id'] == game_id
                    game_data = df[game_mask].copy()
                    
                    merged = pd.merge(
                        game_data,
                        game_pbp[['game_id', 'game_minute', 'score_home', 'score_away']],
                        on=['game_id', 'game_minute'],
                        how='left'
                    )
                    
                    df.loc[game_mask, 'score_home'] = merged['score_home'].values
                    df.loc[game_mask, 'score_away'] = merged['score_away'].values
            
            # Fill forward scores
            df['score_home'] = df.groupby('game_id')['score_home'].ffill().bfill().fillna(0)
            df['score_away'] = df.groupby('game_id')['score_away'].ffill().bfill().fillna(0)
        
        conn.close()
    except Exception as e:
        logger.warning(f"  Could not load PBP data: {e}")
        logger.warning(f"  Continuing without PBP features...")
    
    # Initialize components
    logger.info(f"\n[3/5] Initializing trading engine...")
    
    if use_ml:
        signal_gen = MLSignalGenerator()
        logger.info(f"  ✓ ML Signal Generator")
        logger.info(f"    - Threshold: {signal_gen.entry_threshold}")
        logger.info(f"    - Contracts: {signal_gen.base_contracts}")
    else:
        signal_gen = SignalGenerator()
        logger.info(f"  ✓ Rule-based Signal Generator")
    
    position_mgr = PositionManager()
    order_executor = OrderExecutor()
    visualizer = TradeVisualizer()
    
    # Run simulations
    logger.info(f"\n[4/5] Running simulations...")
    
    all_results = []
    game_profits = {}
    
    for game_id in selected_games:
        game_df = df[df['game_id'] == game_id].sort_values('game_minute').reset_index(drop=True)
        
        # Skip if no data
        if len(game_df) == 0:
            continue
        
        # Reset for new game
        position_mgr.reset()
        game_trades = []
        
        # Simulate game minute by minute
        for minute in game_df['game_minute'].unique():
            minute_data = game_df[game_df['game_minute'] <= minute]
            current_price = game_df[game_df['game_minute'] == minute]['close'].iloc[0]
            
            # Generate signal
            if use_ml:
                signal = signal_gen.generate_signal(minute_data, minute)
            else:
                signal = signal_gen.generate_signal(minute_data, minute)
            
            # Execute buy order
            if signal:
                order = order_executor.execute_buy(
                    price=signal['price'],
                    contracts=signal['contracts'],
                    game_minute=minute,
                    strategy=signal.get('strategy', 'Unknown')
                )
                
                # Add metadata for tracking
                order['game_id'] = game_id
                order['entry_minute'] = minute
                order['entry_price'] = signal['price']
                order['contracts'] = signal['contracts']
                
                # Add hold time if ML
                if use_ml:
                    order['hold_until_minute'] = minute + signal['hold_minutes']
                    order['probability'] = signal['probability']
                else:
                    order['hold_until_minute'] = minute + 5  # Default 5 min hold
                
                position_mgr.positions.append(order)
            
            # Check exits
            positions_to_close = []
            
            if use_ml:
                # Exit based on ML predicted timing
                for pos in position_mgr.positions:
                    if minute >= pos['hold_until_minute']:
                        positions_to_close.append(pos)
            else:
                # Exit based on rule-based logic (profit target or time-based)
                for pos in position_mgr.positions:
                    entry_price = pos['entry_price']
                    profit_cents = current_price - entry_price
                    
                    # Exit if profit target hit (5 cents) or max hold time (5 min)
                    if profit_cents >= 5 or minute >= pos['hold_until_minute']:
                        positions_to_close.append(pos)
            
            # Execute exits
            for pos in positions_to_close:
                exit_order = order_executor.execute_sell(
                    position=pos,
                    current_price=current_price,
                    game_minute=minute
                )
                exit_order['game_id'] = game_id
                exit_order['entry_minute'] = pos['entry_minute']
                exit_order['exit_minute'] = minute
                position_mgr.positions.remove(pos)
                game_trades.append(exit_order)
        
        # Close remaining positions at game end
        final_price = game_df['close'].iloc[-1]
        final_minute = game_df['game_minute'].iloc[-1]
        
        for pos in position_mgr.positions[:]:
            exit_order = order_executor.execute_sell(
                position=pos,
                current_price=final_price,
                game_minute=final_minute
            )
            exit_order['game_id'] = game_id
            exit_order['entry_minute'] = pos['entry_minute']
            exit_order['exit_minute'] = final_minute
            game_trades.append(exit_order)
        
        position_mgr.positions.clear()
        
        # Calculate game results
        if len(game_trades) > 0:
            game_profit = sum(t['net_profit'] for t in game_trades)
            game_profits[game_id] = {
                'profit': game_profit,
                'trades': len(game_trades),
                'win_rate': sum(1 for t in game_trades if t['net_profit'] > 0) / len(game_trades)
            }
            
            all_results.extend(game_trades)
            
            logger.info(f"  Game {game_id}: {len(game_trades)} trades, ${game_profit:,.2f} P/L")
    
    # Display results
    logger.info(f"\n[5/5] Results Summary")
    logger.info("="*100)
    
    if len(all_results) == 0:
        logger.info("  No trades executed!")
        return
    
    total_trades = len(all_results)
    winning_trades = sum(1 for t in all_results if t['net_profit'] > 0)
    total_profit = sum(t['net_profit'] for t in all_results)
    
    logger.info(f"\n{'ML MODEL' if use_ml else 'RULE-BASED'} STRATEGY:")
    logger.info(f"  Games: {len(selected_games)}")
    logger.info(f"  Total Trades: {total_trades:,}")
    logger.info(f"  Win Rate: {winning_trades/total_trades:.1%}")
    logger.info(f"  Total P/L: ${total_profit:,.2f}")
    logger.info(f"  Avg P/L per Trade: ${total_profit/total_trades:.2f}")
    logger.info(f"  Avg Trades per Game: {total_trades/len(selected_games):.1f}")
    
    # Scale to 502 games
    scale_factor = 502 / len(selected_games)
    logger.info(f"\n  SCALED TO 502 GAMES:")
    logger.info(f"    Estimated Trades: {int(total_trades * scale_factor):,}")
    logger.info(f"    Estimated P/L: ${total_profit * scale_factor:,.2f}")
    
    # Visualize top games
    if visualize_top > 0:
        logger.info(f"\n[BONUS] Visualizing top {visualize_top} profitable games...")
        
        sorted_games = sorted(game_profits.items(), key=lambda x: x[1]['profit'], reverse=True)
        top_games = [g[0] for g in sorted_games[:visualize_top]]
        
        for game_id in top_games:
            game_df = df[df['game_id'] == game_id].sort_values('game_minute')
            game_trades = [t for t in all_results if t['game_id'] == game_id]
            
            output_path = f"trading_engine/outputs/{'ML' if use_ml else 'RULES'}_game_{game_id}.png"
            visualizer.plot_game(game_df, game_trades, output_path)
            logger.info(f"  ✓ Saved: {output_path}")
    
    return all_results, game_profits


if __name__ == "__main__":
    # Run both ML and Rules-based for comparison
    print("\n" + "="*100)
    print("RUNNING ML MODEL")
    print("="*100)
    ml_results, ml_profits = run_ml_simulation(n_games=20, use_ml=True, visualize_top=2)
    
    print("\n" + "="*100)
    print("RUNNING RULE-BASED MODEL")
    print("="*100)
    rules_results, rules_profits = run_ml_simulation(n_games=20, use_ml=False, visualize_top=2)
    
    # Compare
    print("\n" + "="*100)
    print("FINAL COMPARISON")
    print("="*100)
    
    if ml_results and rules_results:
        ml_profit = sum(t['net_profit'] for t in ml_results)
        rules_profit = sum(t['net_profit'] for t in rules_results)
        
        print(f"\nML Model:        ${ml_profit:,.2f} ({len(ml_results)} trades)")
        print(f"Rule-Based:      ${rules_profit:,.2f} ({len(rules_results)} trades)")
        print(f"Difference:      ${ml_profit - rules_profit:,.2f}")
        print(f"Improvement:     {((ml_profit - rules_profit) / abs(rules_profit) * 100):+.1f}%")
        
        if ml_profit > rules_profit:
            print("\n🏆 ML MODEL WINS! Integrating into trading engine...")
        else:
            print("\n📊 Rule-based still better. More optimization needed.")

