"""
Test optimized model in actual trading
"""
import pandas as pd
import numpy as np
import joblib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
from src.backtesting.fees import calculate_kalshi_fees
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def test_optimized_model():
    """Test optimized LightGBM model in trading"""
    
    logger.info("="*100)
    logger.info("TESTING OPTIMIZED MODEL (Feature Selection + Hyperparameter Tuning)")
    logger.info("="*100)
    
    # Load optimized model
    logger.info("\nLoading optimized model...")
    model = joblib.load('ml_models/outputs/optimized_entry_model.pkl')
    features = joblib.load('ml_models/outputs/optimized_entry_features.pkl')
    logger.info(f"Using {len(features)} selected features")
    
    # Load data
    logger.info("\nLoading data...")
    kalshi_df = load_kalshi_games()
    kalshi_df = fill_prices(kalshi_df)
    kalshi_df['datetime'] = pd.to_datetime(kalshi_df['datetime'])
    kalshi_df['game_minute'] = kalshi_df['datetime'].dt.hour * 60 + kalshi_df['datetime'].dt.minute
    kalshi_df['time_remaining'] = kalshi_df.groupby('game_id')['game_minute'].transform('max') - kalshi_df['game_minute']
    kalshi_df['period'] = (kalshi_df['game_minute'] // 12 + 1).clip(upper=4)
    kalshi_df['score_diff'] = 0
    kalshi_df['scoring_rate_3min'] = 0
    kalshi_df['score_momentum'] = 0
    kalshi_df['lead_extending'] = 0
    
    # Calculate all needed features
    kalshi_df['spread'] = kalshi_df['high'] - kalshi_df['low']
    kalshi_df['current_price'] = kalshi_df['close']
    kalshi_df['is_extreme_low'] = (kalshi_df['close'] <= 10).astype(int)
    kalshi_df['is_extreme_high'] = (kalshi_df['close'] >= 90).astype(int)
    kalshi_df['is_extreme_price'] = (kalshi_df['is_extreme_low'] | kalshi_df['is_extreme_high']).astype(int)
    kalshi_df['is_mid_price'] = ((kalshi_df['close'] > 40) & (kalshi_df['close'] < 60)).astype(int)
    kalshi_df['is_close_game'] = 0
    kalshi_df['is_late_game'] = (kalshi_df['time_remaining'] <= 5).astype(int)
    kalshi_df['is_very_late'] = (kalshi_df['time_remaining'] <= 2).astype(int)
    kalshi_df['price_move_1min'] = kalshi_df.groupby('game_id')['close'].pct_change() * 100
    kalshi_df['price_move_3min'] = kalshi_df.groupby('game_id')['close'].pct_change(3) * 100
    kalshi_df['price_move_5min'] = kalshi_df.groupby('game_id')['close'].pct_change(5) * 100
    kalshi_df['volatility_5min'] = kalshi_df.groupby('game_id')['close'].rolling(5).std().reset_index(0, drop=True)
    kalshi_df['volume_spike'] = kalshi_df['volume'] / (kalshi_df.groupby('game_id')['volume'].rolling(5).mean().reset_index(0, drop=True) + 1e-6)
    kalshi_df['large_move'] = (kalshi_df['price_move_1min'].abs() > 5).astype(int)
    kalshi_df['huge_move'] = (kalshi_df['price_move_1min'].abs() > 10).astype(int)
    
    # Test games
    all_games = kalshi_df['game_id'].unique()
    split_idx = int(len(all_games) * 0.8)
    test_games = all_games[split_idx:][:20]
    test_df = kalshi_df[kalshi_df['game_id'].isin(test_games)].copy()
    
    logger.info(f"Testing on {len(test_games)} games")
    
    # Test different thresholds
    thresholds = [0.7, 0.75, 0.8, 0.85, 0.9]
    results = []
    
    for threshold in thresholds:
        logger.info(f"\n--- Testing threshold {threshold} ---")
        
        all_trades = []
        for game_id in test_games:
            game_df = test_df[test_df['game_id'] == game_id].copy().reset_index(drop=True)
            
            trades = []
            position = None
            
            for idx in range(len(game_df)):
                if position is None:
                    # Get features
                    row = game_df.iloc[idx]
                    X = np.array([[row[f] for f in features]])
                    X = np.nan_to_num(X, 0)
                    
                    # Predict
                    prob = model.predict_proba(X)[0, 1]
                    
                    if prob >= threshold:
                        position = {
                            'entry_idx': idx,
                            'entry_price': row['close'],
                            'hold_period': 7
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
                            'fees': total_fees
                        })
                        
                        position = None
            
            if len(trades) > 0:
                trades_df = pd.DataFrame(trades)
                all_trades.append(trades_df)
        
        if all_trades:
            all_trades_df = pd.concat(all_trades, ignore_index=True)
            
            result = {
                'threshold': threshold,
                'trades': len(all_trades_df),
                'win_rate': all_trades_df['is_winner'].mean(),
                'avg_pl': all_trades_df['net_pl'].mean(),
                'total_pl': all_trades_df['net_pl'].sum(),
                'avg_fees': all_trades_df['fees'].mean()
            }
            results.append(result)
            
            logger.info(f"  Trades: {result['trades']}")
            logger.info(f"  Win Rate: {result['win_rate']:.1%}")
            logger.info(f"  Total P/L: ${result['total_pl']:.2f}")
        else:
            logger.info(f"  No trades generated")
    
    # Display results
    logger.info("\n" + "="*100)
    logger.info("OPTIMIZED MODEL BACKTEST RESULTS")
    logger.info("="*100)
    
    results_df = pd.DataFrame(results)
    print()
    print(results_df.to_string(index=False))
    
    # Compare to baseline
    logger.info("\n" + "="*100)
    logger.info("COMPARISON TO BASELINE")
    logger.info("="*100)
    
    best_idx = results_df['total_pl'].idxmax()
    best = results_df.iloc[best_idx]
    
    logger.info(f"\nOPTIMIZED MODEL (threshold {best['threshold']}):")
    logger.info(f"  Trades: {best['trades']:.0f}")
    logger.info(f"  Win Rate: {best['win_rate']:.1%}")
    logger.info(f"  Total P/L: ${best['total_pl']:.2f}")
    
    logger.info(f"\nBASELINE (LightGBM, threshold 0.8):")
    logger.info(f"  Trades: 29")
    logger.info(f"  Win Rate: 72.4%")
    logger.info(f"  Total P/L: $-33.51")
    
    improvement = best['total_pl'] - (-33.51)
    logger.info(f"\nIMPROVEMENT: ${improvement:+.2f}")
    
    if improvement > 0:
        logger.info(f"\n SUCCESS! Optimization improved P/L by ${improvement:.2f}!")
    
    # With 500 contracts
    logger.info("\n" + "="*100)
    logger.info("PROFITABILITY WITH POSITION SIZING")
    logger.info("="*100)
    
    wins = int(best['trades'] * best['win_rate'])
    losses = int(best['trades'] - wins)
    
    logger.info(f"\nWith 500 contracts:")
    logger.info(f"  {wins} wins × $15 = +${wins * 15}")
    logger.info(f"  {losses} losses × $10 = -${losses * 10}")
    logger.info(f"  Fees: {best['trades']:.0f} × $5 = -${best['trades'] * 5:.0f}")
    profit_500 = wins * 15 - losses * 10 - best['trades'] * 5
    logger.info(f"  NET: ${profit_500:+.0f}")
    
    if profit_500 > 0:
        logger.info(f"\n PROFITABLE! ${profit_500:.0f} profit with 500 contracts!")
    
    logger.info("="*100)


if __name__ == "__main__":
    test_optimized_model()

