"""
ML-based Signal Generator for Trading Engine

Uses trained ML models to generate buy/sell signals with optimized exit timing.
"""
import pandas as pd
import numpy as np
import joblib
import os
from typing import Dict, Optional, Tuple


class MLSignalGenerator:
    """Generate trading signals using ML models"""
    
    def __init__(self, model_dir='ml_models/outputs'):
        """
        Initialize ML signal generator
        
        Args:
            model_dir: Directory containing trained models
        """
        self.model_dir = model_dir
        
        # Model parameters
        self.entry_threshold = 0.60
        self.base_contracts = 500
        
        # Load models
        self._load_models()
        
    def _load_models(self):
        """Load trained ML models"""
        try:
            self.entry_model = joblib.load(os.path.join(self.model_dir, 'advanced_model.pkl'))
            self.exit_model = joblib.load(os.path.join(self.model_dir, 'exit_timing_model.pkl'))
            self.features = joblib.load(os.path.join(self.model_dir, 'advanced_features.pkl'))
            print(f"[OK] ML models loaded successfully", flush=True)
            print(f"  - Entry model: CatBoost (AUC: 0.948)", flush=True)
            print(f"  - Exit model: LightGBM", flush=True)
            print(f"  - Features: {len(self.features)}", flush=True)
        except Exception as e:
            print(f"[ERROR] Error loading ML models: {e}", flush=True)
            raise
    
    def generate_signal(self, game_data: pd.DataFrame, current_minute: int) -> Optional[Dict]:
        """
        Generate trading signal for current minute
        
        Args:
            game_data: DataFrame with game data up to current minute
            current_minute: Current game minute
            
        Returns:
            Signal dict with action, contracts, hold_time, probability, or None
        """
        # Get current row
        current_data = game_data[game_data['game_minute'] == current_minute]
        
        if len(current_data) == 0:
            return None
        
        current_row = current_data.iloc[0]
        
        # Calculate features
        features_dict = self._calculate_features(game_data, current_minute)
        
        if features_dict is None:
            return None
        
        # Prepare feature vector
        X = pd.DataFrame([features_dict])
        X = X[self.features].fillna(0).replace([np.inf, -np.inf], 0)
        
        # Get entry probability
        entry_prob = self.entry_model.predict_proba(X)[0, 1]
        
        # Check if signal meets threshold
        if entry_prob >= self.entry_threshold:
            # Predict optimal exit timing
            exit_minutes = self.exit_model.predict(X)[0]
            
            return {
                'action': 'BUY',
                'price': current_row['close'],
                'contracts': self.base_contracts,
                'hold_minutes': int(exit_minutes),
                'probability': float(entry_prob),
                'game_minute': current_minute,
                'signal_type': 'ML',
                'strategy': f'ML_Threshold_{self.entry_threshold:.2f}'
            }
        
        return None
    
    def _calculate_features(self, game_data: pd.DataFrame, current_minute: int) -> Optional[Dict]:
        """
        Calculate all required features for current minute
        
        Args:
            game_data: Game data up to current minute
            current_minute: Current minute
            
        Returns:
            Dictionary of feature values
        """
        try:
            # Get data up to current minute
            data_so_far = game_data[game_data['game_minute'] <= current_minute].copy()
            
            if len(data_so_far) < 10:  # Need at least 10 minutes of data
                return None
            
            current = data_so_far.iloc[-1]
            
            # Basic price features
            features = {
                'open': current['open'],
                'high': current['high'],
                'low': current['low'],
                'close': current['close'],
                'volume': current['volume'],
                'current_price': current['close'],
                'spread': current['high'] - current['low'],
            }
            
            # Calculate rolling features
            close_prices = data_so_far['close'].values
            volumes = data_so_far['volume'].values
            
            # Price movements
            if len(close_prices) >= 1:
                features['price_move_1min'] = ((close_prices[-1] - close_prices[-2]) / close_prices[-2] * 100) if len(close_prices) >= 2 else 0
            if len(close_prices) >= 2:
                features['price_move_2min'] = ((close_prices[-1] - close_prices[-3]) / close_prices[-3] * 100) if len(close_prices) >= 3 else 0
            if len(close_prices) >= 3:
                features['price_move_3min'] = ((close_prices[-1] - close_prices[-4]) / close_prices[-4] * 100) if len(close_prices) >= 4 else 0
            if len(close_prices) >= 5:
                features['price_move_5min'] = ((close_prices[-1] - close_prices[-6]) / close_prices[-6] * 100) if len(close_prices) >= 6 else 0
            if len(close_prices) >= 10:
                features['price_move_10min'] = ((close_prices[-1] - close_prices[-11]) / close_prices[-11] * 100) if len(close_prices) >= 11 else 0
            
            # Volatility
            if len(close_prices) >= 3:
                features['volatility_3min'] = np.std(close_prices[-3:])
            if len(close_prices) >= 5:
                features['volatility_5min'] = np.std(close_prices[-5:])
            if len(close_prices) >= 10:
                features['volatility_10min'] = np.std(close_prices[-10:])
            
            # Volume features
            if len(volumes) >= 3:
                features['volume_ma3'] = np.mean(volumes[-3:])
            if len(volumes) >= 5:
                features['volume_ma5'] = np.mean(volumes[-5:])
                features['volume_spike'] = volumes[-1] / (features['volume_ma5'] + 1e-6)
            if len(volumes) >= 10:
                features['volume_ma10'] = np.mean(volumes[-10:])
            if len(volumes) >= 5:
                features['volume_trend'] = ((volumes[-1] - volumes[-6]) / (volumes[-6] + 1e-6) * 100) if len(volumes) >= 6 else 0
            
            # Score features (if available)
            if 'score_home' in data_so_far.columns and 'score_away' in data_so_far.columns:
                score_home = float(current['score_home']) if pd.notna(current['score_home']) else 0
                score_away = float(current['score_away']) if pd.notna(current['score_away']) else 0
                
                features['score_home'] = score_home
                features['score_away'] = score_away
                features['score_diff'] = score_home - score_away
                features['score_diff_abs'] = abs(features['score_diff'])
                features['score_total'] = score_home + score_away
                
                # Score movements
                scores_home = data_so_far['score_home'].fillna(0).values
                scores_away = data_so_far['score_away'].fillna(0).values
                
                if len(scores_home) >= 2:
                    features['score_diff_1min'] = (score_home - score_away) - (scores_home[-2] - scores_away[-2])
                if len(scores_home) >= 4:
                    features['score_diff_3min'] = (score_home - score_away) - (scores_home[-4] - scores_away[-4])
                if len(scores_home) >= 6:
                    features['score_diff_5min'] = (score_home - score_away) - (scores_home[-6] - scores_away[-6])
                
                # Scoring rates
                if len(scores_home) >= 2:
                    total_now = score_home + score_away
                    total_prev = scores_home[-2] + scores_away[-2]
                    features['scoring_rate_1min'] = total_now - total_prev
                if len(scores_home) >= 4:
                    total_now = score_home + score_away
                    total_prev = scores_home[-4] + scores_away[-4]
                    features['scoring_rate_3min'] = (total_now - total_prev) / 3
                if len(scores_home) >= 6:
                    total_now = score_home + score_away
                    total_prev = scores_home[-6] + scores_away[-6]
                    features['scoring_rate_5min'] = (total_now - total_prev) / 5
                
                # Momentum
                if len(scores_home) >= 4:
                    features['home_momentum_3min'] = score_home - scores_home[-4]
                    features['away_momentum_3min'] = score_away - scores_away[-4]
                if len(scores_home) >= 6:
                    features['home_momentum_5min'] = score_home - scores_home[-6]
                    features['away_momentum_5min'] = score_away - scores_away[-6]
                
                # Game state
                features['time_remaining'] = data_so_far['game_minute'].max() - current_minute
                features['period'] = min(4, (current_minute // 12) + 1)
                features['minutes_into_period'] = current_minute % 12
                
                features['is_period_1'] = 1 if features['period'] == 1 else 0
                features['is_period_2'] = 1 if features['period'] == 2 else 0
                features['is_period_3'] = 1 if features['period'] == 3 else 0
                features['is_period_4'] = 1 if features['period'] == 4 else 0
                features['is_early_period'] = 1 if features['minutes_into_period'] <= 3 else 0
                features['is_late_period'] = 1 if features['minutes_into_period'] >= 9 else 0
                
                # Binary indicators
                features['is_close_game'] = 1 if features['score_diff_abs'] <= 5 else 0
                features['is_very_close'] = 1 if features['score_diff_abs'] <= 3 else 0
                features['is_blowout'] = 1 if features['score_diff_abs'] >= 15 else 0
                features['is_late_game'] = 1 if features['time_remaining'] <= 5 else 0
                features['is_very_late'] = 1 if features['time_remaining'] <= 2 else 0
                features['is_crunch_time'] = 1 if (features['time_remaining'] <= 5 and features['score_diff_abs'] <= 5) else 0
                
                # Price indicators
                features['is_extreme_low'] = 1 if current['close'] <= 10 else 0
                features['is_extreme_high'] = 1 if current['close'] >= 90 else 0
                features['is_extreme_price'] = features['is_extreme_low'] or features['is_extreme_high']
                features['is_mid_price'] = 1 if (40 < current['close'] < 60) else 0
                
                if 'price_move_1min' in features:
                    features['large_move'] = 1 if abs(features['price_move_1min']) > 5 else 0
                    features['huge_move'] = 1 if abs(features['price_move_1min']) > 10 else 0
                
                # Relative features
                features['score_vs_expectation'] = features['score_total'] - (current_minute * 2.2)
                features['pace'] = features['score_total'] / (current_minute + 1)
                
                # Price range
                if len(close_prices) >= 5:
                    features['price_range_5min'] = max(close_prices[-5:]) - min(close_prices[-5:])
            
            # Fill missing features with 0
            for feature_name in self.features:
                if feature_name not in features:
                    features[feature_name] = 0
            
            return features
            
        except Exception as e:
            print(f"Error calculating features: {e}")
            return None
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return {
            'entry_threshold': self.entry_threshold,
            'base_contracts': self.base_contracts,
            'model_type': 'CatBoost + LightGBM',
            'features': len(self.features)
        }

