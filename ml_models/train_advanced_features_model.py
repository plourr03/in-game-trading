"""
Train models with advanced features to find more trading opportunities
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from xgboost import XGBClassifier
import joblib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def train_with_advanced_features():
    """Train models with comprehensive PBP features"""
    
    logger.info("="*100)
    logger.info("TRAINING WITH ADVANCED FEATURES")
    logger.info("="*100)
    
    # Load data
    logger.info("\nLoading advanced training data...")
    df = pd.read_csv('ml_models/outputs/advanced_training_data.csv')
    logger.info(f"Loaded {len(df):,} samples")
    logger.info(f"Positive class rate: {df['any_profitable'].mean():.1%}")
    
    # Feature columns (exclude targets and IDs and non-numeric)
    exclude_cols = ['game_id', 'ticker', 'timestamp', 'datetime', 'away_team', 'home_team', 'game_date', 'game_minute', 
                    'future_price_1min', 'future_price_3min', 'future_price_5min', 'future_price_7min',
                    'profit_1min', 'profit_3min', 'profit_5min', 'profit_7min', 'any_profitable']
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    
    logger.info(f"Using {len(feature_cols)} features")
    
    X = df[feature_cols].fillna(0)
    X = X.replace([np.inf, -np.inf], 0)  # Replace inf values
    y = df['any_profitable']
    
    # Time-based split
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info(f"\nTrain: {len(X_train):,} | Test: {len(X_test):,}")
    logger.info(f"Train positive rate: {y_train.mean():.1%}")
    logger.info(f"Test positive rate: {y_test.mean():.1%}")
    
    # Train multiple models
    models = {}
    
    # LightGBM
    logger.info("\n[1/3] Training LightGBM...")
    lgbm = LGBMClassifier(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.05,
        num_leaves=63,
        min_child_samples=20,
        random_state=42,
        verbose=-1
    )
    lgbm.fit(X_train, y_train)
    models['LightGBM'] = lgbm
    
    # XGBoost
    logger.info("[2/3] Training XGBoost...")
    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss'
    )
    xgb.fit(X_train, y_train)
    models['XGBoost'] = xgb
    
    # CatBoost
    logger.info("[3/3] Training CatBoost...")
    cat = CatBoostClassifier(
        iterations=300,
        depth=8,
        learning_rate=0.05,
        random_state=42,
        verbose=False
    )
    cat.fit(X_train, y_train)
    models['CatBoost'] = cat
    
    # Evaluate all
    logger.info("\n" + "="*100)
    logger.info("MODEL PERFORMANCE")
    logger.info("="*100)
    
    results = []
    for name, model in models.items():
        y_pred_train = model.predict_proba(X_train)[:, 1]
        y_pred_test = model.predict_proba(X_test)[:, 1]
        
        train_auc = roc_auc_score(y_train, y_pred_train)
        test_auc = roc_auc_score(y_test, y_pred_test)
        
        results.append({
            'model': name,
            'train_auc': train_auc,
            'test_auc': test_auc,
            'overfit': train_auc - test_auc
        })
        
        logger.info(f"\n{name}:")
        logger.info(f"  Train AUC: {train_auc:.4f}")
        logger.info(f"  Test AUC:  {test_auc:.4f}")
        logger.info(f"  Overfit:   {train_auc - test_auc:.4f}")
    
    results_df = pd.DataFrame(results).sort_values('test_auc', ascending=False)
    
    # Save best model
    best_model_name = results_df.iloc[0]['model']
    best_model = models[best_model_name]
    
    logger.info("\n" + "="*100)
    logger.info(f"BEST MODEL: {best_model_name}")
    logger.info(f"  Test AUC: {results_df.iloc[0]['test_auc']:.4f}")
    logger.info("="*100)
    
    # Save
    joblib.dump(best_model, 'ml_models/outputs/advanced_model.pkl')
    joblib.dump(feature_cols, 'ml_models/outputs/advanced_features.pkl')
    
    logger.info("\nSaved:")
    logger.info("  - ml_models/outputs/advanced_model.pkl")
    logger.info("  - ml_models/outputs/advanced_features.pkl")
    
    # Feature importance
    logger.info("\n" + "="*100)
    logger.info("TOP 20 MOST IMPORTANT FEATURES")
    logger.info("="*100)
    
    if best_model_name == 'LightGBM':
        importances = best_model.feature_importances_
    elif best_model_name == 'XGBoost':
        importances = best_model.feature_importances_
    else:  # CatBoost
        importances = best_model.feature_importances_
    
    importance_df = pd.DataFrame({
        'feature': feature_cols,
        'importance': importances
    }).sort_values('importance', ascending=False)
    
    print()
    print(importance_df.head(20).to_string(index=False))
    
    return best_model, feature_cols


if __name__ == "__main__":
    model, features = train_with_advanced_features()

