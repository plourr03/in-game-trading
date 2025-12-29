"""
Backtest ML models vs rules-based strategies
"""
import pandas as pd
import numpy as np
import joblib
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
from src.backtesting.fees import calculate_kalshi_fees
from src.utils.helpers import get_logger

logger = get_logger(__name__)


class MLStrategy:
    """ML-based trading strategy"""
    
    def __init__(self):
        self.entry_model = joblib.load('ml_models/outputs/entry_model.pkl')
        self.entry_scaler = joblib.load('ml_models/outputs/entry_scaler.pkl')
        self.entry_features = joblib.load('ml_models/outputs/entry_features.pkl')
        
        try:
            self.hold_model = joblib.load('ml_models/outputs/hold_duration_model.pkl')
            self.hold_scaler = joblib.load('ml_models/outputs/hold_duration_scaler.pkl')
            self.hold_features = joblib.load('ml_models/outputs/hold_duration_features.pkl')
            self.has_hold_model = True
        except:
            self.has_hold_model = False
            self.default_hold = 7  # Default hold period
    
    def calculate_features(self, df, idx):
        """Calculate features for a single row"""
        features = {}
        
        # Current values
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
        X = np.array([[features[f] for f in self.entry_features]])
        X_scaled = self.entry_scaler.transform(X)
        
        if hasattr(self.entry_model, 'predict_proba'):
            prob = self.entry_model.predict_proba(X_scaled)[0, 1]
            return prob >= threshold, prob
        else:
            pred = self.entry_model.predict(X_scaled)[0]
            return pred == 1, pred
    
    def get_hold_period(self, features):
        """Predict optimal hold period"""
        if not self.has_hold_model:
            return self.default_hold
        
        X = np.array([[features[f] for f in self.hold_features]])
        X_scaled = self.hold_scaler.transform(X)
        hold = self.hold_model.predict(X_scaled)[0]
        
        return int(hold)


class RulesStrategy:
    """Rules-based mean reversion strategy"""
    
    def __init__(self, price_min, price_max, threshold, hold_period):
        self.price_min = price_min
        self.price_max = price_max
        self.threshold = threshold
        self.hold_period = hold_period
    
    def should_enter(self, df, idx):
        """Check if should enter based on rules"""
        if idx < 1:
            return False, 0
        
        current_price = df.iloc[idx]['close']
        prev_price = df.iloc[idx-1]['close']
        
        # Price in range?
        if not (self.price_min <= current_price <= self.price_max):
            return False, 0
        
        # Large move?
        price_change_pct = abs((current_price - prev_price) / prev_price * 100)
        if price_change_pct < self.threshold:
            return False, 0
        
        return True, 1
    
    def get_hold_period(self, features=None):
        """Return fixed hold period"""
        return self.hold_period


def backtest_strategy(df, strategy, strategy_name):
    """Run backtest for a strategy"""
    trades = []
    position = None
    
    for idx in range(len(df)):
        # Check if should enter
        if position is None:
            if isinstance(strategy, MLStrategy):
                features = strategy.calculate_features(df, idx)
                should_enter, confidence = strategy.should_enter(features)
                if should_enter:
                    hold_period = strategy.get_hold_period(features)
                    position = {
                        'entry_idx': idx,
                        'entry_price': df.iloc[idx]['close'],
                        'hold_period': hold_period,
                        'entry_time': idx,
                        'confidence': confidence
                    }
            else:  # RulesStrategy
                should_enter, _ = strategy.should_enter(df, idx)
                if should_enter:
                    position = {
                        'entry_idx': idx,
                        'entry_price': df.iloc[idx]['close'],
                        'hold_period': strategy.get_hold_period(),
                        'entry_time': idx
                    }
        
        # Check if should exit
        elif position is not None:
            time_in_trade = idx - position['entry_idx']
            
            if time_in_trade >= position['hold_period'] or idx == len(df) - 1:
                # Exit position
                exit_price = df.iloc[idx]['close']
                entry_price = position['entry_price']
                
                # Calculate P/L (mean reversion: fade the move)
                if idx >= 1:
                    prev_price = df.iloc[position['entry_idx']-1]['close'] if position['entry_idx'] > 0 else entry_price
                    price_move_direction = np.sign(entry_price - prev_price)
                else:
                    price_move_direction = 0
                
                # Calculate raw P/L
                if price_move_direction > 0:
                    raw_pl = entry_price - exit_price  # Short
                else:
                    raw_pl = exit_price - entry_price  # Long
                
                # Calculate fees
                entry_fee = calculate_kalshi_fees(100, entry_price, is_taker=True)
                exit_fee = calculate_kalshi_fees(100, exit_price, is_taker=True)
                total_fees = entry_fee + exit_fee
                
                # Net P/L
                net_pl = raw_pl - total_fees
                is_winner = net_pl > 0
                
                trades.append({
                    'entry_idx': position['entry_idx'],
                    'exit_idx': idx,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'hold_period': position['hold_period'],
                    'raw_pl': raw_pl,
                    'fees': total_fees,
                    'net_pl': net_pl,
                    'is_winner': is_winner,
                    'confidence': position.get('confidence', 1.0)
                })
                
                position = None
    
    return pd.DataFrame(trades)


def run_backtest_comparison():
    """Compare ML vs rules-based strategies"""
    logger.info("="*100)
    logger.info("ML vs RULES-BASED STRATEGY COMPARISON")
    logger.info("="*100)
    
    # Load data
    logger.info("\n[1/4] Loading data...")
    kalshi_df = load_kalshi_games()
    kalshi_df = fill_prices(kalshi_df)
    kalshi_df['datetime'] = pd.to_datetime(kalshi_df['datetime'])
    kalshi_df['game_minute'] = kalshi_df['datetime'].dt.hour * 60 + kalshi_df['datetime'].dt.minute
    
    # Add required features
    kalshi_df['time_remaining'] = kalshi_df.groupby('game_id')['game_minute'].transform('max') - kalshi_df['game_minute']
    kalshi_df['period'] = (kalshi_df['game_minute'] // 12 + 1).clip(upper=4)
    kalshi_df['score_diff'] = 0  # Placeholder
    
    logger.info(f"      Loaded {len(kalshi_df):,} rows from {kalshi_df['game_id'].nunique()} games")
    
    # Select test games (last 20% for out-of-sample testing)
    all_games = kalshi_df['game_id'].unique()
    split_idx = int(len(all_games) * 0.8)
    test_games = all_games[split_idx:][:20]  # Take 20 test games
    
    test_df = kalshi_df[kalshi_df['game_id'].isin(test_games)].copy()
    logger.info(f"      Testing on {len(test_games)} games ({len(test_df):,} rows)")
    
    # Initialize strategies
    logger.info("\n[2/4] Initializing strategies...")
    
    logger.info("      - ML Strategy (entry + hold duration models)")
    ml_strategy = MLStrategy()
    
    logger.info("      - Rules Strategy (1-5c, >20% move, 3min hold)")
    rules_strategy = RulesStrategy(price_min=1, price_max=5, threshold=20, hold_period=3)
    
    # Run backtests
    logger.info("\n[3/4] Running backtests...")
    
    logger.info("      - Backtesting ML strategy...")
    ml_trades = []
    for game_id in test_games:
        game_df = test_df[test_df['game_id'] == game_id].copy().reset_index(drop=True)
        game_trades = backtest_strategy(game_df, ml_strategy, 'ML')
        if len(game_trades) > 0:
            game_trades['game_id'] = game_id
            ml_trades.append(game_trades)
    
    ml_trades_df = pd.concat(ml_trades, ignore_index=True) if ml_trades else pd.DataFrame()
    logger.info(f"        ML trades: {len(ml_trades_df)}")
    
    logger.info("      - Backtesting rules strategy...")
    rules_trades = []
    for game_id in test_games:
        game_df = test_df[test_df['game_id'] == game_id].copy().reset_index(drop=True)
        game_trades = backtest_strategy(game_df, rules_strategy, 'Rules')
        if len(game_trades) > 0:
            game_trades['game_id'] = game_id
            rules_trades.append(game_trades)
    
    rules_trades_df = pd.concat(rules_trades, ignore_index=True) if rules_trades else pd.DataFrame()
    logger.info(f"        Rules trades: {len(rules_trades_df)}")
    
    # Calculate metrics
    logger.info("\n[4/4] Calculating performance metrics...")
    
    def calculate_metrics(trades_df):
        if len(trades_df) == 0:
            return {
                'trades': 0,
                'win_rate': 0,
                'avg_pl': 0,
                'total_pl': 0,
                'sharpe': 0,
                'avg_fees': 0
            }
        
        return {
            'trades': len(trades_df),
            'win_rate': trades_df['is_winner'].mean(),
            'avg_pl': trades_df['net_pl'].mean(),
            'total_pl': trades_df['net_pl'].sum(),
            'sharpe': trades_df['net_pl'].mean() / (trades_df['net_pl'].std() + 1e-6),
            'avg_fees': trades_df['fees'].mean()
        }
    
    ml_metrics = calculate_metrics(ml_trades_df)
    rules_metrics = calculate_metrics(rules_trades_df)
    
    # Display results
    logger.info("\n" + "="*100)
    logger.info("BACKTEST RESULTS")
    logger.info("="*100)
    
    logger.info(f"\n{'Metric':<20} {'ML Strategy':>20} {'Rules Strategy':>20} {'Difference':>20}")
    logger.info("-"*100)
    logger.info(f"{'Total Trades':<20} {ml_metrics['trades']:>20,} {rules_metrics['trades']:>20,} {ml_metrics['trades'] - rules_metrics['trades']:>+20,}")
    logger.info(f"{'Win Rate':<20} {ml_metrics['win_rate']:>19.1%} {rules_metrics['win_rate']:>19.1%} {ml_metrics['win_rate'] - rules_metrics['win_rate']:>+19.1%}")
    logger.info(f"{'Avg P/L per Trade':<20} ${ml_metrics['avg_pl']:>19.2f} ${rules_metrics['avg_pl']:>19.2f} ${ml_metrics['avg_pl'] - rules_metrics['avg_pl']:>+19.2f}")
    logger.info(f"{'Total P/L':<20} ${ml_metrics['total_pl']:>19.2f} ${rules_metrics['total_pl']:>19.2f} ${ml_metrics['total_pl'] - rules_metrics['total_pl']:>+19.2f}")
    logger.info(f"{'Sharpe Ratio':<20} {ml_metrics['sharpe']:>20.2f} {rules_metrics['sharpe']:>20.2f} {ml_metrics['sharpe'] - rules_metrics['sharpe']:>+20.2f}")
    logger.info(f"{'Avg Fees':<20} ${ml_metrics['avg_fees']:>19.2f} ${rules_metrics['avg_fees']:>19.2f} ${ml_metrics['avg_fees'] - rules_metrics['avg_fees']:>+19.2f}")
    
    # Verdict
    logger.info("\n" + "="*100)
    logger.info("VERDICT")
    logger.info("="*100)
    
    if ml_metrics['total_pl'] > rules_metrics['total_pl']:
        improvement = ((ml_metrics['total_pl'] - rules_metrics['total_pl']) / 
                      (abs(rules_metrics['total_pl']) + 1e-6) * 100)
        logger.info(f"\n SUCCESS! ML Strategy outperforms by ${ml_metrics['total_pl'] - rules_metrics['total_pl']:+.2f}")
        logger.info(f"  ({improvement:+.1f}% improvement)")
    elif ml_metrics['total_pl'] < rules_metrics['total_pl']:
        logger.info(f"\n  Rules strategy still better by ${rules_metrics['total_pl'] - ml_metrics['total_pl']:.2f}")
        logger.info("  ML needs more training or different features")
    else:
        logger.info("\n  Strategies perform equally")
    
    # Save results
    logger.info("\nSaving results...")
    if len(ml_trades_df) > 0:
        ml_trades_df.to_csv('ml_models/outputs/ml_backtest_trades.csv', index=False)
        logger.info("  - ml_backtest_trades.csv")
    if len(rules_trades_df) > 0:
        rules_trades_df.to_csv('ml_models/outputs/rules_backtest_trades.csv', index=False)
        logger.info("  - rules_backtest_trades.csv")
    
    logger.info("\n" + "="*100)


if __name__ == "__main__":
    run_backtest_comparison()

