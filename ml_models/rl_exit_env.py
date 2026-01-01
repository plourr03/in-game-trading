"""
Reinforcement Learning Environment for NBA Trading Exit Decisions

This environment uses the existing supervised learning entry model and focuses
on learning optimal exit timing through PPO reinforcement learning.
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import gym
import numpy as np
import pandas as pd
import joblib
from gym import spaces
from typing import Dict, List, Optional, Tuple
from src.backtesting.fees import calculate_kalshi_fees


class NBAExitEnv(gym.Env):
    """
    Gym environment for learning optimal exit timing in NBA trading.
    
    State Space (75 dimensions):
        - 70 features from entry model (price, score, game state)
        - 5 position features (entry price, current price, unrealized P/L, minutes held, has position)
    
    Action Space:
        - Discrete(2): [0=HOLD, 1=EXIT]
    
    Reward:
        - At exit: net P/L (after Kalshi fees)
        - Per step: small negative reward (-0.001 per minute held)
        - Bonus: +2 if exit near peak (≥90% of peak P/L)
    """
    
    metadata = {'render.modes': ['human']}
    
    def __init__(
        self,
        game_files: List[str],
        entry_threshold: float = 0.60,
        contracts: int = 500,
        max_hold_minutes: int = 30
    ):
        """
        Initialize the environment.
        
        Args:
            game_files: List of paths to game CSV files
            entry_threshold: Entry model probability threshold
            contracts: Number of contracts per trade
            max_hold_minutes: Maximum minutes to hold before forced exit
        """
        super(NBAExitEnv, self).__init__()
        
        self.game_files = game_files
        self.entry_threshold = entry_threshold
        self.contracts = contracts
        self.max_hold_minutes = max_hold_minutes
        
        # Load models
        self.entry_model = joblib.load('ml_models/outputs/advanced_model.pkl')
        self.features_list = joblib.load('ml_models/outputs/advanced_features.pkl')
        
        # State space: 70 entry features + 5 position features
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(75,),
            dtype=np.float32
        )
        
        # Action space: 0=HOLD, 1=EXIT
        self.action_space = spaces.Discrete(2)
        
        # Episode state
        self.current_game = None
        self.current_game_df = None
        self.current_minute = 0
        self.position = None
        self.episode_trades = []
        self.peak_pl = 0
        
    def reset(self) -> np.ndarray:
        """
        Reset environment to start a new episode (random game).
        
        Returns:
            Initial state observation
        """
        # Pick random game
        game_file = np.random.choice(self.game_files)
        self.current_game = game_file
        self.current_game_df = self._load_game_data(game_file)
        
        # Start at a random minute (between 10 and 30 to have history)
        self.current_minute = np.random.randint(10, min(30, len(self.current_game_df) - 10))
        
        self.position = None
        self.episode_trades = []
        self.peak_pl = 0
        
        return self._get_state()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one step in the environment.
        
        Args:
            action: 0=HOLD, 1=EXIT
            
        Returns:
            next_state, reward, done, info
        """
        reward = 0
        done = False
        info = {}
        
        # If no position, check if we should enter
        if self.position is None:
            if self._should_enter():
                entry_price = self._get_current_price()
                self.position = {
                    'entry_price': entry_price,
                    'entry_minute': self.current_minute,
                    'contracts': self.contracts,
                    'entry_features': self._get_current_features()
                }
                self.peak_pl = 0
                reward = -0.01  # Small penalty for opening (encourages selectivity)
                info['action_taken'] = 'ENTER'
            else:
                info['action_taken'] = 'NO_ENTRY'
        
        # If we have a position
        else:
            current_price = self._get_current_price()
            minutes_held = self.current_minute - self.position['entry_minute']
            
            # Update peak P/L
            unrealized_pl = self._calculate_unrealized_pl(current_price)
            self.peak_pl = max(self.peak_pl, unrealized_pl)
            
            # Execute action
            if action == 1:  # EXIT
                net_pl = self._calculate_pl(
                    self.position['entry_price'],
                    current_price,
                    self.position['contracts']
                )
                
                # Base reward is the net P/L
                reward = net_pl
                
                # Bonus for exiting near peak
                if net_pl > 0 and net_pl >= self.peak_pl * 0.9:
                    reward += 2  # Bonus for good timing
                
                # Record trade
                self.episode_trades.append({
                    'entry_minute': self.position['entry_minute'],
                    'exit_minute': self.current_minute,
                    'entry_price': self.position['entry_price'],
                    'exit_price': current_price,
                    'net_pl': net_pl,
                    'minutes_held': minutes_held
                })
                
                self.position = None
                self.peak_pl = 0
                info['action_taken'] = 'EXIT'
                info['pl'] = net_pl
                
            else:  # HOLD
                # Small holding cost (encourages decisive action)
                reward = -0.001 * minutes_held
                
                # Penalty for watching profit evaporate
                if self.peak_pl > 0 and unrealized_pl < self.peak_pl * 0.5:
                    reward -= 1  # Penalty for not exiting when ahead
                
                info['action_taken'] = 'HOLD'
                
                # Force exit if held too long
                if minutes_held >= self.max_hold_minutes:
                    net_pl = self._calculate_pl(
                        self.position['entry_price'],
                        current_price,
                        self.position['contracts']
                    )
                    reward = net_pl
                    self.episode_trades.append({
                        'entry_minute': self.position['entry_minute'],
                        'exit_minute': self.current_minute,
                        'entry_price': self.position['entry_price'],
                        'exit_price': current_price,
                        'net_pl': net_pl,
                        'minutes_held': minutes_held,
                        'forced_exit': True
                    })
                    self.position = None
                    info['action_taken'] = 'FORCED_EXIT'
        
        # Advance time
        self.current_minute += 1
        
        # Check if game ended
        if self.current_minute >= len(self.current_game_df) - 1:
            done = True
            
            # Force exit at game end if still holding
            if self.position is not None:
                expiration_price = 100  # Contracts settle at $1.00
                net_pl = self._calculate_pl_at_expiration(
                    self.position['entry_price'],
                    self.position['contracts']
                )
                reward = net_pl
                self.episode_trades.append({
                    'entry_minute': self.position['entry_minute'],
                    'exit_minute': self.current_minute,
                    'entry_price': self.position['entry_price'],
                    'exit_price': expiration_price,
                    'net_pl': net_pl,
                    'minutes_held': self.current_minute - self.position['entry_minute'],
                    'expiration': True
                })
                info['action_taken'] = 'EXPIRATION'
        
        next_state = self._get_state()
        info['total_trades'] = len(self.episode_trades)
        
        return next_state, reward, done, info
    
    def _load_game_data(self, game_file: str) -> pd.DataFrame:
        """Load and prepare game data from CSV."""
        df = pd.read_csv(game_file)
        
        # Ensure required columns exist
        required = ['game_minute', 'close', 'open', 'high', 'low', 'volume']
        for col in required:
            if col not in df.columns:
                if col == 'game_minute':
                    df['game_minute'] = range(len(df))
                else:
                    df[col] = 0
        
        # Add score columns if missing
        if 'score_home' not in df.columns:
            df['score_home'] = 0
        if 'score_away' not in df.columns:
            df['score_away'] = 0
        
        return df
    
    def _get_current_price(self) -> float:
        """Get current market price (mid price)."""
        if self.current_minute >= len(self.current_game_df):
            return self.current_game_df.iloc[-1]['close']
        return self.current_game_df.iloc[self.current_minute]['close']
    
    def _get_current_features(self) -> Dict:
        """Calculate all 70 features for current minute."""
        if self.current_minute < 10:
            # Not enough history - return zeros
            return {feat: 0.0 for feat in self.features_list}
        
        # Get data up to current minute
        data_so_far = self.current_game_df.iloc[:self.current_minute+1].copy()
        current = data_so_far.iloc[-1]
        
        features = {}
        
        # Basic price features
        features['current_price'] = current['close']
        features['close'] = current['close']
        features['open'] = data_so_far.iloc[0]['open']
        features['high'] = data_so_far['high'].max()
        features['low'] = data_so_far['low'].min()
        features['spread'] = features['high'] - features['low']
        features['volume'] = current['volume']
        
        # Price movements
        prices = data_so_far['close'].values
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
        
        # Volume features
        volumes = data_so_far['volume'].values
        if len(volumes) >= 3:
            features['volume_ma3'] = np.mean(volumes[-3:])
        if len(volumes) >= 5:
            features['volume_ma5'] = np.mean(volumes[-5:])
            features['volume_spike'] = volumes[-1] / (features['volume_ma5'] + 1e-6)
        if len(volumes) >= 10:
            features['volume_ma10'] = np.mean(volumes[-10:])
        if len(volumes) >= 6:
            features['volume_trend'] = ((volumes[-1] - volumes[-6]) / (volumes[-6] + 1e-6) * 100)
        
        # Score features
        score_home = current.get('score_home', 0)
        score_away = current.get('score_away', 0)
        
        features['score_home'] = score_home
        features['score_away'] = score_away
        features['score_diff'] = score_home - score_away
        features['score_diff_abs'] = abs(features['score_diff'])
        features['score_total'] = score_home + score_away
        
        # Game state
        game_minute = current.get('game_minute', 0)
        features['time_remaining'] = 48 - game_minute
        features['period'] = min(4, (game_minute // 12) + 1)
        features['minutes_into_period'] = game_minute % 12
        
        features['is_period_1'] = 1 if features['period'] == 1 else 0
        features['is_period_2'] = 1 if features['period'] == 2 else 0
        features['is_period_3'] = 1 if features['period'] == 3 else 0
        features['is_period_4'] = 1 if features['period'] == 4 else 0
        features['is_early_period'] = 1 if features['minutes_into_period'] <= 3 else 0
        features['is_late_period'] = 1 if features['minutes_into_period'] >= 9 else 0
        
        features['is_close_game'] = 1 if features['score_diff_abs'] <= 5 else 0
        features['is_very_close'] = 1 if features['score_diff_abs'] <= 3 else 0
        features['is_blowout'] = 1 if features['score_diff_abs'] >= 15 else 0
        features['is_late_game'] = 1 if features['time_remaining'] <= 5 else 0
        features['is_very_late'] = 1 if features['time_remaining'] <= 2 else 0
        features['is_crunch_time'] = 1 if (features['time_remaining'] <= 5 and features['score_diff_abs'] <= 5) else 0
        
        features['is_extreme_low'] = 1 if current['close'] <= 10 else 0
        features['is_extreme_high'] = 1 if current['close'] >= 90 else 0
        features['is_extreme_price'] = features['is_extreme_low'] or features['is_extreme_high']
        features['is_mid_price'] = 1 if (40 < current['close'] < 60) else 0
        
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
                features[feat] = 0.0
        
        return features
    
    def _get_state(self) -> np.ndarray:
        """
        Get current state observation (75 dimensions).
        
        Returns:
            State vector [70 entry features + 5 position features]
        """
        # Get entry features
        entry_features = self._get_current_features()
        entry_vector = np.array([entry_features.get(f, 0.0) for f in self.features_list], dtype=np.float32)
        
        # Get position features
        if self.position is not None:
            current_price = self._get_current_price()
            unrealized_pl = self._calculate_unrealized_pl(current_price)
            minutes_held = self.current_minute - self.position['entry_minute']
            
            position_vector = np.array([
                self.position['entry_price'],
                current_price,
                unrealized_pl,
                minutes_held,
                1.0  # has_position flag
            ], dtype=np.float32)
        else:
            position_vector = np.zeros(5, dtype=np.float32)
        
        # Combine
        state = np.concatenate([entry_vector, position_vector])
        return state
    
    def _should_enter(self) -> bool:
        """Check if we should enter a trade using the supervised entry model."""
        features = self._get_current_features()
        X = pd.DataFrame([features])
        X = X[self.features_list].fillna(0).replace([np.inf, -np.inf], 0)
        
        prob = self.entry_model.predict_proba(X)[0, 1]
        return prob >= self.entry_threshold
    
    def _calculate_unrealized_pl(self, current_price: float) -> float:
        """Calculate unrealized P/L in dollars."""
        if self.position is None:
            return 0.0
        
        price_diff = current_price - self.position['entry_price']
        gross_cents = price_diff * self.position['contracts']
        return gross_cents / 100  # Convert to dollars
    
    def _calculate_pl(self, entry_price: float, exit_price: float, contracts: int) -> float:
        """Calculate net P/L including Kalshi fees."""
        buy_fee = calculate_kalshi_fees(contracts, entry_price, is_taker=True)
        sell_fee = calculate_kalshi_fees(contracts, exit_price, is_taker=True)
        
        gross_profit_cents = (exit_price - entry_price) * contracts
        net_profit = (gross_profit_cents / 100) - buy_fee - sell_fee
        
        return net_profit
    
    def _calculate_pl_at_expiration(self, entry_price: float, contracts: int) -> float:
        """Calculate net P/L when holding to expiration (no exit fee)."""
        buy_fee = calculate_kalshi_fees(contracts, entry_price, is_taker=True)
        
        expiration_price = 100  # Contracts settle at $1.00
        gross_profit_cents = (expiration_price - entry_price) * contracts
        net_profit = (gross_profit_cents / 100) - buy_fee  # No sell fee at expiration
        
        return net_profit
    
    def render(self, mode='human'):
        """Render the environment (optional)."""
        if self.position is not None:
            current_price = self._get_current_price()
            unrealized_pl = self._calculate_unrealized_pl(current_price)
            minutes_held = self.current_minute - self.position['entry_minute']
            print(f"Minute {self.current_minute}: Position held for {minutes_held}min, "
                  f"Entry: ${self.position['entry_price']:.0f}, Current: ${current_price:.0f}, "
                  f"Unrealized P/L: ${unrealized_pl:+.2f}")
        else:
            print(f"Minute {self.current_minute}: No position")
    
    def get_episode_stats(self) -> Dict:
        """Get statistics for the current episode."""
        if len(self.episode_trades) == 0:
            return {
                'total_trades': 0,
                'total_pl': 0,
                'avg_pl': 0,
                'win_rate': 0,
                'avg_hold_time': 0
            }
        
        total_pl = sum(t['net_pl'] for t in self.episode_trades)
        wins = sum(1 for t in self.episode_trades if t['net_pl'] > 0)
        
        return {
            'total_trades': len(self.episode_trades),
            'total_pl': total_pl,
            'avg_pl': total_pl / len(self.episode_trades),
            'win_rate': wins / len(self.episode_trades),
            'avg_hold_time': np.mean([t['minutes_held'] for t in self.episode_trades])
        }

