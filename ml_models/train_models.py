"""
Train ML models for trading entry prediction and hold duration optimization
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.helpers import get_logger

logger = get_logger(__name__)


def train_entry_model(df):
    """
    Train model to predict whether to enter a trade
    Target: Will ANY hold period be profitable?
    """
    logger.info("\n" + "="*100)
    logger.info("TRAINING ENTRY PREDICTION MODEL")
    logger.info("="*100)
    
    # Features for entry model
    feature_cols = [
        'current_price', 'price_move_1min', 'price_move_3min', 'price_move_5min',
        'volatility_5min', 'spread', 'volume_spike',
        'score_diff', 'score_diff_abs', 'time_remaining', 'period',
        'scoring_rate_3min', 'score_momentum', 'lead_extending',  # New PBP features
        'is_extreme_low', 'is_extreme_high', 'is_extreme_price', 'is_mid_price',
        'is_close_game', 'is_late_game', 'is_very_late',
        'large_move', 'huge_move'
    ]
    
    X = df[feature_cols].fillna(0)
    y = df['any_profitable']
    
    logger.info(f"\nDataset:")
    logger.info(f"  Samples:         {len(X):,}")
    logger.info(f"  Features:        {len(feature_cols)}")
    logger.info(f"  Positive class:  {y.sum():,} ({y.mean():.1%})")
    logger.info(f"  Negative class:  {(~y.astype(bool)).sum():,} ({(~y.astype(bool)).mean():.1%})")
    
    # Train/test split (time-based - last 20% for testing)
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info(f"\nSplit:")
    logger.info(f"  Train:  {len(X_train):,} samples")
    logger.info(f"  Test:   {len(X_test):,} samples")
    
    # Scale features
    logger.info("\nScaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train multiple models
    logger.info("\nTraining models...")
    models = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced'),
        'Random Forest': RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, class_weight='balanced', n_jobs=-1),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)
    }
    
    results = {}
    for name, model in models.items():
        logger.info(f"\n  Training {name}...")
        model.fit(X_train_scaled, y_train)
        
        y_pred = model.predict(X_test_scaled)
        y_pred_train = model.predict(X_train_scaled)
        
        if hasattr(model, 'predict_proba'):
            y_prob = model.predict_proba(X_test_scaled)[:, 1]
            auc = roc_auc_score(y_test, y_prob)
        else:
            y_prob = None
            auc = None
        
        train_acc = accuracy_score(y_train, y_pred_train)
        test_acc = accuracy_score(y_test, y_pred)
        
        logger.info(f"    Train Accuracy: {train_acc:.3f}")
        logger.info(f"    Test Accuracy:  {test_acc:.3f}")
        if auc:
            logger.info(f"    AUC:            {auc:.3f}")
        
        results[name] = {
            'model': model,
            'auc': auc if auc else test_acc,
            'test_acc': test_acc,
            'train_acc': train_acc,
            'predictions': y_pred,
            'probabilities': y_prob
        }
    
    # Select best model
    best_model_name = max(results, key=lambda k: results[k]['auc'])
    best_model = results[best_model_name]['model']
    best_auc = results[best_model_name]['auc']
    
    logger.info("\n" + "="*100)
    logger.info(f"BEST MODEL: {best_model_name}")
    logger.info("="*100)
    logger.info(f"\nTest Performance:")
    logger.info(f"  Accuracy: {results[best_model_name]['test_acc']:.3f}")
    logger.info(f"  AUC:      {results[best_model_name]['auc']:.3f}")
    
    y_pred_best = results[best_model_name]['predictions']
    logger.info("\nClassification Report:")
    logger.info(classification_report(y_test, y_pred_best, target_names=['No Trade', 'Enter Trade']))
    
    logger.info("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred_best)
    logger.info(f"                 Predicted")
    logger.info(f"               No    Yes")
    logger.info(f"Actual No   {cm[0,0]:5d}  {cm[0,1]:5d}")
    logger.info(f"       Yes  {cm[1,0]:5d}  {cm[1,1]:5d}")
    
    # Save model
    logger.info("\nSaving model artifacts...")
    joblib.dump(best_model, 'ml_models/outputs/entry_model.pkl')
    joblib.dump(scaler, 'ml_models/outputs/entry_scaler.pkl')
    joblib.dump(feature_cols, 'ml_models/outputs/entry_features.pkl')
    logger.info("  - entry_model.pkl")
    logger.info("  - entry_scaler.pkl")
    logger.info("  - entry_features.pkl")
    
    # Feature importance (if available)
    if hasattr(best_model, 'feature_importances_'):
        logger.info("\nFeature Importance (Top 15):")
        importances = pd.DataFrame({
            'feature': feature_cols,
            'importance': best_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for idx, row in importances.head(15).iterrows():
            logger.info(f"  {row['feature']:25s} {row['importance']:.4f}")
        
        # Plot
        plt.figure(figsize=(10, 8))
        sns.barplot(data=importances.head(20), x='importance', y='feature', palette='viridis')
        plt.title(f'Feature Importance - Entry Model ({best_model_name})', fontsize=14, fontweight='bold')
        plt.xlabel('Importance', fontsize=12)
        plt.ylabel('Feature', fontsize=12)
        plt.tight_layout()
        plt.savefig('ml_models/outputs/feature_importance_entry.png', dpi=150)
        logger.info("\n  Saved: feature_importance_entry.png")
        plt.close()
    
    return best_model, scaler, feature_cols, results


def train_hold_duration_model(df):
    """
    Train model to predict optimal hold duration
    Only trains on samples where at least one hold period is profitable
    """
    logger.info("\n" + "="*100)
    logger.info("TRAINING HOLD DURATION OPTIMIZER")
    logger.info("="*100)
    
    # Filter to profitable trades only
    df_profitable = df[df['any_profitable'] == 1].copy()
    logger.info(f"\nTraining on {len(df_profitable):,} profitable samples (out of {len(df):,} total)")
    
    if len(df_profitable) < 100:
        logger.warning("Not enough profitable samples for hold duration model!")
        return None, None, None, None
    
    # Features for hold duration model
    feature_cols = [
        'current_price', 'price_move_1min', 'price_move_3min', 'price_move_5min',
        'volatility_5min', 'spread', 'volume_spike',
        'score_diff_abs', 'time_remaining', 'period',
        'scoring_rate_3min', 'score_momentum',  # New PBP features
        'is_extreme_price', 'is_close_game', 'is_late_game',
        'large_move', 'huge_move'
    ]
    
    X = df_profitable[feature_cols].fillna(0)
    y = df_profitable['optimal_hold']
    
    logger.info(f"\nDataset:")
    logger.info(f"  Samples:  {len(X):,}")
    logger.info(f"  Features: {len(feature_cols)}")
    logger.info(f"\nHold Period Distribution:")
    for hold_period in sorted(y.unique()):
        count = (y == hold_period).sum()
        pct = count / len(y)
        logger.info(f"  {int(hold_period):2d}min: {count:5d} ({pct:.1%})")
    
    # Train/test split
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info(f"\nSplit:")
    logger.info(f"  Train: {len(X_train):,} samples")
    logger.info(f"  Test:  {len(X_test):,} samples")
    
    # Scale
    logger.info("\nScaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    logger.info("\nTraining Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test_scaled)
    y_pred_train = model.predict(X_train_scaled)
    
    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred)
    
    logger.info(f"\nPerformance:")
    logger.info(f"  Train Accuracy: {train_acc:.3f}")
    logger.info(f"  Test Accuracy:  {test_acc:.3f}")
    
    logger.info("\nClassification Report:")
    logger.info(classification_report(y_test, y_pred, zero_division=0))
    
    # Save
    logger.info("\nSaving model artifacts...")
    joblib.dump(model, 'ml_models/outputs/hold_duration_model.pkl')
    joblib.dump(scaler, 'ml_models/outputs/hold_duration_scaler.pkl')
    joblib.dump(feature_cols, 'ml_models/outputs/hold_duration_features.pkl')
    logger.info("  - hold_duration_model.pkl")
    logger.info("  - hold_duration_scaler.pkl")
    logger.info("  - hold_duration_features.pkl")
    
    # Feature importance
    if hasattr(model, 'feature_importances_'):
        logger.info("\nFeature Importance (Top 10):")
        importances = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for idx, row in importances.head(10).iterrows():
            logger.info(f"  {row['feature']:25s} {row['importance']:.4f}")
        
        # Plot
        plt.figure(figsize=(10, 6))
        sns.barplot(data=importances.head(15), x='importance', y='feature', palette='plasma')
        plt.title('Feature Importance - Hold Duration Model', fontsize=14, fontweight='bold')
        plt.xlabel('Importance', fontsize=12)
        plt.ylabel('Feature', fontsize=12)
        plt.tight_layout()
        plt.savefig('ml_models/outputs/feature_importance_hold.png', dpi=150)
        logger.info("\n  Saved: feature_importance_hold.png")
        plt.close()
    
    return model, scaler, feature_cols, {'train_acc': train_acc, 'test_acc': test_acc}


def main():
    logger.info("="*100)
    logger.info("ML MODEL TRAINING FOR NBA IN-GAME TRADING")
    logger.info("="*100)
    
    # Load training data
    logger.info("\nLoading training data...")
    df = pd.read_csv('ml_models/outputs/training_data.csv')
    logger.info(f"Loaded {len(df):,} samples from {df['game_id'].nunique()} games")
    
    # Train entry model
    entry_model, entry_scaler, entry_features, entry_results = train_entry_model(df)
    
    # Train hold duration model
    hold_model, hold_scaler, hold_features, hold_results = train_hold_duration_model(df)
    
    # Summary
    logger.info("\n" + "="*100)
    logger.info("TRAINING COMPLETE!")
    logger.info("="*100)
    logger.info("\nModels saved to ml_models/outputs/:")
    logger.info("  Entry Model:")
    logger.info("    - entry_model.pkl")
    logger.info("    - entry_scaler.pkl")
    logger.info("    - entry_features.pkl")
    if hold_model:
        logger.info("  Hold Duration Model:")
        logger.info("    - hold_duration_model.pkl")
        logger.info("    - hold_duration_scaler.pkl")
        logger.info("    - hold_duration_features.pkl")
    logger.info("\nVisualizat ions:")
    logger.info("  - feature_importance_entry.png")
    if hold_model:
        logger.info("  - feature_importance_hold.png")
    logger.info("\n" + "="*100)
    logger.info("READY FOR BACKTESTING!")
    logger.info("="*100)


if __name__ == "__main__":
    main()

