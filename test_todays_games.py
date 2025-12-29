"""
Test ML Trading on Today's Games

Tests on specific games:
- Pistons vs Clippers
- Kings vs Lakers
"""
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_engine.signals.ml_signal_generator import MLSignalGenerator
from src.data.loader import load_kalshi_games
from src.data.realtime_pbp import RealTimePBPFetcher
from src.backtesting.fees import calculate_kalshi_fees
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def find_todays_games(df):
    """Find today's games in the dataset"""
    # Get unique games with team info
    games = df[['game_id', 'away_team', 'home_team', 'game_date']].drop_duplicates()
    
    # Find Pistons vs Clippers
    pistons_clippers = games[
        ((games['away_team'].str.contains('DET|Pistons', case=False, na=False)) & 
         (games['home_team'].str.contains('LAC|Clippers', case=False, na=False))) |
        ((games['home_team'].str.contains('DET|Pistons', case=False, na=False)) & 
         (games['away_team'].str.contains('LAC|Clippers', case=False, na=False)))
    ]
    
    # Find Kings vs Lakers
    kings_lakers = games[
        ((games['away_team'].str.contains('SAC|Kings', case=False, na=False)) & 
         (games['home_team'].str.contains('LAL|Lakers', case=False, na=False))) |
        ((games['home_team'].str.contains('SAC|Kings', case=False, na=False)) & 
         (games['away_team'].str.contains('LAL|Lakers', case=False, na=False)))
    ]
    
    return pistons_clippers, kings_lakers


def simulate_game_live(game_id, game_info, kalshi_df, pbp_fetcher, ml_gen):
    """Simulate trading on a specific game"""
    logger.info("="*80)
    logger.info(f"TRADING: {game_info['away_team']} @ {game_info['home_team']}")
    logger.info(f"Game ID: {game_id}")
    logger.info(f"Date: {game_info['game_date']}")
    logger.info("="*80)
    
    # Get game data
    game_df = kalshi_df[kalshi_df['game_id'] == game_id].sort_values('game_minute').reset_index(drop=True)
    
    if len(game_df) == 0:
        logger.warning("No Kalshi data for this game")
        return None
    
    logger.info(f"Loaded {len(game_df)} minutes of Kalshi data")
    
    # Fetch real-time PBP data
    logger.info("Fetching real-time NBA play-by-play...")
    pbp_data = pbp_fetcher.fetch_game_pbp(game_id)
    
    if not pbp_data:
        logger.warning("Could not fetch NBA API data")
        return None
    
    # Convert PBP to DataFrame
    pbp_df = pbp_fetcher.convert_to_dataframe(pbp_data)
    logger.info(f"Loaded {len(pbp_df)} play-by-play actions")
    
    # Calculate game minutes from PBP data
    pbp_df['game_minute'] = 0
    for idx, row in pbp_df.iterrows():
        period = row.get('period', 1)
        clock_str = row.get('clock', 'PT12M00.00S')
        
        try:
            clock_str = clock_str.replace('PT', '').replace('S', '')
            if 'M' in clock_str:
                parts = clock_str.split('M')
                minutes = int(parts[0])
                seconds = float(parts[1]) if len(parts) > 1 else 0
            else:
                minutes = 0
                seconds = float(clock_str)
            
            seconds_elapsed_in_period = (12 * 60) - (minutes * 60 + seconds)
            game_minute = (period - 1) * 12 + int(seconds_elapsed_in_period / 60)
            pbp_df.at[idx, 'game_minute'] = game_minute
        except:
            pbp_df.at[idx, 'game_minute'] = 0
    
    # Get scores by minute
    minute_scores = pbp_df.groupby('game_minute').agg({
        'score_home': 'last',
        'score_away': 'last'
    }).reset_index()
    
    # Merge with Kalshi data
    game_df = pd.merge(
        game_df,
        minute_scores,
        on='game_minute',
        how='left'
    )
    
    # Forward fill scores
    game_df['score_home'] = game_df['score_home'].ffill().bfill().fillna(0)
    game_df['score_away'] = game_df['score_away'].ffill().bfill().fillna(0)
    
    logger.info(f"Merged data - score range: {game_df['score_home'].min():.0f}-{game_df['score_home'].max():.0f} (home)")
    
    # Run trading simulation
    logger.info("\nSimulating trades...")
    trades = []
    open_positions = []
    
    for minute in game_df['game_minute'].unique():
        if minute < 10:
            continue
        
        minute_data = game_df[game_df['game_minute'] <= minute]
        current_price = game_df[game_df['game_minute'] == minute]['close'].iloc[0]
        current_score_home = game_df[game_df['game_minute'] == minute]['score_home'].iloc[0]
        current_score_away = game_df[game_df['game_minute'] == minute]['score_away'].iloc[0]
        
        # Generate signal
        signal = ml_gen.generate_signal(minute_data, minute)
        
        if signal:
            logger.info(f"  [BUY] Minute {minute}: Price={signal['price']:.0f}¢, Prob={signal['probability']:.3f}, Hold={signal['hold_minutes']}min")
            logger.info(f"        Score: {current_score_away:.0f}-{current_score_home:.0f}")
            
            position = {
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
                exit_price = current_price
                
                # Calculate P/L
                buy_fee = calculate_kalshi_fees(pos['contracts'], pos['entry_price'], is_taker=True)
                sell_fee = calculate_kalshi_fees(pos['contracts'], exit_price, is_taker=True)
                
                gross_profit_cents = (exit_price - pos['entry_price']) * pos['contracts']
                net_profit = (gross_profit_cents / 100) - buy_fee - sell_fee
                
                win_symbol = "[WIN]" if net_profit > 0 else "[LOSS]"
                logger.info(f"  {win_symbol} Minute {minute}: Exit={exit_price:.0f}¢, P/L=${net_profit:+.2f}")
                logger.info(f"        Score: {current_score_away:.0f}-{current_score_home:.0f}")
                
                trade = {
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
        final_score_home = game_df['score_home'].iloc[-1]
        final_score_away = game_df['score_away'].iloc[-1]
        
        logger.info(f"\nClosing {len(open_positions)} remaining positions at game end...")
        
        for pos in open_positions:
            buy_fee = calculate_kalshi_fees(pos['contracts'], pos['entry_price'], is_taker=True)
            sell_fee = calculate_kalshi_fees(pos['contracts'], final_price, is_taker=True)
            
            gross_profit_cents = (final_price - pos['entry_price']) * pos['contracts']
            net_profit = (gross_profit_cents / 100) - buy_fee - sell_fee
            
            win_symbol = "[WIN]" if net_profit > 0 else "[LOSS]"
            logger.info(f"  {win_symbol} Final: Exit={final_price:.0f}¢, P/L=${net_profit:+.2f}")
            logger.info(f"        Final Score: {final_score_away:.0f}-{final_score_home:.0f}")
            
            trade = {
                'entry_minute': pos['entry_minute'],
                'exit_minute': final_minute,
                'entry_price': pos['entry_price'],
                'exit_price': final_price,
                'contracts': pos['contracts'],
                'net_profit': net_profit,
                'probability': pos['probability']
            }
            trades.append(trade)
    
    # Summary
    if len(trades) > 0:
        total_pl = sum(t['net_profit'] for t in trades)
        wins = sum(1 for t in trades if t['net_profit'] > 0)
        win_rate = wins / len(trades)
        
        logger.info("\n" + "="*80)
        logger.info("GAME SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Trades: {len(trades)}")
        logger.info(f"Wins: {wins} ({win_rate:.1%})")
        logger.info(f"Losses: {len(trades) - wins}")
        logger.info(f"Total P/L: ${total_pl:+,.2f}")
        logger.info(f"Avg P/L: ${total_pl/len(trades):+.2f}")
        
        if wins > 0:
            avg_win = np.mean([t['net_profit'] for t in trades if t['net_profit'] > 0])
            logger.info(f"Avg Win: ${avg_win:.2f}")
        if wins < len(trades):
            avg_loss = np.mean([t['net_profit'] for t in trades if t['net_profit'] <= 0])
            logger.info(f"Avg Loss: ${avg_loss:.2f}")
    else:
        logger.info("\nNo trades executed in this game")
        total_pl = 0
        win_rate = 0
    
    return {
        'game_id': game_id,
        'trades': trades,
        'total_pl': total_pl,
        'win_rate': win_rate if len(trades) > 0 else 0
    }


def main():
    print("\n" + "="*80)
    print("LIVE TRADING TEST - TODAY'S GAMES")
    print("="*80)
    
    # Load data
    print("\nLoading Kalshi data...")
    df = load_kalshi_games()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values(['game_id', 'datetime'])
    df['game_minute'] = df.groupby('game_id').cumcount()
    
    print(f"Loaded {len(df):,} rows from {df['game_id'].nunique()} games")
    
    # Find today's games
    print("\nSearching for today's games...")
    pistons_clippers, kings_lakers = find_todays_games(df)
    
    print(f"\nPistons vs Clippers: {len(pistons_clippers)} game(s) found")
    if len(pistons_clippers) > 0:
        print(pistons_clippers[['game_id', 'away_team', 'home_team', 'game_date']].to_string(index=False))
    
    print(f"\nKings vs Lakers: {len(kings_lakers)} game(s) found")
    if len(kings_lakers) > 0:
        print(kings_lakers[['game_id', 'away_team', 'home_team', 'game_date']].to_string(index=False))
    
    # Combine games to test
    games_to_test = pd.concat([pistons_clippers, kings_lakers])
    
    if len(games_to_test) == 0:
        print("\n[ERROR] No matching games found in dataset!")
        print("\nLet me show you some recent games available:")
        recent = df[['game_id', 'away_team', 'home_team', 'game_date']].drop_duplicates().tail(10)
        print(recent.to_string(index=False))
        return
    
    # Initialize components
    print("\nInitializing ML model and NBA API fetcher...")
    pbp_fetcher = RealTimePBPFetcher()
    ml_gen = MLSignalGenerator()
    print("[OK] Ready to trade!\n")
    
    # Trade each game
    results = []
    for idx, row in games_to_test.iterrows():
        result = simulate_game_live(
            row['game_id'],
            row,
            df,
            pbp_fetcher,
            ml_gen
        )
        
        if result:
            results.append(result)
        
        print("\n")
    
    # Overall summary
    if len(results) > 0:
        print("="*80)
        print("OVERALL SUMMARY")
        print("="*80)
        
        total_trades = sum(len(r['trades']) for r in results)
        total_pl = sum(r['total_pl'] for r in results)
        
        if total_trades > 0:
            all_trades = []
            for r in results:
                all_trades.extend(r['trades'])
            
            wins = sum(1 for t in all_trades if t['net_profit'] > 0)
            win_rate = wins / len(all_trades)
            
            print(f"\nGames Traded: {len(results)}")
            print(f"Total Trades: {total_trades}")
            print(f"Win Rate: {win_rate:.1%}")
            print(f"Total P/L: ${total_pl:+,.2f}")
            print(f"Avg P/L per Trade: ${total_pl/total_trades:+.2f}")
            print(f"Avg P/L per Game: ${total_pl/len(results):+.2f}")
        else:
            print("\nNo trades executed across all games")
    
    print("\n" + "="*80)
    print("[OK] Live trading test complete!")
    print("="*80)


if __name__ == "__main__":
    main()




