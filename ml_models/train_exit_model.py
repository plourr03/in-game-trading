"""
Train Exit Timing Model
Trains a LightGBM classifier to predict optimal exit points
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import matplotlib.pyplot as plt

print("="*80)
print("TRAINING EXIT TIMING MODEL")
print("="*80)

# Load training data
print("\nLoading training data...")
df = pd.read_csv('ml_models/exit_training_data.csv')
print(f"[OK] Loaded {len(df):,} examples from {df['game_id'].nunique()} games")

# Separate features and labels
feature_cols = [c for c in df.columns if c not in ['label', 'game_id']]
X = df[feature_cols]
y = df['label']

print(f"\nFeatures: {len(feature_cols)}")
print(f"Label distribution: HOLD={y.value_counts()[0]:,}, EXIT={y.value_counts()[1]:,}")

# Split by games to prevent leakage
unique_games = df['game_id'].unique()
train_games, test_games = train_test_split(unique_games, test_size=0.2, random_state=42)

train_mask = df['game_id'].isin(train_games)
test_mask = df['game_id'].isin(test_games)

X_train = X[train_mask]
y_train = y[train_mask]
X_test = X[test_mask]
y_test = y[test_mask]

print(f"\nTrain set: {len(X_train):,} examples ({len(train_games)} games)")
print(f"Test set: {len(X_test):,} examples ({len(test_games)} games)")

# Handle class imbalance
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"\nClass imbalance ratio: {scale_pos_weight:.2f}")
print(f"Using scale_pos_weight for LightGBM")

# Train LightGBM model
print("\nTraining LightGBM model...")
print("-"*80)

params = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'scale_pos_weight': scale_pos_weight,
    'verbose': -1,
    'max_depth': 7,
    'min_data_in_leaf': 50
}

train_data = lgb.Dataset(X_train, label=y_train)
test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

model = lgb.train(
    params,
    train_data,
    num_boost_round=500,
    valid_sets=[train_data, test_data],
    valid_names=['train', 'test'],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50),
        lgb.log_evaluation(period=50)
    ]
)

print("\n[OK] Training complete!")

# Evaluate
print("\n" + "="*80)
print("MODEL EVALUATION")
print("="*80)

# Predictions
y_pred_proba = model.predict(X_test)
y_pred = (y_pred_proba > 0.5).astype(int)

# Metrics
auc = roc_auc_score(y_test, y_pred_proba)
print(f"\nAUC: {auc:.4f}")

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['HOLD', 'EXIT']))

print("\nConfusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(f"             Predicted")
print(f"              HOLD    EXIT")
print(f"Actual HOLD   {cm[0,0]:>7,}  {cm[0,1]:>7,}")
print(f"       EXIT   {cm[1,0]:>7,}  {cm[1,1]:>7,}")

# Feature importance
print("\n" + "="*80)
print("FEATURE IMPORTANCE")
print("="*80)

feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importance(importance_type='gain')
}).sort_values('importance', ascending=False)

print("\nTop 15 features:")
for idx, row in feature_importance.head(15).iterrows():
    print(f"  {row['feature']:<30} {row['importance']:>10,.0f}")

# Plot feature importance
plt.figure(figsize=(10, 8))
top_features = feature_importance.head(15)
plt.barh(range(len(top_features)), top_features['importance'])
plt.yticks(range(len(top_features)), top_features['feature'])
plt.xlabel('Importance (Gain)')
plt.title('Top 15 Feature Importance - Exit Timing Model')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig('ml_models/exit_model_feature_importance.png', dpi=150)
print("\n[OK] Feature importance plot saved")

# Save model and features
print("\n" + "="*80)
print("SAVING MODEL")
print("="*80)

os.makedirs('ml_models/outputs', exist_ok=True)

model_file = 'ml_models/outputs/exit_timing_dynamic.pkl'
features_file = 'ml_models/outputs/exit_features.pkl'

joblib.dump(model, model_file)
joblib.dump(feature_cols, features_file)

print(f"[OK] Model saved to: {model_file}")
print(f"[OK] Features saved to: {features_file}")

# Test at different thresholds
print("\n" + "="*80)
print("THRESHOLD ANALYSIS")
print("="*80)

thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
print(f"\n{'Threshold':<12} {'Exit Rate':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12}")
print("-"*60)

for threshold in thresholds:
    y_pred_thresh = (y_pred_proba > threshold).astype(int)
    
    exit_rate = y_pred_thresh.sum() / len(y_pred_thresh)
    
    from sklearn.metrics import precision_score, recall_score, f1_score
    precision = precision_score(y_test, y_pred_thresh)
    recall = recall_score(y_test, y_pred_thresh)
    f1 = f1_score(y_test, y_pred_thresh)
    
    print(f"{threshold:<12.1f} {exit_rate:<12.1%} {precision:<12.3f} {recall:<12.3f} {f1:<12.3f}")

print("\n" + "="*80)
print("TRAINING COMPLETE")
print("="*80)
print(f"Model: {model_file}")
print(f"AUC: {auc:.4f}")
print(f"Ready for backtesting!")
print("="*80)

