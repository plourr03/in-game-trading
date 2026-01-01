"""
Test LightGBM model in actual trading backtest
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


class LightGBMStrategy:
    """Trading strategy using LightGBM model"""
    
    def __init__(self):
        self.model = joblib.load('ml_models/outputs/best_entry_model.pkl')
        self.scaler = joblib.load('ml_models/outputs/best_entry_scaler.pkl')
        self.features = joblib.load('ml_models/outputs/best_entry_features.pkl')
    
    def calculate_features(self, df, idx):
        """Calculate features for prediction"""
        features = {}
        
        features['current_price'] = df.iloc[idx]['close']
        features['spread'] = df.iloc[idx]['high'] - df.iloc[idx]['low']
        features['volume'] = df.iloc[idx]['volume']
        features['time_remaining'] = df.iloc[idx]['time_remaining']
        features['period'] = df.iloc[idx]['period']
        features['score_diff'] = df.iloc[idx].get('score_diff', 0)
        features['score_diff_abs'] = abs(features['score_diff'])
        features['scoring_rate_3min'] = df.iloc[idx].get('scoring_rate_3min', 0)
        features['score_momentum'] = df.iloc[idx].get('score_momentum', 0)
        features['lead_extending'] = df.iloc[idx].get('lead_extending', 0)
        
        # Price moves
        if idx >= 1:
            features['price_move_1min'] = (df.iloc[idx]['close'] - df.iloc[idx-1]['close']) / df.iloc[idx-1]['close'] * 100
        else:
            features['price_move_1min'] = 0
        
        if idx >= 3:
            features['price_move_3min'] = (df.iloc[idx]['close'] - df.iloc[idx-3]['close']) / df.iloc[idx-3]['close'] * 100
        else:
            features['price_move_3min'] = 0
        
        if idx >= 5:
            features['price_move_5min'] = (df.iloc[idx]['close'] - df.iloc[idx-5]['close']) / df.iloc[idx-5]['close'] * 100
            features['volatility_5min'] = df.iloc[idx-4:idx+1]['close'].std()
            features['volume_ma5'] = df.iloc[idx-4:idx+1]['volume'].mean()
        else:
            features['price_move_5min'] = 0
            features['volatility_5min'] = 0
            features['volume_ma5'] = features['volume']
        
        features['volume_spike'] = features['volume'] / (features['volume_ma5'] + 1e-6)
        
        # Binary features
        features['is_extreme_low'] = 1 if features['current_price'] <= 10 else 0
        features['is_extreme_high'] = 1 if features['current_price'] >= 90 else 0
        features['is_extreme_price'] = features['is_extreme_low'] or features['is_extreme_high']
        features['is_mid_price'] = 1 if 40 < features['current_price'] < 60 else 0
        features['is_close_game'] = 1 if features['score_diff_abs'] <= 5 else 0
        features['is_late_game'] = 1 if features['time_remaining'] <= 5 else 0
        features['is_very_late'] = 1 if features['time_remaining'] <= 2 else 0
        features['large_move'] = 1 if abs(features['price_move_1min']) > 5 else 0
        features['huge_move'] = 1 if abs(features['price_move_1min']) > 10 else 0
        
        return features
    
    def should_enter(self, features, threshold=0.5):
        """Predict if should enter trade"""
        X = np.array([[features[f] for f in self.features]])
        prob = self.model.predict_proba(X)[0, 1]
        return prob >= threshold, prob


def backtest_lightgbm():
    """Backtest LightGBM strategy at different thresholds"""
    
    logger.info("="*100)
    logger.info("BACKTESTING LIGHTGBM STRATEGY")
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
    
    # Test different thresholds
    thresholds = [0.6, 0.7, 0.8, 0.85, 0.9]
    strategy = LightGBMStrategy()
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
                    features = strategy.calculate_features(game_df, idx)
                    should_enter, confidence = strategy.should_enter(features, threshold=threshold)
                    
                    if should_enter:
                        position = {
                            'entry_idx': idx,
                            'entry_price': game_df.iloc[idx]['close'],
                            'hold_period': 7,  # Default hold
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
    logger.info("LIGHTGBM BACKTEST RESULTS")
    logger.info("="*100)
    
    results_df = pd.DataFrame(results)
    print()
    print(results_df.to_string(index=False))
    
    # Find best
    logger.info("\n" + "="*100)
    best_idx = results_df['total_pl'].idxmax()
    best = results_df.iloc[best_idx]
    logger.info(f"BEST THRESHOLD: {best['threshold']}")
    logger.info(f"  Trades: {best['trades']:.0f}")
    logger.info(f"  Win Rate: {best['win_rate']:.1%}")
    logger.info(f"  Total P/L: ${best['total_pl']:.2f}")
    logger.info(f"  Avg P/L: ${best['avg_pl']:.2f}")
    logger.info("="*100)


if __name__ == "__main__":
    backtest_lightgbm()





