"""
Train and compare multiple ML model types:
- Neural Network (MLP)
- CatBoost
- XGBoost  
- LightGBM
- Random Forest (current baseline)
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
import joblib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.helpers import get_logger

logger = get_logger(__name__)

# Import advanced models
try:
    from xgboost import XGBClassifier
    has_xgboost = True
except:
    has_xgboost = False
    logger.warning("XGBoost not installed")

try:
    from catboost import CatBoostClassifier
    has_catboost = True
except:
    has_catboost = False
    logger.warning("CatBoost not installed")

try:
    from lightgbm import LGBMClassifier
    has_lightgbm = True
except:
    has_lightgbm = False
    logger.warning("LightGBM not installed")


def train_all_models():
    """Train multiple model types and compare performance"""
    
    logger.info("="*100)
    logger.info("TRAINING MULTIPLE ML MODEL TYPES")
    logger.info("="*100)
    
    # Load training data
    logger.info("\nLoading training data...")
    df = pd.read_csv('ml_models/outputs/training_data.csv')
    logger.info(f"Loaded {len(df):,} samples")
    
    # Features
    feature_cols = [
        'current_price', 'price_move_1min', 'price_move_3min', 'price_move_5min',
        'volatility_5min', 'spread', 'volume_spike',
        'score_diff', 'score_diff_abs', 'time_remaining', 'period',
        'scoring_rate_3min', 'score_momentum', 'lead_extending',
        'is_extreme_low', 'is_extreme_high', 'is_extreme_price', 'is_mid_price',
        'is_close_game', 'is_late_game', 'is_very_late',
        'large_move', 'huge_move'
    ]
    
    X = df[feature_cols].fillna(0)
    y = df['any_profitable']
    
    # Train/test split (time-based)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info(f"\nTrain: {len(X_train):,} | Test: {len(X_test):,}")
    logger.info(f"Positive class: {y_train.mean():.1%}")
    
    # Scale features
    logger.info("\nScaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Define models
    models = {}
    
    # 1. Random Forest (baseline)
    logger.info("\n[1/6] Training Random Forest (baseline)...")
    models['Random Forest'] = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        class_weight='balanced',
        n_jobs=-1
    )
    
    # 2. Neural Network
    logger.info("[2/6] Training Neural Network...")
    models['Neural Network'] = MLPClassifier(
        hidden_layer_sizes=(100, 50, 25),
        activation='relu',
        solver='adam',
        alpha=0.0001,
        batch_size=256,
        learning_rate='adaptive',
        max_iter=200,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1
    )
    
    # 3. XGBoost
    if has_xgboost:
        logger.info("[3/6] Training XGBoost...")
        models['XGBoost'] = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        )
    
    # 4. CatBoost
    if has_catboost:
        logger.info("[4/6] Training CatBoost...")
        models['CatBoost'] = CatBoostClassifier(
            iterations=200,
            depth=6,
            learning_rate=0.1,
            random_state=42,
            verbose=False
        )
    
    # 5. LightGBM
    if has_lightgbm:
        logger.info("[5/6] Training LightGBM...")
        models['LightGBM'] = LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            verbose=-1
        )
    
    # Train all models
    results = {}
    
    for name, model in models.items():
        logger.info(f"\nTraining {name}...")
        
        # Use scaled data for Neural Network, original for tree-based
        if name == 'Neural Network':
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            y_prob = model.predict_proba(X_test_scaled)[:, 1]
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]
        
        # Evaluate
        accuracy = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        
        logger.info(f"  Accuracy: {accuracy:.3f}")
        logger.info(f"  AUC: {auc:.3f}")
        
        results[name] = {
            'model': model,
            'accuracy': accuracy,
            'auc': auc,
            'predictions': y_pred,
            'probabilities': y_prob
        }
    
    # Display comparison
    logger.info("\n" + "="*100)
    logger.info("MODEL COMPARISON")
    logger.info("="*100)
    
    comparison = pd.DataFrame({
        'Model': list(results.keys()),
        'Accuracy': [r['accuracy'] for r in results.values()],
        'AUC': [r['auc'] for r in results.values()]
    }).sort_values('AUC', ascending=False)
    
    print()
    print(comparison.to_string(index=False))
    
    # Save best model
    best_model_name = comparison.iloc[0]['Model']
    best_auc = comparison.iloc[0]['AUC']
    
    logger.info("\n" + "="*100)
    logger.info(f"BEST MODEL: {best_model_name}")
    logger.info(f"  AUC: {best_auc:.3f}")
    logger.info("="*100)
    
    # Save best model
    best_model = results[best_model_name]['model']
    joblib.dump(best_model, 'ml_models/outputs/best_entry_model.pkl')
    joblib.dump(scaler, 'ml_models/outputs/best_entry_scaler.pkl')
    joblib.dump(feature_cols, 'ml_models/outputs/best_entry_features.pkl')
    
    logger.info(f"\nSaved best model ({best_model_name}) to ml_models/outputs/")
    
    # Detailed report for best model
    logger.info(f"\nDetailed Performance ({best_model_name}):")
    y_pred_best = results[best_model_name]['predictions']
    print(classification_report(y_test, y_pred_best, target_names=['No Trade', 'Enter Trade']))
    
    return results, comparison


if __name__ == "__main__":
    results, comparison = train_all_models()




