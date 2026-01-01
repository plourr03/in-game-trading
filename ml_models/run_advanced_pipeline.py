"""
Complete pipeline: Create features -> Train models -> Test thresholds
"""
import subprocess
import sys
import os
import time

def run_pipeline():
    """Run complete ML pipeline with advanced features"""
    
    print("="*100)
    print("🚀 ADVANCED FEATURES ML PIPELINE")
    print("="*100)
    
    # Step 1: Create features (if not already done)
    if not os.path.exists('ml_models/outputs/advanced_training_data.csv'):
        print("\n[1/3] Creating advanced features...")
        result = subprocess.run([sys.executable, 'ml_models/create_advanced_features.py'], 
                              capture_output=False)
        if result.returncode != 0:
            print("❌ Feature creation failed!")
            return
    else:
        print("\n[1/3] ✅ Features already created!")
    
    # Step 2: Train models
    print("\n[2/3] Training models...")
    result = subprocess.run([sys.executable, 'ml_models/train_advanced_features_model.py'],
                          capture_output=False)
    if result.returncode != 0:
        print("❌ Training failed!")
        return
    
    # Step 3: Test thresholds
    print("\n[3/3] Testing thresholds...")
    result = subprocess.run([sys.executable, 'ml_models/test_advanced_model.py'],
                          capture_output=False)
    if result.returncode != 0:
        print("❌ Testing failed!")
        return
    
    print("\n" + "="*100)
    print("✅ PIPELINE COMPLETE!")
    print("="*100)
    print("\nResults saved to:")
    print("  - ml_models/outputs/advanced_model.pkl")
    print("  - ml_models/outputs/advanced_threshold_results.csv")


if __name__ == "__main__":
    run_pipeline()





