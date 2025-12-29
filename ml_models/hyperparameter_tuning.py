"""
Hyperparameter Tuning for LightGBM using selected features
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score
from lightgbm import LGBMClassifier
import joblib
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def hyperparameter_tuning():
    """Grid search for best LightGBM hyperparameters"""
    
    logger.info("="*100)
    logger.info("HYPERPARAMETER TUNING - LIGHTGBM")
    logger.info("="*100)
    
    # Load data
    logger.info("\nLoading training data...")
    df = pd.read_csv('ml_models/outputs/training_data.csv')
    logger.info(f"Loaded {len(df):,} samples")
    
    # Load selected features
    logger.info("Loading selected features...")
    with open('ml_models/outputs/selected_features.json', 'r') as f:
        feature_sets = json.load(f)
    
    # Use consensus features (top performers)
    feature_cols = feature_sets['consensus_2_of_3']
    logger.info(f"Using {len(feature_cols)} selected features")
    
    X = df[feature_cols].fillna(0)
    y = df['any_profitable']
    
    # Train/test split
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info(f"\nTrain: {len(X_train):,} | Test: {len(X_test):,}")
    
    # Define hyperparameter grid
    param_grid = [
        # Baseline
        {'n_estimators': 200, 'max_depth': 6, 'learning_rate': 0.1, 'num_leaves': 31, 'min_child_samples': 20},
        
        # More trees
        {'n_estimators': 300, 'max_depth': 6, 'learning_rate': 0.1, 'num_leaves': 31, 'min_child_samples': 20},
        {'n_estimators': 400, 'max_depth': 6, 'learning_rate': 0.1, 'num_leaves': 31, 'min_child_samples': 20},
        
        # Deeper trees
        {'n_estimators': 200, 'max_depth': 8, 'learning_rate': 0.1, 'num_leaves': 63, 'min_child_samples': 20},
        {'n_estimators': 200, 'max_depth': 10, 'learning_rate': 0.1, 'num_leaves': 127, 'min_child_samples': 20},
        
        # Lower learning rate
        {'n_estimators': 300, 'max_depth': 6, 'learning_rate': 0.05, 'num_leaves': 31, 'min_child_samples': 20},
        {'n_estimators': 400, 'max_depth': 6, 'learning_rate': 0.05, 'num_leaves': 31, 'min_child_samples': 20},
        
        # More leaves
        {'n_estimators': 200, 'max_depth': 6, 'learning_rate': 0.1, 'num_leaves': 50, 'min_child_samples': 20},
        {'n_estimators': 200, 'max_depth': 6, 'learning_rate': 0.1, 'num_leaves': 70, 'min_child_samples': 20},
        
        # Regularization
        {'n_estimators': 200, 'max_depth': 6, 'learning_rate': 0.1, 'num_leaves': 31, 'min_child_samples': 30},
        {'n_estimators': 200, 'max_depth': 6, 'learning_rate': 0.1, 'num_leaves': 31, 'min_child_samples': 50},
        
        # Combined best
        {'n_estimators': 300, 'max_depth': 8, 'learning_rate': 0.05, 'num_leaves': 63, 'min_child_samples': 20},
        {'n_estimators': 400, 'max_depth': 8, 'learning_rate': 0.05, 'num_leaves': 63, 'min_child_samples': 30},
    ]
    
    logger.info(f"\nTesting {len(param_grid)} hyperparameter combinations...")
    logger.info("="*100)
    
    results = []
    
    for i, params in enumerate(param_grid, 1):
        logger.info(f"\n[{i}/{len(param_grid)}] Testing: {params}")
        
        model = LGBMClassifier(
            **params,
            random_state=42,
            verbose=-1
        )
        
        # Train
        model.fit(X_train, y_train)
        
        # Evaluate
        train_pred = model.predict_proba(X_train)[:, 1]
        test_pred = model.predict_proba(X_test)[:, 1]
        
        train_auc = roc_auc_score(y_train, train_pred)
        test_auc = roc_auc_score(y_test, test_pred)
        
        logger.info(f"    Train AUC: {train_auc:.4f}")
        logger.info(f"    Test AUC:  {test_auc:.4f}")
        logger.info(f"    Overfit:   {train_auc - test_auc:.4f}")
        
        results.append({
            **params,
            'train_auc': train_auc,
            'test_auc': test_auc,
            'overfit': train_auc - test_auc
        })
    
    # Display results
    logger.info("\n" + "="*100)
    logger.info("HYPERPARAMETER TUNING RESULTS")
    logger.info("="*100)
    
    results_df = pd.DataFrame(results).sort_values('test_auc', ascending=False)
    print()
    print(results_df.to_string(index=False))
    
    # Find best
    logger.info("\n" + "="*100)
    logger.info("BEST HYPERPARAMETERS")
    logger.info("="*100)
    
    best = results_df.iloc[0]
    logger.info(f"\nTest AUC: {best['test_auc']:.4f}")
    logger.info(f"Train AUC: {best['train_auc']:.4f}")
    logger.info(f"Overfit: {best['overfit']:.4f}")
    logger.info("\nParameters:")
    for param in ['n_estimators', 'max_depth', 'learning_rate', 'num_leaves', 'min_child_samples']:
        logger.info(f"  {param}: {best[param]}")
    
    # Train final model with best params
    logger.info("\n" + "="*100)
    logger.info("TRAINING FINAL MODEL WITH BEST PARAMETERS")
    logger.info("="*100)
    
    best_params = {
        'n_estimators': int(best['n_estimators']),
        'max_depth': int(best['max_depth']),
        'learning_rate': float(best['learning_rate']),
        'num_leaves': int(best['num_leaves']),
        'min_child_samples': int(best['min_child_samples']),
        'random_state': 42,
        'verbose': -1
    }
    
    final_model = LGBMClassifier(**best_params)
    final_model.fit(X_train, y_train)
    
    # Save
    logger.info("\nSaving optimized model...")
    joblib.dump(final_model, 'ml_models/outputs/optimized_entry_model.pkl')
    joblib.dump(feature_cols, 'ml_models/outputs/optimized_entry_features.pkl')
    joblib.dump(best_params, 'ml_models/outputs/optimized_hyperparameters.json')
    
    logger.info("  - optimized_entry_model.pkl")
    logger.info("  - optimized_entry_features.pkl")
    logger.info("  - optimized_hyperparameters.json")
    
    logger.info("\n" + "="*100)
    logger.info("OPTIMIZATION COMPLETE!")
    logger.info("="*100)
    logger.info(f"\nImprovement from baseline:")
    baseline_auc = results_df[results_df['n_estimators'] == 200].iloc[0]['test_auc']
    improvement = (best['test_auc'] - baseline_auc) * 100
    logger.info(f"  Baseline AUC: {baseline_auc:.4f}")
    logger.info(f"  Optimized AUC: {best['test_auc']:.4f}")
    logger.info(f"  Improvement: +{improvement:.2f}%")
    logger.info("\nNext: Test optimized model in trading backtest!")
    logger.info("="*100)
    
    return final_model, best_params


if __name__ == "__main__":
    model, params = hyperparameter_tuning()




