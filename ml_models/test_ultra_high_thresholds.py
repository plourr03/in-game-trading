"""Test ultra-high thresholds (0.85-0.95) for maximum selectivity"""
import pandas as pd
import numpy as np
import joblib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_models.backtest_comparison import MLStrategy
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
from src.backtesting.fees import calculate_kalshi_fees
from src.utils.helpers import get_logger

logger = get_logger(__name__)

def test_ultra_high_thresholds():
    """Test thresholds from 0.85 to 0.95 for ultra-selectivity"""
    logger.info("="*100)
    logger.info("TESTING ULTRA-HIGH THRESHOLDS (0.85-0.95)")
    logger.info("="*100)
    
    # Load data
    logger.info("\nLoading data...")
    kalshi_df = load_kalshi_games()
    kalshi_df = fill_prices(kalshi_df)
    kalshi_df['datetime'] = pd.to_datetime(kalshi_df['datetime'])
    kalshi_df['game_minute'] = kalshi_df['datetime'].dt.hour * 60 + kalshi_df['datetime'].dt.minute
    kalshi_df['time_remaining'] = kalshi_df.groupby('game_id')['game_minute'].transform('max') - kalshi_df['game_minute']
    kalshi_df['period'] = (kalshi_df['game_minute'] // 12 + 1).clip(upper=4)
    kalshi_df['score_diff'] = 0  # Placeholder
    kalshi_df['scoring_rate_3min'] = 0
    kalshi_df['score_momentum'] = 0
    kalshi_df['lead_extending'] = 0
    
    # Test games
    all_games = kalshi_df['game_id'].unique()
    split_idx = int(len(all_games) * 0.8)
    test_games = all_games[split_idx:][:20]
    test_df = kalshi_df[kalshi_df['game_id'].isin(test_games)].copy()
    
    logger.info(f"Testing on {len(test_games)} games")
    
    # Test ultra-high thresholds
    thresholds = [0.80, 0.85, 0.90, 0.92, 0.95, 0.97]
    results = []
    
    ml_strategy = MLStrategy()
    
    for threshold in thresholds:
        logger.info(f"\n--- Testing threshold {threshold} ---")
        
        ml_trades = []
        for game_id in test_games:
            game_df = test_df[test_df['game_id'] == game_id].copy().reset_index(drop=True)
            
            trades = []
            position = None
            
            for idx in range(len(game_df)):
                if position is None:
                    features = ml_strategy.calculate_features(game_df, idx)
                    should_enter, confidence = ml_strategy.should_enter(features, threshold=threshold)
                    
                    if should_enter:
                        hold_period = ml_strategy.get_hold_period(features)
                        position = {
                            'entry_idx': idx,
                            'entry_price': game_df.iloc[idx]['close'],
                            'hold_period': hold_period,
                            'entry_time': idx,
                            'confidence': confidence
                        }
                
                elif position is not None:
                    time_in_trade = idx - position['entry_idx']
                    
                    if time_in_trade >= position['hold_period'] or idx == len(game_df) - 1:
                        exit_price = game_df.iloc[idx]['close']
                        entry_price = position['entry_price']
                        
                        if idx >= 1 and position['entry_idx'] > 0:
                            prev_price = game_df.iloc[position['entry_idx']-1]['close']
                            price_move_direction = np.sign(entry_price - prev_price)
                        else:
                            price_move_direction = 0
                        
                        if price_move_direction > 0:
                            raw_pl = entry_price - exit_price
                        else:
                            raw_pl = exit_price - entry_price
                        
                        entry_fee = calculate_kalshi_fees(100, entry_price, is_taker=True)
                        exit_fee = calculate_kalshi_fees(100, exit_price, is_taker=True)
                        total_fees = entry_fee + exit_fee
                        net_pl = raw_pl - total_fees
                        
                        trades.append({
                            'net_pl': net_pl,
                            'is_winner': net_pl > 0,
                            'fees': total_fees,
                            'confidence': position['confidence']
                        })
                        
                        position = None
            
            if len(trades) > 0:
                trades_df = pd.DataFrame(trades)
                trades_df['game_id'] = game_id
                ml_trades.append(trades_df)
        
        if ml_trades:
            ml_trades_df = pd.concat(ml_trades, ignore_index=True)
            
            result = {
                'threshold': threshold,
                'trades': len(ml_trades_df),
                'win_rate': ml_trades_df['is_winner'].mean(),
                'avg_pl': ml_trades_df['net_pl'].mean(),
                'total_pl': ml_trades_df['net_pl'].sum(),
                'avg_fees': ml_trades_df['fees'].mean(),
                'avg_confidence': ml_trades_df['confidence'].mean()
            }
            results.append(result)
            
            logger.info(f"  Trades: {result['trades']}")
            logger.info(f"  Win Rate: {result['win_rate']:.1%}")
            logger.info(f"  Total P/L: ${result['total_pl']:.2f}")
            logger.info(f"  Avg Confidence: {result['avg_confidence']:.3f}")
        else:
            logger.info(f"  No trades generated")
            results.append({
                'threshold': threshold,
                'trades': 0,
                'win_rate': 0,
                'avg_pl': 0,
                'total_pl': 0,
                'avg_fees': 0,
                'avg_confidence': 0
            })
    
    # Display results
    logger.info("\n" + "="*100)
    logger.info("ULTRA-HIGH THRESHOLD COMPARISON")
    logger.info("="*100)
    
    results_df = pd.DataFrame(results)
    print()
    print(results_df.to_string(index=False))
    
    # Find best
    results_with_trades = results_df[results_df['trades'] > 0]
    if len(results_with_trades) > 0:
        logger.info("\n" + "="*100)
        best_idx = results_with_trades['total_pl'].idxmax()
        best = results_with_trades.loc[best_idx]
        logger.info(f"BEST THRESHOLD: {best['threshold']}")
        logger.info(f"  Trades: {best['trades']:.0f}")
        logger.info(f"  Win Rate: {best['win_rate']:.1%}")
        logger.info(f"  Total P/L: ${best['total_pl']:.2f}")
        logger.info(f"  Avg P/L: ${best['avg_pl']:.2f}")
        logger.info("="*100)


if __name__ == "__main__":
    test_ultra_high_thresholds()





