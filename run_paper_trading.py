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
        except Exception as e:
            print(f"  [ERROR] Failed to load models: {e}")
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
        
        if len(self.price_history[game_id]) < self.min_data_points:
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
        features_dict = self.calculate_features(game_id)
        
        if not features_dict:
            return None
        
        # Prepare feature vector
        X = pd.DataFrame([features_dict])
        X = X[self.features_list].fillna(0).replace([np.inf, -np.inf], 0)
        
        # Get prediction
        entry_prob = self.entry_model.predict_proba(X)[0, 1]
        
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
        
        exits = []
        
        for pos in self.open_positions[game_id][:]:
            if current_minute >= pos['exit_minute']:
                # Calculate P/L
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
                    
                    # Fetch data
                    price_data, pbp_data = self.fetch_game_data(game)
                    
                    if not price_data or not pbp_data:
                        print(f"  {game['away']}@{game['home']}: Waiting for data...")
                        continue
                    
                    # Extract game state
                    actions = pbp_data['game']['actions']
                    latest = actions[-1]
                    
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
                
                # Wait
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            print("\n\n[OK] Paper trading stopped by user")
        
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
            
            print(f"Win Rate: {win_rate:.1%}")
            print(f"Total P/L: ${total_pl:+,.2f}")
            print(f"Avg P/L: ${total_pl/len(self.closed_trades):+.2f}")
            
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
    """Get tonight's games"""
    from nba_api.live.nba.endpoints import scoreboard
    
    try:
        games_data = scoreboard.ScoreBoard().get_dict()
        games = []
        
        for g in games_data['scoreboard']['games']:
            game = {
                'game_id': g['gameId'],
                'away': g['awayTeam']['teamTricode'],
                'home': g['homeTeam']['teamTricode'],
                'start_time': g.get('gameTimeUTC', 'Unknown'),
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
            print(f"  {g['away']} @ {g['home']}")
        
        print("\nInitializing paper trading system...")
        system = PaperTradingSystem(games)
        
        if system.initialize():
            print("\n[READY] Starting paper trading...")
            system.run(duration_minutes=180)  # 3 hours
        else:
            print("[ERROR] Initialization failed")

