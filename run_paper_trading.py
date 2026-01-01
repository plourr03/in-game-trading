"""
Paper Trading System - Multi-Game Monitor
Monitors multiple games simultaneously and logs all trading signals
Does NOT execute real trades - only logs what would have happened
"""
import time
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
import joblib
from typing import Dict, List

sys.path.insert(0, os.getcwd())

from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials
from src.data.realtime_pbp import RealTimePBPFetcher
from src.backtesting.fees import calculate_kalshi_fees
from src.paper_trading.database_logger import PaperTradingDB


class PaperTradingSystem:
    """Paper trading system for ML model - multi-game monitoring"""
    
    def __init__(self, games: List[Dict]):
        """
        Args:
            games: List of dicts with 'game_id', 'away', 'home', 'start_time'
        """
        self.games = games
        self.kalshi = None
        self.pbp_fetcher = RealTimePBPFetcher()
        self.db = PaperTradingDB()  # Database logger
        
        # ML Models
        self.entry_model = None
        self.exit_model = None
        self.features_list = None
        
        # Tracking
        self.price_history = {}  # game_id -> list of data points
        self.signals = []  # All signals generated
        self.open_positions = {}  # game_id -> list of positions
        self.closed_trades = []  # Completed trades
        self.game_status = {}  # game_id -> status ('not_started', 'active', 'ended')
        
        # Config
        self.entry_threshold = 0.60
        self.contracts_per_trade = 500
        self.poll_interval = 60  # seconds
        self.min_data_points = 15  # Need 15 minutes before trading
        
        # Logging
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.signal_log = f"paper_signals_{timestamp}.csv"
        self.trade_log = f"paper_trades_{timestamp}.csv"
        self.price_log = f"paper_prices_{timestamp}.csv"
        
    def initialize(self):
        """Initialize APIs and models"""
        print("="*80)
        print("INITIALIZING PAPER TRADING SYSTEM")
        print("="*80)
        
        # Load Kalshi API
        print("\n[1/3] Loading Kalshi API...")
        api_key, private_key = load_kalshi_credentials()
        self.kalshi = KalshiAPIClient(api_key, private_key)
        print("  [OK] Kalshi API ready")
        
        # Load ML models
        print("\n[2/3] Loading ML models...")
        try:
            self.entry_model = joblib.load('ml_models/outputs/advanced_model.pkl')
            self.exit_model = joblib.load('ml_models/outputs/exit_timing_model.pkl')
            self.features_list = joblib.load('ml_models/outputs/advanced_features.pkl')
            print(f"  [OK] Models loaded ({len(self.features_list)} features)")
            print(f"  [OK] ML predictions ENABLED - Entry threshold: {self.entry_threshold:.0%}")
            self.ml_enabled = True
        except Exception as e:
            print(f"  [ERROR] Failed to load models: {e}")
            print(f"  [WARNING] ML predictions DISABLED - monitoring only")
            self.ml_enabled = False
            return False
        
        # Find tickers for all games
        print("\n[3/3] Finding Kalshi tickers for games...")
        for game in self.games:
            markets = self.kalshi.find_nba_markets(game['away'], game['home'])
            if not markets:
                print(f"  [WARNING] No market for {game['away']}@{game['home']}")
                game['ticker'] = None
                continue
            
            # Find home team winning ticker
            ticker = None
            for m in markets:
                if game['home'].upper() in m['ticker']:
                    ticker = m['ticker']
                    break
            if not ticker:
                ticker = markets[0]['ticker']
            
            game['ticker'] = ticker
            print(f"  [OK] {game['away']}@{game['home']}: {ticker}")
        
        print("\n" + "="*80)
        print("[OK] INITIALIZATION COMPLETE")
        print("="*80 + "\n")
        
        # Start database session
        active_games = len([g for g in self.games if g['ticker']])
        self.db.start_session(active_games, f"Paper trading - {active_games} games")
        print(f"[DB] Session started: session_id = {self.db.session_id}\n")
        
        return True
    
    def fetch_game_data(self, game):
        """Fetch current price and PBP data for a game"""
        game_id = game['game_id']
        ticker = game['ticker']
        
        if not ticker:
            return None, None
        
        # Fetch price
        try:
            price_data = self.kalshi.get_live_price(ticker)
            if not price_data or price_data['mid'] is None:
                return None, None
        except Exception as e:
            print(f"      [ERROR] Price fetch failed: {e}")
            return None, None
        
        # Fetch PBP
        try:
            pbp_data = self.pbp_fetcher.fetch_game_pbp(game_id)
            if not pbp_data:
                return price_data, None
        except Exception as e:
            print(f"      [ERROR] PBP fetch failed: {e}")
            return price_data, None
        
        return price_data, pbp_data
    
    def calculate_features(self, game_id):
        """Calculate all 70 features from historical data"""
        if game_id not in self.price_history:
            return None
        
        data_points = len(self.price_history[game_id])
        if data_points < self.min_data_points:
            print(f"    [ML] Warming up... {data_points}/{self.min_data_points} data points")
            return None
        
        df = pd.DataFrame(self.price_history[game_id])
        current_idx = len(df) - 1
        current = df.iloc[current_idx]
        
        features = {}
        
        # Basic price features
        features['current_price'] = current['mid']
        features['close'] = current['mid']
        features['open'] = df.iloc[0]['mid']
        features['high'] = df['mid'].max()
        features['low'] = df['mid'].min()
        features['spread'] = features['high'] - features['low']
        features['volume'] = 0
        
        # Price movements
        prices = df['mid'].values
        if len(prices) >= 2:
            features['price_move_1min'] = ((prices[-1] - prices[-2]) / prices[-2] * 100) if prices[-2] > 0 else 0
        if len(prices) >= 3:
            features['price_move_2min'] = ((prices[-1] - prices[-3]) / prices[-3] * 100) if prices[-3] > 0 else 0
        if len(prices) >= 4:
            features['price_move_3min'] = ((prices[-1] - prices[-4]) / prices[-4] * 100) if prices[-4] > 0 else 0
        if len(prices) >= 6:
            features['price_move_5min'] = ((prices[-1] - prices[-6]) / prices[-6] * 100) if prices[-6] > 0 else 0
        if len(prices) >= 11:
            features['price_move_10min'] = ((prices[-1] - prices[-11]) / prices[-11] * 100) if prices[-11] > 0 else 0
        
        # Volatility
        if len(prices) >= 3:
            features['volatility_3min'] = np.std(prices[-3:])
        if len(prices) >= 5:
            features['volatility_5min'] = np.std(prices[-5:])
        if len(prices) >= 10:
            features['volatility_10min'] = np.std(prices[-10:])
        
        # Volume (all 0)
        features['volume_ma3'] = 0
        features['volume_ma5'] = 0
        features['volume_ma10'] = 0
        features['volume_spike'] = 0
        features['volume_trend'] = 0
        
        # Score features
        score_home = current['score_home']
        score_away = current['score_away']
        
        features['score_home'] = score_home
        features['score_away'] = score_away
        features['score_diff'] = score_home - score_away
        features['score_diff_abs'] = abs(features['score_diff'])
        features['score_total'] = score_home + score_away
        
        # Score movements
        scores_home = df['score_home'].values
        scores_away = df['score_away'].values
        
        if len(scores_home) >= 2:
            features['score_diff_1min'] = (score_home - score_away) - (scores_home[-2] - scores_away[-2])
            features['scoring_rate_1min'] = (score_home + score_away) - (scores_home[-2] + scores_away[-2])
        
        if len(scores_home) >= 4:
            features['score_diff_3min'] = (score_home - score_away) - (scores_home[-4] - scores_away[-4])
            features['scoring_rate_3min'] = ((score_home + score_away) - (scores_home[-4] + scores_away[-4])) / 3
            features['home_momentum_3min'] = score_home - scores_home[-4]
            features['away_momentum_3min'] = score_away - scores_away[-4]
        
        if len(scores_home) >= 6:
            features['score_diff_5min'] = (score_home - score_away) - (scores_home[-6] - scores_away[-6])
            features['scoring_rate_5min'] = ((score_home + score_away) - (scores_home[-6] + scores_away[-6])) / 5
            features['home_momentum_5min'] = score_home - scores_home[-6]
            features['away_momentum_5min'] = score_away - scores_away[-6]
        
        # Game state
        game_minute = current.get('game_minute', 0)
        period = int(current.get('period', 1))
        
        features['time_remaining'] = 48 - game_minute
        features['period'] = period
        features['minutes_into_period'] = game_minute % 12
        
        features['is_period_1'] = 1 if period == 1 else 0
        features['is_period_2'] = 1 if period == 2 else 0
        features['is_period_3'] = 1 if period == 3 else 0
        features['is_period_4'] = 1 if period == 4 else 0
        features['is_early_period'] = 1 if features['minutes_into_period'] <= 3 else 0
        features['is_late_period'] = 1 if features['minutes_into_period'] >= 9 else 0
        
        features['is_close_game'] = 1 if features['score_diff_abs'] <= 5 else 0
        features['is_very_close'] = 1 if features['score_diff_abs'] <= 3 else 0
        features['is_blowout'] = 1 if features['score_diff_abs'] >= 15 else 0
        features['is_late_game'] = 1 if features['time_remaining'] <= 5 else 0
        features['is_very_late'] = 1 if features['time_remaining'] <= 2 else 0
        features['is_crunch_time'] = 1 if (features['time_remaining'] <= 5 and features['score_diff_abs'] <= 5) else 0
        
        features['is_extreme_low'] = 1 if current['mid'] <= 10 else 0
        features['is_extreme_high'] = 1 if current['mid'] >= 90 else 0
        features['is_extreme_price'] = features['is_extreme_low'] or features['is_extreme_high']
        features['is_mid_price'] = 1 if (40 < current['mid'] < 60) else 0
        
        if 'price_move_1min' in features:
            features['large_move'] = 1 if abs(features['price_move_1min']) > 5 else 0
            features['huge_move'] = 1 if abs(features['price_move_1min']) > 10 else 0
        
        features['score_vs_expectation'] = features['score_total'] - (game_minute * 2.2)
        features['pace'] = features['score_total'] / (game_minute + 1) if game_minute > 0 else 0
        
        if len(prices) >= 5:
            features['price_range_5min'] = max(prices[-5:]) - min(prices[-5:])
        
        # Fill missing with 0
        for feat in self.features_list:
            if feat not in features:
                features[feat] = 0
        
        return features
    
    def generate_signal(self, game, game_id):
        """Generate trading signal"""
        if not self.ml_enabled:
            return None
            
        features_dict = self.calculate_features(game_id)
        
        if not features_dict:
            return None
        
        # Prepare feature vector
        X = pd.DataFrame([features_dict])
        X = X[self.features_list].fillna(0).replace([np.inf, -np.inf], 0)
        
        # Get prediction
        entry_prob = self.entry_model.predict_proba(X)[0, 1]
        
        # Debug: Show all predictions (not just signals)
        if entry_prob >= 0.40:  # Show if somewhat confident
            print(f"    [ML] Probability: {entry_prob:.1%} (threshold: {self.entry_threshold:.0%})")
        
        if entry_prob >= self.entry_threshold:
            exit_minutes = int(self.exit_model.predict(X)[0])
            current_data = self.price_history[game_id][-1]
            
            signal = {
                'timestamp': datetime.now(),
                'game_id': game_id,
                'away_team': game['away'],
                'home_team': game['home'],
                'action': 'BUY',
                'entry_price': current_data['mid'],
                'bid': current_data['bid'],
                'ask': current_data['ask'],
                'contracts': self.contracts_per_trade,
                'probability': float(entry_prob),
                'hold_minutes': exit_minutes,
                'score_home': current_data['score_home'],
                'score_away': current_data['score_away'],
                'period': current_data['period'],
                'game_minute': current_data['game_minute']
            }
            
            return signal
        
        return None
    
    def check_exits(self, game_id):
        """Check if any open positions should be closed"""
        if game_id not in self.open_positions:
            return []
        
        current_data = self.price_history[game_id][-1]
        current_minute = current_data['game_minute']
        exit_price = current_data['mid']
        period = current_data['period']
        score_home = current_data['score_home']
        score_away = current_data['score_away']
        
        exits = []
        
        for pos in self.open_positions[game_id][:]:
            # Check if it's time to exit based on ML model
            should_exit_time = current_minute >= pos['exit_minute']
            
            if should_exit_time:
                # HOLD TO EXPIRATION RULE:
                # Don't sell if outcome is nearly certain - better to collect full $1.00 payout
                # and avoid exit fees
                score_diff = abs(score_home - score_away)
                time_remaining = 48 - current_minute
                
                hold_to_expiration = (
                    period >= 4 and  # Q4
                    (time_remaining <= 6 or (period >= 4 and time_remaining <= 3)) and  # Late game
                    exit_price >= 95 and  # Price very high (nearly certain)
                    score_diff >= 11  # Big lead
                )
                
                if hold_to_expiration:
                    # Don't exit - hold to expiration
                    print(f"    [HOLD] Holding to expiration (Q{period}, price=${exit_price:.0f}c, diff={score_diff})")
                    continue
                
                # Calculate P/L for normal exit
                buy_fee = calculate_kalshi_fees(pos['contracts'], pos['entry_price'], is_taker=True)
                sell_fee = calculate_kalshi_fees(pos['contracts'], exit_price, is_taker=True)
                
                gross_profit_cents = (exit_price - pos['entry_price']) * pos['contracts']
                net_profit = (gross_profit_cents / 100) - buy_fee - sell_fee
                
                trade = {
                    'timestamp': datetime.now(),
                    'game_id': game_id,
                    'entry_minute': pos['entry_minute'],
                    'exit_minute': current_minute,
                    'entry_price': pos['entry_price'],
                    'exit_price': exit_price,
                    'contracts': pos['contracts'],
                    'gross_profit_cents': gross_profit_cents,
                    'buy_fee': buy_fee,
                    'sell_fee': sell_fee,
                    'net_profit': net_profit,
                    'probability': pos['probability'],
                    'won': net_profit > 0
                }
                
                exits.append(trade)
                self.closed_trades.append(trade)
                self.open_positions[game_id].remove(pos)
        
        return exits
    
    def log_signal(self, signal):
        """Log signal to CSV"""
        df = pd.DataFrame([signal])
        
        if not os.path.exists(self.signal_log):
            df.to_csv(self.signal_log, index=False)
        else:
            df.to_csv(self.signal_log, mode='a', header=False, index=False)
    
    def log_trade(self, trade):
        """Log completed trade to CSV"""
        df = pd.DataFrame([trade])
        
        if not os.path.exists(self.trade_log):
            df.to_csv(self.trade_log, index=False)
        else:
            df.to_csv(self.trade_log, mode='a', header=False, index=False)
    
    def log_price_data(self, data_points):
        """Log all price data"""
        df = pd.DataFrame(data_points)
        df.to_csv(self.price_log, index=False)
    
    def _calculate_game_minute(self, period, clock_str):
        """Calculate game minute from period and clock"""
        try:
            clock_str = clock_str.replace('PT', '').replace('S', '')
            if 'M' in clock_str:
                parts = clock_str.split('M')
                minutes = int(parts[0])
                seconds = float(parts[1]) if len(parts) > 1 else 0
            else:
                minutes = 0
                seconds = float(clock_str)
            
            seconds_left = minutes * 60 + seconds
            minutes_into_period = 12 - (seconds_left / 60)
            game_minute = (period - 1) * 12 + minutes_into_period
            
            return game_minute
        except:
            return 0
    
    def run(self, duration_minutes=180):
        """Run paper trading"""
        print("\n" + "="*80)
        print("STARTING PAPER TRADING SESSION")
        print("="*80)
        print(f"Duration: {duration_minutes} minutes ({duration_minutes/60:.1f} hours)")
        print(f"Poll Interval: {self.poll_interval} seconds")
        print(f"Games: {len([g for g in self.games if g['ticker']])} active")
        print(f"Entry Threshold: {self.entry_threshold:.0%}")
        print("="*80 + "\n")
        
        start_time = time.time()
        iteration = 0
        
        try:
            while time.time() - start_time < duration_minutes * 60:
                iteration += 1
                now = datetime.now().strftime('%H:%M:%S')
                print(f"\n[Iteration {iteration}] {now}")
                print("-" * 80)
                
                # Poll each game
                for game in self.games:
                    if not game['ticker']:
                        continue
                    
                    game_id = game['game_id']
                    
                    # Initialize game status if not set
                    if game_id not in self.game_status:
                        self.game_status[game_id] = 'not_started'
                    
                    # Check if game has started based on status
                    game_status_code = game.get('game_status', 1)
                    
                    # Skip games that already ended (status = 3)
                    if game_status_code == 3:
                        if self.game_status[game_id] != 'ended':
                            self.game_status[game_id] = 'ended'
                            print(f"  {game['away']}@{game['home']}: [GAME ALREADY FINISHED]")
                        continue
                    
                    # Skip games we've already marked as ended
                    if self.game_status[game_id] == 'ended':
                        continue
                    
                    # If game hasn't started yet (status = 1), check if it already finished
                    if game_status_code == 1 and self.game_status[game_id] == 'not_started':
                        # Check start time if available
                        start_time_utc = game.get('start_time_utc')
                        game_already_finished = False
                        game_should_have_started = False
                        
                        if start_time_utc:
                            try:
                                start_dt = datetime.fromisoformat(start_time_utc.replace('Z', '+00:00'))
                                now_dt = datetime.now(start_dt.tzinfo)
                                
                                time_since_start = (now_dt - start_dt).total_seconds() / 60
                                
                                if time_since_start > 120:
                                    # Game started more than 2 hours ago but no data
                                    game_already_finished = True
                                    self.game_status[game_id] = 'ended'
                                    print(f"  {game['away']}@{game['home']}: Game already finished (started {time_since_start/60:.1f}h ago)")
                                elif now_dt < start_dt:
                                    # Game hasn't started yet
                                    time_until = (start_dt - now_dt).total_seconds() / 60
                                    print(f"  {game['away']}@{game['home']}: Starts in {time_until:.0f} minutes")
                                    continue
                                else:
                                    # Game should have started (within last 2 hours)
                                    game_should_have_started = True
                            except Exception as e:
                                pass
                        
                        if game_already_finished:
                            continue
                        
                        # Only mark as finished if:
                        # 1. Game should have started (past start time)
                        # 2. We've tried multiple times (iteration > 5)
                        # 3. Still no data
                        if game_should_have_started and iteration > 5:
                            if game_id not in self.price_history or len(self.price_history.get(game_id, [])) == 0:
                                self.game_status[game_id] = 'ended'
                                print(f"  {game['away']}@{game['home']}: No data available (game may have been postponed/cancelled)")
                                continue
                        
                        # Game genuinely not started yet
                        print(f"  {game['away']}@{game['home']}: Game not started yet")
                        continue
                    
                    # Fetch data
                    price_data, pbp_data = self.fetch_game_data(game)
                    
                    # Check if game hasn't started yet
                    if not price_data or not pbp_data:
                        if self.game_status[game_id] == 'not_started':
                            print(f"  {game['away']}@{game['home']}: Game not started yet")
                        else:
                            print(f"  {game['away']}@{game['home']}: Waiting for data...")
                        continue
                    
                    # Extract game state
                    actions = pbp_data['game']['actions']
                    
                    # Skip if no actions (game ended or data issue)
                    if not actions or len(actions) == 0:
                        if self.game_status[game_id] != 'ended':
                            self.game_status[game_id] = 'ended'
                            print(f"  {game['away']}@{game['home']}: [GAME ENDED]")
                        else:
                            print(f"  {game['away']}@{game['home']}: Game has ended")
                        continue
                    
                    latest = actions[-1]
                    
                    # Check if game just ended (be careful - could be overtime!)
                    action_type = latest.get('actionType', '')
                    description = latest.get('description', '').lower()
                    period = latest.get('period', 0)
                    
                    # Game only truly ends if:
                    # 1. We see "game end" explicitly, OR
                    # 2. Period ended AND scores are not tied (no OT)
                    is_game_end = False
                    
                    if 'game end' in description and 'period end' not in description:
                        # Explicit game end
                        is_game_end = True
                    elif action_type == 'game end':
                        is_game_end = True
                    
                    if is_game_end:
                        if self.game_status[game_id] != 'ended':
                            self.game_status[game_id] = 'ended'
                            
                            # Get current game state for final stats
                            score_home = int(latest.get('scoreHome', 0))
                            score_away = int(latest.get('scoreAway', 0))
                            period = latest.get('period', 4)
                            clock = latest.get('clock', 'PT00M00.00S')
                            game_minute = self._calculate_game_minute(period, clock)
                            
                            # Close all open positions for this game at expiration ($1.00)
                            if game_id in self.open_positions and len(self.open_positions[game_id]) > 0:
                                print(f"  {game['away']}@{game['home']}: [GAME ENDED] - Settling {len(self.open_positions[game_id])} position(s) at expiration")
                                
                                for pos in self.open_positions[game_id][:]:
                                    # Settle at $1.00 (100 cents)
                                    expiration_price = 100
                                    
                                    buy_fee = calculate_kalshi_fees(pos['contracts'], pos['entry_price'], is_taker=True)
                                    # No sell fee at expiration - Kalshi pays out automatically
                                    
                                    gross_profit_cents = (expiration_price - pos['entry_price']) * pos['contracts']
                                    net_profit = (gross_profit_cents / 100) - buy_fee  # Only entry fee
                                    
                                    trade = {
                                        'timestamp': datetime.now(),
                                        'game_id': game_id,
                                        'entry_minute': pos['entry_minute'],
                                        'exit_minute': game_minute,
                                        'entry_price': pos['entry_price'],
                                        'exit_price': expiration_price,
                                        'contracts': pos['contracts'],
                                        'gross_profit_cents': gross_profit_cents,
                                        'buy_fee': buy_fee,
                                        'sell_fee': 0,  # No sell fee at expiration
                                        'net_profit': net_profit,
                                        'probability': pos['probability'],
                                        'won': net_profit > 0,
                                        'held_to_expiration': True
                                    }
                                    
                                    print(f"    [EXPIRATION] Settled at $1.00 -> P/L: ${trade['net_profit']:+.2f} (saved exit fees!)")
                                    self.closed_trades.append(trade)
                                    self.log_trade(trade)
                                    
                                    # Log to database
                                    try:
                                        db_trade = trade.copy()
                                        db_trade['entry_score_home'] = pos.get('entry_score_home', score_home)
                                        db_trade['entry_score_away'] = pos.get('entry_score_away', score_away)
                                        db_trade['exit_score_home'] = score_home
                                        db_trade['exit_score_away'] = score_away
                                        db_trade['entry_timestamp'] = pos.get('entry_timestamp', datetime.now())
                                        db_trade['exit_timestamp'] = datetime.now()
                                        self.db.log_trade(db_trade)
                                    except Exception as e:
                                        pass
                                
                                self.open_positions[game_id] = []
                            else:
                                print(f"  {game['away']}@{game['home']}: [GAME ENDED]")
                        else:
                            print(f"  {game['away']}@{game['home']}: Game has ended")
                        continue
                    
                    # Mark game as active
                    if self.game_status[game_id] == 'not_started':
                        self.game_status[game_id] = 'active'
                        print(f"  {game['away']}@{game['home']}: [GAME STARTED]")
                    
                    score_home = int(latest.get('scoreHome', 0))
                    score_away = int(latest.get('scoreAway', 0))
                    period = latest.get('period', 0)
                    clock = latest.get('clock', '')
                    
                    game_minute = self._calculate_game_minute(period, clock)
                    
                    # Store data point
                    data_point = {
                        'timestamp': datetime.now(),
                        'game_id': game_id,
                        'mid': price_data['mid'],
                        'bid': price_data['bid'],
                        'ask': price_data['ask'],
                        'score_home': score_home,
                        'score_away': score_away,
                        'period': period,
                        'game_minute': game_minute
                    }
                    
                    if game_id not in self.price_history:
                        self.price_history[game_id] = []
                    self.price_history[game_id].append(data_point)
                    
                    # Log to database
                    try:
                        db_data = data_point.copy()
                        db_data['away_team'] = game['away']
                        db_data['home_team'] = game['home']
                        db_data['ticker'] = game['ticker']
                        self.db.log_price_data(db_data)
                    except Exception as e:
                        pass  # Don't let DB errors stop trading
                    
                    # Display status
                    score_diff = score_home - score_away
                    data_points = len(self.price_history[game_id])
                    print(f"  {game['away']}@{game['home']}: Q{period} | {score_away}-{score_home} (diff:{score_diff:+d}) | ${price_data['mid']:.0f}c | {data_points} pts")
                    
                    # Display last action
                    last_action_desc = latest.get('description', '')
                    
                    # Don't show "Game End" or "Period End" as actions - we already handled those
                    if last_action_desc and 'end' not in last_action_desc.lower():
                        # Truncate if too long
                        if len(last_action_desc) > 70:
                            last_action_desc = last_action_desc[:67] + "..."
                        print(f"    Last: {last_action_desc}")
                    
                    # Check exits first
                    exits = self.check_exits(game_id)
                    for trade in exits:
                        status = "WIN" if trade['won'] else "LOSS"
                        print(f"    [{status}] Exit at ${trade['exit_price']:.0f}c -> P/L: ${trade['net_profit']:+.2f}")
                        self.log_trade(trade)
                        
                        # Log to database
                        try:
                            db_trade = trade.copy()
                            db_trade['entry_score_home'] = trade.get('entry_score_home', score_home)
                            db_trade['entry_score_away'] = trade.get('entry_score_away', score_away)
                            db_trade['exit_score_home'] = score_home
                            db_trade['exit_score_away'] = score_away
                            db_trade['entry_timestamp'] = trade.get('entry_timestamp', datetime.now())
                            db_trade['exit_timestamp'] = datetime.now()
                            self.db.log_trade(db_trade)
                        except Exception as e:
                            pass
                    
                    # Generate signal
                    signal = self.generate_signal(game, game_id)
                    
                    if signal:
                        print(f"    [SIGNAL] BUY ${signal['entry_price']:.0f}c (prob={signal['probability']:.1%}, hold={signal['hold_minutes']}min)")
                        self.signals.append(signal)
                        self.log_signal(signal)
                        
                        # Log to database
                        try:
                            db_signal = signal.copy()
                            db_signal['ticker'] = game['ticker']
                            signal_id = self.db.log_signal(db_signal)
                        except Exception as e:
                            pass
                        
                        # Open position
                        position = {
                            'entry_minute': game_minute,
                            'exit_minute': game_minute + signal['hold_minutes'],
                            'entry_price': signal['entry_price'],
                            'contracts': signal['contracts'],
                            'probability': signal['probability']
                        }
                        
                        if game_id not in self.open_positions:
                            self.open_positions[game_id] = []
                        self.open_positions[game_id].append(position)
                
                # Summary
                total_open = sum(len(positions) for positions in self.open_positions.values())
                if total_open > 0:
                    print(f"\n  Open positions: {total_open}")
                
                # Check if all games have ended
                all_games_ended = all(
                    self.game_status.get(g['game_id'], 'not_started') == 'ended' 
                    for g in self.games if g['ticker']
                )
                
                if all_games_ended:
                    print("\n[INFO] All games have ended - will finish this session")
                    break
                
                # Wait
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            print("\n\n[OK] Paper trading stopped by user")
        
        # Check if all games ended naturally
        all_games_ended = all(
            self.game_status.get(g['game_id'], 'not_started') == 'ended' 
            for g in self.games if g['ticker']
        )
        
        if all_games_ended:
            print("\n[OK] All games have ended - stopping paper trading")
        
        # Final summary
        elapsed = (time.time() - start_time) / 60
        print("\n" + "="*80)
        print("SESSION COMPLETE")
        print("="*80)
        print(f"Duration: {elapsed:.1f} minutes")
        print(f"Signals Generated: {len(self.signals)}")
        print(f"Trades Completed: {len(self.closed_trades)}")
        
        if self.closed_trades:
            total_pl = sum(t['net_profit'] for t in self.closed_trades)
            wins = sum(1 for t in self.closed_trades if t['won'])
            win_rate = wins / len(self.closed_trades)
            held_to_expiration = sum(1 for t in self.closed_trades if t.get('held_to_expiration', False))
            
            print(f"Win Rate: {win_rate:.1%}")
            print(f"Total P/L: ${total_pl:+,.2f}")
            print(f"Avg P/L: ${total_pl/len(self.closed_trades):+.2f}")
            
            if held_to_expiration > 0:
                print(f"\nHold-to-Expiration:")
                print(f"  Positions held: {held_to_expiration}")
                print(f"  Exit fees saved: ~${held_to_expiration * 3.50:.2f}")
            
            # Update database session
            try:
                self.db.end_session(len(self.signals), len(self.closed_trades), total_pl, win_rate)
            except Exception as e:
                print(f"[WARNING] Could not update database: {e}")
        
        print(f"\nLogs saved:")
        print(f"  Signals: {self.signal_log}")
        print(f"  Trades: {self.trade_log}")
        
        # Save price data
        all_prices = []
        for game_id, prices in self.price_history.items():
            all_prices.extend(prices)
        if all_prices:
            self.log_price_data(all_prices)
            print(f"  Prices: {self.price_log}")
        
        print(f"\nDatabase:")
        print(f"  Session ID: {self.db.session_id}")
        print(f"  View results: python view_paper_trading.py")
        
        print("="*80)


def get_todays_games():
    """Get tonight's games with start times"""
    from nba_api.live.nba.endpoints import scoreboard
    from datetime import timezone
    
    try:
        games_data = scoreboard.ScoreBoard().get_dict()
        games = []
        
        for g in games_data['scoreboard']['games']:
            # Parse start time
            start_time_utc = g.get('gameTimeUTC', None)
            
            game = {
                'game_id': g['gameId'],
                'away': g['awayTeam']['teamTricode'],
                'home': g['homeTeam']['teamTricode'],
                'start_time_utc': start_time_utc,
                'game_status': g.get('gameStatus', 1),  # 1=not started, 2=in progress, 3=ended
                'ticker': None
            }
            games.append(game)
        
        return games
    except Exception as e:
        print(f"Error fetching games: {e}")
        return []


if __name__ == "__main__":
    print("\nFetching today's games...")
    games = get_todays_games()
    
    if not games:
        print("[ERROR] No games found")
    else:
        print(f"\nFound {len(games)} games:")
        for g in games:
            start_info = ""
            if g.get('start_time_utc'):
                try:
                    start_dt = datetime.fromisoformat(g['start_time_utc'].replace('Z', '+00:00'))
                    start_local = start_dt.astimezone()
                    start_info = f" - {start_local.strftime('%I:%M %p')}"
                except:
                    pass
            print(f"  {g['away']} @ {g['home']}{start_info}")
        
        print("\nInitializing paper trading system...")
        system = PaperTradingSystem(games)
        
        if system.initialize():
            print("\n[READY] Starting paper trading...")
            system.run(duration_minutes=360)  # 6 hours
        else:
            print("[ERROR] Initialization failed")

