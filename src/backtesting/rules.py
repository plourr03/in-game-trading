"""Simple rule-based strategies"""
import pandas as pd
import numpy as np
from .framework import Strategy
from ..utils.helpers import get_logger

logger = get_logger(__name__)


class SimpleRuleStrategy(Strategy):
    """Simple rule-based strategy implementation."""
    
    def __init__(self, rule_type: str, **params):
        """
        Initialize rule strategy.
        
        Args:
            rule_type: Type of rule ('fade_momentum', 'buy_underdog', etc.)
            **params: Rule-specific parameters
        """
        super().__init__(name=f"{rule_type}_strategy")
        self.rule_type = rule_type
        self.params = params
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on rule type.
        
        Args:
            df: Game data
            
        Returns:
            DataFrame with signal column
        """
        df = df.copy()
        df['signal'] = 0  # Default: no signal
        
        if self.rule_type == 'fade_momentum':
            return self._fade_momentum(df)
        elif self.rule_type == 'buy_underdog_after_run':
            return self._buy_underdog_after_run(df)
        elif self.rule_type == 'contrarian':
            return self._contrarian(df)
        else:
            logger.warning(f"Unknown rule type: {self.rule_type}")
            return df
    
    def _fade_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fade momentum after big runs.
        
        After large price move up, bet down (and vice versa).
        """
        threshold = self.params.get('threshold', 5.0)
        
        df['price_change'] = df.groupby('game_id')['close'].diff()
        
        # Sell after large up move
        df.loc[df['price_change'] > threshold, 'signal'] = -1
        
        # Buy after large down move
        df.loc[df['price_change'] < -threshold, 'signal'] = 1
        
        return df
    
    def _buy_underdog_after_run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Buy underdog when they score in Q4 of close game.
        
        Hypothesis: Market overreacts to favorite momentum in clutch time.
        """
        # Identify Q4 close games
        is_q4 = df['period'] == 4
        
        if 'score_differential' not in df.columns:
            df['score_differential'] = df['score_home'] - df['score_away']
        
        is_close = df['score_differential'].abs() < 5
        
        # Look for scoring by either team
        is_scoring = df['action_type'] == 'Made Shot'
        
        # Buy underdog (bet against favorite)
        df.loc[is_q4 & is_close & is_scoring, 'signal'] = 1
        
        return df
    
    def _contrarian(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Contrarian strategy after large price movements.
        
        Bet on mean reversion after extreme moves.
        """
        threshold = self.params.get('threshold', 5.0)
        
        df['price_change'] = df.groupby('game_id')['close'].diff()
        
        # After large move, bet on reversal
        df.loc[df['price_change'].abs() > threshold, 'signal'] = -np.sign(df['price_change'])
        
        return df


class MomentumFadeStrategy(Strategy):
    """Fade momentum after scoring runs."""
    
    def __init__(self, min_run_points: int = 8):
        """
        Initialize momentum fade strategy.
        
        Args:
            min_run_points: Minimum points in run to trigger signal
        """
        super().__init__(name=f"fade_{min_run_points}pt_runs")
        self.min_run_points = min_run_points
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals to fade scoring runs."""
        df = df.copy()
        df['signal'] = 0
        
        # Track consecutive scoring
        df['same_team_scored'] = (
            (df['action_type'] == 'Made Shot') &
            (df['location'] == df['location'].shift(1))
        )
        
        # Count points in current run
        df['run_points'] = 0
        current_run = 0
        
        for idx in range(len(df)):
            if df.iloc[idx]['same_team_scored']:
                current_run += df.iloc[idx].get('shot_value', 2)
            else:
                current_run = 0
            df.iloc[idx, df.columns.get_loc('run_points')] = current_run
        
        # Signal to fade after significant run
        df.loc[df['run_points'] >= self.min_run_points, 'signal'] = -1
        
        return df

