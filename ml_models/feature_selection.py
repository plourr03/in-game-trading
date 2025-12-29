"""
Feature Selection - Find the most predictive features
"""
import pandas as pd
import numpy as np
from sklearn.feature_selection import mutual_info_classif, RFE
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def feature_selection_analysis():
    """Comprehensive feature selection analysis"""
    
    logger.info("="*100)
    logger.info("FEATURE SELECTION ANALYSIS")
    logger.info("="*100)
    
    # Load data
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
    
    # Sample for speed
    sample_size = min(100000, len(X))
    idx = np.random.choice(len(X), sample_size, replace=False)
    X_sample = X.iloc[idx]
    y_sample = y.iloc[idx]
    
    logger.info(f"Using sample of {len(X_sample):,} for feature selection")
    
    results = {}
    
    # Method 1: Mutual Information
    logger.info("\n[1/3] Calculating Mutual Information...")
    mi_scores = mutual_info_classif(X_sample, y_sample, random_state=42)
    mi_df = pd.DataFrame({
        'feature': feature_cols,
        'mi_score': mi_scores
    }).sort_values('mi_score', ascending=False)
    results['mutual_info'] = mi_df
    
    # Method 2: Feature Importance from LightGBM
    logger.info("[2/3] Training LightGBM for feature importance...")
    lgbm = LGBMClassifier(n_estimators=100, max_depth=6, random_state=42, verbose=-1)
    lgbm.fit(X_sample, y_sample)
    
    importance_df = pd.DataFrame({
        'feature': feature_cols,
        'importance': lgbm.feature_importances_
    }).sort_values('importance', ascending=False)
    results['lgbm_importance'] = importance_df
    
    # Method 3: Recursive Feature Elimination
    logger.info("[3/3] Running Recursive Feature Elimination (RFE)...")
    rf = RandomForestClassifier(n_estimators=50, max_depth=8, random_state=42, n_jobs=-1)
    rfe = RFE(estimator=rf, n_features_to_select=15, step=1)
    rfe.fit(X_sample, y_sample)
    
    rfe_df = pd.DataFrame({
        'feature': feature_cols,
        'selected': rfe.support_,
        'ranking': rfe.ranking_
    }).sort_values('ranking')
    results['rfe'] = rfe_df
    
    # Display results
    logger.info("\n" + "="*100)
    logger.info("METHOD 1: MUTUAL INFORMATION (Top 15)")
    logger.info("="*100)
    print()
    print(mi_df.head(15).to_string(index=False))
    
    logger.info("\n" + "="*100)
    logger.info("METHOD 2: LIGHTGBM FEATURE IMPORTANCE (Top 15)")
    logger.info("="*100)
    print()
    print(importance_df.head(15).to_string(index=False))
    
    logger.info("\n" + "="*100)
    logger.info("METHOD 3: RECURSIVE FEATURE ELIMINATION (Selected Features)")
    logger.info("="*100)
    selected_features = rfe_df[rfe_df['selected']]['feature'].tolist()
    print()
    print("Selected Features:", selected_features)
    
    # Consensus features (appear in top 15 of all methods)
    logger.info("\n" + "="*100)
    logger.info("CONSENSUS FEATURES (Top in multiple methods)")
    logger.info("="*100)
    
    top_mi = set(mi_df.head(15)['feature'])
    top_importance = set(importance_df.head(15)['feature'])
    top_rfe = set(selected_features)
    
    consensus = top_mi & top_importance & top_rfe
    logger.info(f"\nFeatures in ALL 3 methods ({len(consensus)}):")
    for f in consensus:
        print(f"  • {f}")
    
    consensus_2 = (top_mi & top_importance) | (top_mi & top_rfe) | (top_importance & top_rfe)
    logger.info(f"\nFeatures in at least 2 methods ({len(consensus_2)}):")
    for f in consensus_2:
        print(f"  • {f}")
    
    # Create visualization
    logger.info("\nCreating visualization...")
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    
    # Plot 1: Mutual Information
    top_mi_df = mi_df.head(15)
    axes[0].barh(range(len(top_mi_df)), top_mi_df['mi_score'])
    axes[0].set_yticks(range(len(top_mi_df)))
    axes[0].set_yticklabels(top_mi_df['feature'])
    axes[0].set_xlabel('Mutual Information Score')
    axes[0].set_title('Top 15 Features by Mutual Information')
    axes[0].invert_yaxis()
    
    # Plot 2: LightGBM Importance
    top_imp_df = importance_df.head(15)
    axes[1].barh(range(len(top_imp_df)), top_imp_df['importance'])
    axes[1].set_yticks(range(len(top_imp_df)))
    axes[1].set_yticklabels(top_imp_df['feature'])
    axes[1].set_xlabel('Feature Importance')
    axes[1].set_title('Top 15 Features by LightGBM Importance')
    axes[1].invert_yaxis()
    
    plt.tight_layout()
    plt.savefig('ml_models/outputs/feature_selection.png', dpi=150, bbox_inches='tight')
    logger.info("  Saved: ml_models/outputs/feature_selection.png")
    plt.close()
    
    # Save results
    logger.info("\nSaving selected features...")
    import json
    
    feature_sets = {
        'top_10_mi': mi_df.head(10)['feature'].tolist(),
        'top_10_importance': importance_df.head(10)['feature'].tolist(),
        'top_15_mi': mi_df.head(15)['feature'].tolist(),
        'top_15_importance': importance_df.head(15)['feature'].tolist(),
        'rfe_selected': selected_features,
        'consensus_all': list(consensus),
        'consensus_2_of_3': list(consensus_2)
    }
    
    with open('ml_models/outputs/selected_features.json', 'w') as f:
        json.dump(feature_sets, f, indent=2)
    
    logger.info("  Saved: ml_models/outputs/selected_features.json")
    
    # Recommendation
    logger.info("\n" + "="*100)
    logger.info("RECOMMENDATION")
    logger.info("="*100)
    logger.info(f"\nBest feature set: Top {len(consensus_2)} features (consensus of 2+ methods)")
    logger.info("\nThese features capture the most predictive information while reducing noise.")
    logger.info("\nNext step: Retrain LightGBM with selected features for improved performance!")
    logger.info("="*100)
    
    return feature_sets


if __name__ == "__main__":
    feature_sets = feature_selection_analysis()




