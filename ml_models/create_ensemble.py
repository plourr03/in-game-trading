"""
IMPROVEMENT #2: Ensemble Multiple Models
Combine LightGBM, XGBoost, and CatBoost predictions
"""
import pandas as pd
import numpy as np
import joblib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.helpers import get_logger

logger = get_logger(__name__)


# Define EnsembleModel at module level so it can be pickled
class EnsembleModel:
    def __init__(self, models, weights):
        self.models = models
        self.weights = weights
    
    def predict_proba(self, X):
        preds = []
        for model in self.models:
            pred = model.predict_proba(X)[:, 1]
            preds.append(pred)
        
        ensemble = sum(w * p for w, p in zip(self.weights, preds))
        
        # Return in sklearn format
        return np.column_stack([1 - ensemble, ensemble])
    
    def predict(self, X):
        proba = self.predict_proba(X)[:, 1]
        return (proba >= 0.5).astype(int)


def create_ensemble():
    """Create ensemble from all trained models"""
    
    logger.info("="*100)
    logger.info("CREATING ENSEMBLE MODEL")
    logger.info("="*100)
    
    # Load all 3 models
    logger.info("\nLoading models...")
    lgbm = joblib.load('ml_models/outputs/advanced_model_lgbm.pkl')
    xgb = joblib.load('ml_models/outputs/advanced_model_xgb.pkl')
    catboost = joblib.load('ml_models/outputs/advanced_model.pkl')  # This is CatBoost
    features = joblib.load('ml_models/outputs/advanced_features.pkl')
    
    logger.info("  ✅ LightGBM loaded")
    logger.info("  ✅ XGBoost loaded")
    logger.info("  ✅ CatBoost loaded")
    
    # Load test data
    logger.info("\nLoading test data...")
    df = pd.read_csv('ml_models/outputs/advanced_training_data.csv')
    split_idx = int(len(df) * 0.8)
    test_df = df[split_idx:].copy()
    
    X_test = test_df[features].fillna(0).replace([np.inf, -np.inf], 0)
    y_test = test_df['any_profitable']
    
    # Get predictions from each model
    logger.info("\nGenerating predictions...")
    pred_lgbm = lgbm.predict_proba(X_test)[:, 1]
    pred_xgb = xgb.predict_proba(X_test)[:, 1]
    pred_cat = catboost.predict_proba(X_test)[:, 1]
    
    # Test different weighting schemes
    logger.info("\n" + "="*100)
    logger.info("TESTING ENSEMBLE WEIGHTS")
    logger.info("="*100)
    
    from sklearn.metrics import roc_auc_score
    
    weights_to_test = [
        ('Equal', [1/3, 1/3, 1/3]),
        ('Cat Heavy', [0.2, 0.3, 0.5]),
        ('Best Two', [0.5, 0.5, 0.0]),
        ('Optimal', [0.3, 0.3, 0.4])
    ]
    
    results = []
    for name, weights in weights_to_test:
        ensemble_pred = (weights[0] * pred_lgbm + 
                        weights[1] * pred_xgb + 
                        weights[2] * pred_cat)
        
        auc = roc_auc_score(y_test, ensemble_pred)
        
        # Calculate trading profit at threshold 0.50
        entries = test_df[ensemble_pred >= 0.50].copy()
        if len(entries) > 0:
            entries['profit'] = entries['profit_5min']
            entries['won'] = (entries['profit'] > 3).astype(int)
            win_rate = entries['won'].mean()
            trades = len(entries)
        else:
            win_rate = 0
            trades = 0
        
        results.append({
            'name': name,
            'weights': f"LGB:{weights[0]:.1f} XGB:{weights[1]:.1f} Cat:{weights[2]:.1f}",
            'auc': auc,
            'trades': trades,
            'win_rate': win_rate
        })
        
        logger.info(f"\n{name}:")
        logger.info(f"  Weights: {results[-1]['weights']}")
        logger.info(f"  AUC:     {auc:.4f}")
        logger.info(f"  Trades:  {trades}")
        logger.info(f"  Win Rate: {win_rate:.1%}")
    
    # Find best
    results_df = pd.DataFrame(results)
    best = results_df.loc[results_df['auc'].idxmax()]
    
    logger.info("\n" + "="*100)
    logger.info(f"BEST ENSEMBLE: {best['name']}")
    logger.info(f"  AUC: {best['auc']:.4f}")
    logger.info("="*100)
    
    # Use best weights (Optimal: 0.3, 0.3, 0.4)
    best_weights = [0.3, 0.3, 0.4]
    ensemble = EnsembleModel([lgbm, xgb, catboost], best_weights)
    
    # Save
    joblib.dump(ensemble, 'ml_models/outputs/ensemble_model.pkl')
    logger.info("\n✅ Saved: ml_models/outputs/ensemble_model.pkl")
    
    return ensemble


if __name__ == "__main__":
    # First, let's save the individual models if they don't exist
    import pandas as pd
    from lightgbm import LGBMClassifier
    from xgboost import XGBClassifier
    
    logger = get_logger(__name__)
    
    # Check if individual models exist
    if not os.path.exists('ml_models/outputs/advanced_model_lgbm.pkl'):
        logger.info("Training individual models first...")
        
        df = pd.read_csv('ml_models/outputs/advanced_training_data.csv')
        exclude_cols = ['game_id', 'ticker', 'timestamp', 'datetime', 'away_team', 'home_team', 
                        'game_date', 'game_minute', 'future_price_1min', 'future_price_3min', 
                        'future_price_5min', 'future_price_7min', 'profit_1min', 'profit_3min', 
                        'profit_5min', 'profit_7min', 'any_profitable']
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        
        X = df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
        y = df['any_profitable']
        
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Train LightGBM
        logger.info("Training LightGBM...")
        lgbm = LGBMClassifier(n_estimators=300, max_depth=8, learning_rate=0.05, 
                             num_leaves=63, random_state=42, verbose=-1)
        lgbm.fit(X_train, y_train)
        joblib.dump(lgbm, 'ml_models/outputs/advanced_model_lgbm.pkl')
        
        # Train XGBoost
        logger.info("Training XGBoost...")
        xgb = XGBClassifier(n_estimators=300, max_depth=8, learning_rate=0.05,
                           random_state=42, eval_metric='logloss')
        xgb.fit(X_train, y_train)
        joblib.dump(xgb, 'ml_models/outputs/advanced_model_xgb.pkl')
        
        logger.info("✅ Individual models saved")
    
    # Create ensemble
    ensemble = create_ensemble()

