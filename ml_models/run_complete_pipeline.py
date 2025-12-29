"""
Master script to run complete ML pipeline
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.helpers import get_logger

logger = get_logger(__name__)


def main():
    logger.info("="*100)
    logger.info("COMPLETE ML PIPELINE FOR NBA IN-GAME TRADING")
    logger.info("="*100)
    logger.info("\nThis will:")
    logger.info("  1. Prepare training dataset from historical data")
    logger.info("  2. Train entry prediction model")
    logger.info("  3. Train hold duration optimizer")
    logger.info("  4. Backtest ML vs rules-based strategies")
    logger.info("\n" + "="*100)
    
    # Step 1: Prepare data
    logger.info("\n\n")
    logger.info("="*100)
    logger.info("STEP 1/3: PREPARE TRAINING DATA")
    logger.info("="*100)
    
    try:
        from ml_models.prepare_training_data import prepare_ml_dataset
        df = prepare_ml_dataset()
        logger.info("\n SUCCESS! Training data prepared.")
    except Exception as e:
        logger.error(f"\n ERROR preparing data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Train models
    logger.info("\n\n")
    logger.info("="*100)
    logger.info("STEP 2/3: TRAIN ML MODELS")
    logger.info("="*100)
    
    try:
        from ml_models.train_models import main as train_main
        train_main()
        logger.info("\n SUCCESS! Models trained.")
    except Exception as e:
        logger.error(f"\n ERROR training models: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: Backtest
    logger.info("\n\n")
    logger.info("="*100)
    logger.info("STEP 3/3: BACKTEST COMPARISON")
    logger.info("="*100)
    
    try:
        from ml_models.backtest_comparison import run_backtest_comparison
        run_backtest_comparison()
        logger.info("\n SUCCESS! Backtest complete.")
    except Exception as e:
        logger.error(f"\n ERROR backtesting: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Final summary
    logger.info("\n\n")
    logger.info("="*100)
    logger.info("PIPELINE COMPLETE!")
    logger.info("="*100)
    logger.info("\nAll outputs saved to ml_models/outputs/:")
    logger.info("\nData:")
    logger.info("  - training_data.csv")
    logger.info("\nModels:")
    logger.info("  - entry_model.pkl")
    logger.info("  - entry_scaler.pkl")
    logger.info("  - entry_features.pkl")
    logger.info("  - hold_duration_model.pkl (if enough data)")
    logger.info("  - hold_duration_scaler.pkl")
    logger.info("  - hold_duration_features.pkl")
    logger.info("\nVisualizations:")
    logger.info("  - feature_importance_entry.png")
    logger.info("  - feature_importance_hold.png")
    logger.info("\nBacktest Results:")
    logger.info("  - ml_backtest_trades.csv")
    logger.info("  - rules_backtest_trades.csv")
    logger.info("\n" + "="*100)
    logger.info("Next: Review results and integrate into trading_engine if ML performs better!")
    logger.info("="*100)


if __name__ == "__main__":
    main()




