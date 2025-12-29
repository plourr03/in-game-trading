"""Baseline win probability model"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss
from typing import Dict, Tuple
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def historical_win_rate(df: pd.DataFrame, score_diff_bins: int = 20,
                       time_bins: int = 10) -> pd.DataFrame:
    """
    Calculate empirical win rates by score differential and time remaining.
    
    Args:
        df: Historical game data with outcomes
        score_diff_bins: Number of bins for score differential
        time_bins: Number of bins for time remaining
        
    Returns:
        DataFrame with win rates by game state
    """
    logger.info("Calculating historical win rates...")
    
    # Create bins
    df['score_diff_bin'] = pd.cut(df['score_differential'], bins=score_diff_bins)
    df['time_bin'] = pd.cut(df['time_remaining'], bins=time_bins)
    
    # Calculate win rates
    win_rates = df.groupby(['score_diff_bin', 'time_bin']).agg({
        'team_won': ['mean', 'count']
    }).reset_index()
    
    win_rates.columns = ['score_diff_bin', 'time_bin', 'win_rate', 'count']
    
    logger.info(f"Calculated win rates for {len(win_rates)} game states")
    return win_rates


def logistic_regression_baseline(df: pd.DataFrame) -> Tuple[LogisticRegression, Dict]:
    """
    Build simple logistic regression: P(win) ~ score_diff + time + interaction.
    
    Args:
        df: Training data with game outcomes
        
    Returns:
        Tuple of (fitted model, performance metrics)
    """
    logger.info("Training logistic regression baseline model...")
    
    # Prepare features
    X = df[['score_differential', 'time_remaining']].copy()
    X['interaction'] = X['score_differential'] * X['time_remaining']
    
    # Target: did the team win?
    y = df['team_won']
    
    # Remove NaN values
    valid_mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[valid_mask]
    y = y[valid_mask]
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train model
    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_train, y_train)
    
    # Calculate performance metrics
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    metrics = {
        'train_size': len(X_train),
        'test_size': len(X_test),
        'roc_auc': roc_auc_score(y_test, y_pred_proba),
        'log_loss': log_loss(y_test, y_pred_proba),
        'brier_score': brier_score_loss(y_test, y_pred_proba),
        'coefficients': {
            'score_differential': model.coef_[0][0],
            'time_remaining': model.coef_[0][1],
            'interaction': model.coef_[0][2],
            'intercept': model.intercept_[0]
        }
    }
    
    logger.info(f"Model trained. ROC-AUC: {metrics['roc_auc']:.4f}")
    
    return model, metrics

