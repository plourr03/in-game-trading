"""
Test ML + Rules Ensemble: Only take ML trades that ALSO meet rules criteria
This combines ML's pattern recognition with rules-based fee optimization
"""
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

def test_ml_rules_ensemble():
    """Test ML + Rules ensemble strategy"""
    logger.info("="*100)
    logger.info("ML + RULES ENSEMBLE STRATEGY")
    logger.info("="*100)
    
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
    
    # Test games
    all_games = kalshi_df['game_id'].unique()
    split_idx = int(len(all_games) * 0.8)
    test_games = all_games[split_idx:][:20]
    test_df = kalshi_df[kalshi_df['game_id'].isin(test_games)].copy()
    
    logger.info(f"Testing on {len(test_games)} games")
    
    # Test different ensemble configurations
    configs = [
        {'ml_threshold': 0.7, 'price_min': 1, 'price_max': 10, 'move_threshold': 15},
        {'ml_threshold': 0.7, 'price_min': 1, 'price_max': 10, 'move_threshold': 20},
        {'ml_threshold': 0.8, 'price_min': 1, 'price_max': 10, 'move_threshold': 15},
        {'ml_threshold': 0.8, 'price_min': 1, 'price_max': 10, 'move_threshold': 20},
        {'ml_threshold': 0.8, 'price_min': 1, 'price_max': 5, 'move_threshold': 20},
        {'ml_threshold': 0.85, 'price_min': 1, 'price_max': 10, 'move_threshold': 15},
    ]
    
    ml_strategy = MLStrategy()
    results = []
    
    for config in configs:
        logger.info(f"\n--- Testing: ML>{config['ml_threshold']}, Price {config['price_min']}-{config['price_max']}c, Move>{config['move_threshold']}% ---")
        
        ml_trades = []
        for game_id in test_games:
            game_df = test_df[test_df['game_id'] == game_id].copy().reset_index(drop=True)
            
            trades = []
            position = None
            
            for idx in range(len(game_df)):
                if position is None:
                    current_price = game_df.iloc[idx]['close']
                    
                    # Rules check: Price in range?
                    if not (config['price_min'] <= current_price <= config['price_max']):
                        continue
                    
                    # Rules check: Large move?
                    if idx > 0:
                        prev_price = game_df.iloc[idx-1]['close']
                        price_change_pct = abs((current_price - prev_price) / prev_price * 100)
                        if price_change_pct < config['move_threshold']:
                            continue
                    else:
                        continue
                    
                    # ML check: High confidence?
                    features = ml_strategy.calculate_features(game_df, idx)
                    should_enter, confidence = ml_strategy.should_enter(features, threshold=config['ml_threshold'])
                    
                    if should_enter:
                        hold_period = ml_strategy.get_hold_period(features)
                        position = {
                            'entry_idx': idx,
                            'entry_price': current_price,
                            'hold_period': hold_period,
                            'entry_time': idx,
                            'confidence': confidence
                        }
                
                elif position is not None:
                    time_in_trade = idx - position['entry_idx']
                    
                    if time_in_trade >= position['hold_period'] or idx == len(game_df) - 1:
                        exit_price = game_df.iloc[idx]['close']
                        entry_price = position['entry_price']
                        
                        prev_price = game_df.iloc[position['entry_idx']-1]['close']
                        price_move_direction = np.sign(entry_price - prev_price)
                        
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
                            'confidence': position['confidence'],
                            'entry_price': entry_price
                        })
                        
                        position = None
            
            if len(trades) > 0:
                trades_df = pd.DataFrame(trades)
                trades_df['game_id'] = game_id
                ml_trades.append(trades_df)
        
        if ml_trades:
            ml_trades_df = pd.concat(ml_trades, ignore_index=True)
            
            result = {
                'ml_threshold': config['ml_threshold'],
                'price_range': f"{config['price_min']}-{config['price_max']}c",
                'move_threshold': config['move_threshold'],
                'trades': len(ml_trades_df),
                'win_rate': ml_trades_df['is_winner'].mean(),
                'avg_pl': ml_trades_df['net_pl'].mean(),
                'total_pl': ml_trades_df['net_pl'].sum(),
                'avg_fees': ml_trades_df['fees'].mean()
            }
            results.append(result)
            
            logger.info(f"  Trades: {result['trades']}")
            logger.info(f"  Win Rate: {result['win_rate']:.1%}")
            logger.info(f"  Total P/L: ${result['total_pl']:+.2f}")
        else:
            logger.info(f"  No trades generated")
    
    # Display results
    logger.info("\n" + "="*100)
    logger.info("ENSEMBLE STRATEGY RESULTS")
    logger.info("="*100)
    
    if results:
        results_df = pd.DataFrame(results)
        print()
        print(results_df.to_string(index=False))
        
        logger.info("\n" + "="*100)
        best_idx = results_df['total_pl'].idxmax()
        best = results_df.iloc[best_idx]
        logger.info(f"BEST ENSEMBLE:")
        logger.info(f"  ML Threshold: >{best['ml_threshold']}")
        logger.info(f"  Price Range: {best['price_range']}")
        logger.info(f"  Move Threshold: >{best['move_threshold']}%")
        logger.info(f"  Trades: {best['trades']:.0f}")
        logger.info(f"  Win Rate: {best['win_rate']:.1%}")
        logger.info(f"  Total P/L: ${best['total_pl']:+.2f}")
        logger.info(f"  Avg P/L: ${best['avg_pl']:+.2f}")
        logger.info("="*100)


if __name__ == "__main__":
    test_ml_rules_ensemble()




