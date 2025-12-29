"""
Find optimal balance between win rate and trade frequency
Test much lower thresholds to increase trade volume
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


def test_trade_frequency():
    """Test both models at various thresholds to maximize trade frequency"""
    
    logger.info("="*100)
    logger.info("FINDING OPTIMAL WIN RATE vs TRADE FREQUENCY BALANCE")
    logger.info("="*100)
    
    # Load data
    logger.info("\nLoading data...")
    kalshi_df = load_kalshi_games()
    total_games = kalshi_df['game_id'].nunique()
    logger.info(f"Total games in dataset: {total_games}")
    
    kalshi_df = fill_prices(kalshi_df)
    kalshi_df['datetime'] = pd.to_datetime(kalshi_df['datetime'])
    kalshi_df['game_minute'] = kalshi_df['datetime'].dt.hour * 60 + kalshi_df['datetime'].dt.minute
    kalshi_df['time_remaining'] = kalshi_df.groupby('game_id')['game_minute'].transform('max') - kalshi_df['game_minute']
    kalshi_df['period'] = (kalshi_df['game_minute'] // 12 + 1).clip(upper=4)
    kalshi_df['score_diff'] = 0
    kalshi_df['scoring_rate_3min'] = 0
    kalshi_df['score_momentum'] = 0
    kalshi_df['lead_extending'] = 0
    
    # Calculate ALL features (for both models)
    kalshi_df['spread'] = kalshi_df['high'] - kalshi_df['low']
    kalshi_df['current_price'] = kalshi_df['close']
    kalshi_df['score_diff_abs'] = kalshi_df['score_diff'].abs()
    kalshi_df['is_extreme_low'] = (kalshi_df['close'] <= 10).astype(int)
    kalshi_df['is_extreme_high'] = (kalshi_df['close'] >= 90).astype(int)
    kalshi_df['is_extreme_price'] = (kalshi_df['is_extreme_low'] | kalshi_df['is_extreme_high']).astype(int)
    kalshi_df['is_mid_price'] = ((kalshi_df['close'] > 40) & (kalshi_df['close'] < 60)).astype(int)
    kalshi_df['is_close_game'] = (kalshi_df['score_diff_abs'] <= 5).astype(int)
    kalshi_df['is_late_game'] = (kalshi_df['time_remaining'] <= 5).astype(int)
    kalshi_df['is_very_late'] = (kalshi_df['time_remaining'] <= 2).astype(int)
    kalshi_df['price_move_1min'] = kalshi_df.groupby('game_id')['close'].pct_change() * 100
    kalshi_df['price_move_3min'] = kalshi_df.groupby('game_id')['close'].pct_change(3) * 100
    kalshi_df['price_move_5min'] = kalshi_df.groupby('game_id')['close'].pct_change(5) * 100
    kalshi_df['volatility_5min'] = kalshi_df.groupby('game_id')['close'].rolling(5).std().reset_index(0, drop=True)
    kalshi_df['volume_ma5'] = kalshi_df.groupby('game_id')['volume'].rolling(5).mean().reset_index(0, drop=True)
    kalshi_df['volume_spike'] = kalshi_df['volume'] / (kalshi_df['volume_ma5'] + 1e-6)
    kalshi_df['large_move'] = (kalshi_df['price_move_1min'].abs() > 5).astype(int)
    kalshi_df['huge_move'] = (kalshi_df['price_move_1min'].abs() > 10).astype(int)
    
    # Test games
    all_games = kalshi_df['game_id'].unique()
    split_idx = int(len(all_games) * 0.8)
    test_games = all_games[split_idx:][:20]
    test_df = kalshi_df[kalshi_df['game_id'].isin(test_games)].copy()
    
    logger.info(f"Testing on {len(test_games)} games")
    
    # Test BOTH models at MANY thresholds
    models = {
        'Baseline': {
            'model': joblib.load('ml_models/outputs/best_entry_model.pkl'),
            'scaler': joblib.load('ml_models/outputs/best_entry_scaler.pkl'),
            'features': joblib.load('ml_models/outputs/best_entry_features.pkl'),
            'needs_scaling': True
        },
        'Optimized': {
            'model': joblib.load('ml_models/outputs/optimized_entry_model.pkl'),
            'features': joblib.load('ml_models/outputs/optimized_entry_features.pkl'),
            'needs_scaling': False
        }
    }
    
    # Test LOWER thresholds for more trades
    thresholds = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
    
    all_results = []
    
    for model_name, model_info in models.items():
        logger.info(f"\n{'='*100}")
        logger.info(f"TESTING {model_name.upper()} MODEL")
        logger.info(f"{'='*100}")
        
        model = model_info['model']
        features = model_info['features']
        scaler = model_info.get('scaler')
        
        for threshold in thresholds:
            logger.info(f"\n--- Threshold {threshold} ---")
            
            all_trades = []
            games_with_trades = 0
            
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
                        
                        # Scale if needed
                        if scaler is not None:
                            X = scaler.transform(X)
                        
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
                            
                            entry_fee = calculate_kalshi_fees(500, entry_price, is_taker=True)
                            exit_fee = calculate_kalshi_fees(500, exit_price, is_taker=True)
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
                    games_with_trades += 1
            
            if all_trades:
                all_trades_df = pd.concat(all_trades, ignore_index=True)
                
                result = {
                    'model': model_name,
                    'threshold': threshold,
                    'trades': len(all_trades_df),
                    'games_traded': games_with_trades,
                    'trade_frequency': len(all_trades_df) / len(test_games),
                    'win_rate': all_trades_df['is_winner'].mean(),
                    'avg_pl': all_trades_df['net_pl'].mean(),
                    'total_pl': all_trades_df['net_pl'].sum(),
                    'avg_fees': all_trades_df['fees'].mean()
                }
                all_results.append(result)
                
                logger.info(f"  Trades: {result['trades']} across {games_with_trades} games ({result['trade_frequency']:.2f} trades/game)")
                logger.info(f"  Win Rate: {result['win_rate']:.1%}")
                logger.info(f"  Total P/L: ${result['total_pl']:.2f}")
            else:
                logger.info(f"  No trades generated")
    
    # Display comprehensive results
    logger.info("\n" + "="*100)
    logger.info("COMPLETE RESULTS - SORTED BY TOTAL P/L")
    logger.info("="*100)
    
    results_df = pd.DataFrame(all_results).sort_values('total_pl', ascending=False)
    print()
    print(results_df.to_string(index=False))
    
    # Find best by different criteria
    logger.info("\n" + "="*100)
    logger.info("TOP STRATEGIES BY DIFFERENT CRITERIA")
    logger.info("="*100)
    
    # Best total P/L
    best_pl = results_df.iloc[0]
    logger.info(f"\n1. HIGHEST PROFIT:")
    logger.info(f"   {best_pl['model']} @ threshold {best_pl['threshold']}")
    logger.info(f"   {best_pl['trades']:.0f} trades, {best_pl['win_rate']:.1%} win rate")
    logger.info(f"   Total P/L: ${best_pl['total_pl']:.2f}")
    logger.info(f"   Avg P/L per trade: ${best_pl['avg_pl']:.2f}")
    
    # Most trades
    most_trades = results_df.iloc[results_df['trades'].idxmax()]
    logger.info(f"\n2. MOST TRADES:")
    logger.info(f"   {most_trades['model']} @ threshold {most_trades['threshold']}")
    logger.info(f"   {most_trades['trades']:.0f} trades ({most_trades['trade_frequency']:.2f}/game)")
    logger.info(f"   {most_trades['win_rate']:.1%} win rate")
    logger.info(f"   Total P/L: ${most_trades['total_pl']:.2f}")
    
    # Best win rate with >20 trades
    high_volume = results_df[results_df['trades'] >= 20]
    if len(high_volume) > 0:
        best_wr_volume = high_volume.iloc[high_volume['win_rate'].idxmax()]
        logger.info(f"\n3. BEST WIN RATE (with 20+ trades):")
        logger.info(f"   {best_wr_volume['model']} @ threshold {best_wr_volume['threshold']}")
        logger.info(f"   {best_wr_volume['trades']:.0f} trades, {best_wr_volume['win_rate']:.1%} win rate")
        logger.info(f"   Total P/L: ${best_wr_volume['total_pl']:.2f}")
    
    # Best ROI
    results_df['roi'] = results_df['total_pl'] / results_df['trades']
    best_roi = results_df.iloc[results_df['roi'].idxmax()]
    logger.info(f"\n4. BEST ROI (profit per trade):")
    logger.info(f"   {best_roi['model']} @ threshold {best_roi['threshold']}")
    logger.info(f"   {best_roi['trades']:.0f} trades, ${best_roi['roi']:.2f} per trade")
    logger.info(f"   Total P/L: ${best_roi['total_pl']:.2f}")
    
    # Projection to full dataset
    logger.info("\n" + "="*100)
    logger.info(f"PROJECTION TO FULL DATASET ({total_games} games)")
    logger.info("="*100)
    
    scale_factor = total_games / len(test_games)
    
    logger.info(f"\nBest Strategy ({best_pl['model']} @ {best_pl['threshold']}):")
    logger.info(f"  Expected trades: {best_pl['trades'] * scale_factor:.0f}")
    logger.info(f"  Expected P/L: ${best_pl['total_pl'] * scale_factor:.2f}")
    logger.info(f"  Trade frequency: {best_pl['trade_frequency']:.2f} per game")
    
    logger.info("="*100)


if __name__ == "__main__":
    test_trade_frequency()

