"""
IMPROVEMENT #1: Exit Timing Optimization
Train a model to predict the BEST hold duration for each trade
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from lightgbm import LGBMClassifier
import joblib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def train_exit_timing_model():
    """Train model to predict optimal exit timing"""
    
    logger.info("="*100)
    logger.info("TRAINING EXIT TIMING MODEL")
    logger.info("="*100)
    
    # Load data
    logger.info("\nLoading training data...")
    df = pd.read_csv('ml_models/outputs/advanced_training_data.csv')
    
    # Only use samples where we have all hold periods
    df = df.dropna(subset=['profit_1min', 'profit_3min', 'profit_5min', 'profit_7min'])
    logger.info(f"Loaded {len(df):,} samples")
    
    # Create target: which hold period is best?
    # Best = highest profit after fees (assume ~2 cents total fees)
    fee_threshold = 3  # Need 3+ cents profit after ~2 cent fees
    
    df['profit_1min_net'] = df['profit_1min'] - 2
    df['profit_3min_net'] = df['profit_3min'] - 2
    df['profit_5min_net'] = df['profit_5min'] - 2
    df['profit_7min_net'] = df['profit_7min'] - 2
    
    # Find best hold period
    profits = df[['profit_1min_net', 'profit_3min_net', 'profit_5min_net', 'profit_7min_net']]
    df['best_hold'] = profits.idxmax(axis=1).str.replace('profit_', '').str.replace('min_net', '').astype(int)
    df['best_profit'] = profits.max(axis=1)
    
    # Only train on samples where at least one hold period is profitable
    df_profitable = df[df['best_profit'] > 0].copy()
    logger.info(f"Samples with profitable exit: {len(df_profitable):,}")
    
    # Distribution of best holds
    hold_dist = df_profitable['best_hold'].value_counts().sort_index()
    logger.info("\nBest hold distribution:")
    for hold, count in hold_dist.items():
        logger.info(f"  {hold}min: {count:,} ({count/len(df_profitable)*100:.1f}%)")
    
    # Features (exclude target-related)
    exclude_cols = ['game_id', 'ticker', 'timestamp', 'datetime', 'away_team', 'home_team', 
                    'game_date', 'game_minute', 'future_price_1min', 'future_price_3min', 
                    'future_price_5min', 'future_price_7min', 'profit_1min', 'profit_3min', 
                    'profit_5min', 'profit_7min', 'any_profitable', 'profit_1min_net',
                    'profit_3min_net', 'profit_5min_net', 'profit_7min_net', 'best_hold', 'best_profit']
    feature_cols = [c for c in df_profitable.columns if c not in exclude_cols]
    
    X = df_profitable[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    y = df_profitable['best_hold']
    
    # Time-based split
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info(f"\nTrain: {len(X_train):,} | Test: {len(X_test):,}")
    
    # Train LightGBM for multi-class
    logger.info("\nTraining exit timing model...")
    model = LGBMClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        verbose=-1
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    
    logger.info(f"\nModel Performance:")
    logger.info(f"  Train Accuracy: {train_acc:.2%}")
    logger.info(f"  Test Accuracy:  {test_acc:.2%}")
    
    # Save
    joblib.dump(model, 'ml_models/outputs/exit_timing_model.pkl')
    logger.info("\n✅ Saved: ml_models/outputs/exit_timing_model.pkl")
    
    # Test on actual predictions
    logger.info("\n" + "="*100)
    logger.info("SIMULATING WITH OPTIMAL EXIT TIMING")
    logger.info("="*100)
    
    # Predict best holds
    y_pred = model.predict(X_test)
    
    # Calculate actual profits with predicted holds
    test_df = df_profitable[split_idx:].copy()
    test_df['predicted_hold'] = y_pred
    
    # Get actual profit for predicted hold
    def get_profit_for_hold(row):
        hold = row['predicted_hold']
        return row[f'profit_{hold}min_net']
    
    test_df['predicted_profit'] = test_df.apply(get_profit_for_hold, axis=1)
    test_df['fixed_5min_profit'] = test_df['profit_5min_net']
    
    # Compare
    total_pred = test_df['predicted_profit'].sum()
    total_fixed = test_df['fixed_5min_profit'].sum()
    improvement = ((total_pred - total_fixed) / abs(total_fixed)) * 100 if total_fixed != 0 else 0
    
    logger.info(f"\nProfit Comparison (test set):")
    logger.info(f"  Fixed 5min hold:    {total_fixed:.2f} cents")
    logger.info(f"  Optimized timing:   {total_pred:.2f} cents")
    logger.info(f"  Improvement:        {total_pred - total_fixed:.2f} cents ({improvement:+.1f}%)")
    
    return model, feature_cols


if __name__ == "__main__":
    model, features = train_exit_timing_model()




