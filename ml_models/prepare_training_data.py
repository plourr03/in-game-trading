"""
Prepare training dataset from historical data with all features
"""
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.loader import load_kalshi_games, load_pbp_data, connect_to_pbp_db
from src.data.preprocessor import fill_prices, calculate_game_minute
from src.data.aligner import align_pbp_to_minutes, merge_kalshi_pbp
from src.backtesting.fees import calculate_kalshi_fees
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def prepare_ml_dataset():
    """
    Create comprehensive ML dataset with all features and targets
    """
    logger.info("="*100)
    logger.info("PREPARING ML TRAINING DATASET")
    logger.info("="*100)
    
    # [1/6] Load Kalshi data
    logger.info("\n[1/6] Loading Kalshi data...")
    kalshi_df = load_kalshi_games()
    kalshi_df = fill_prices(kalshi_df)
    kalshi_df['datetime'] = pd.to_datetime(kalshi_df['datetime'])
    kalshi_df['game_minute'] = kalshi_df['datetime'].dt.hour * 60 + kalshi_df['datetime'].dt.minute
    logger.info(f"      Loaded {len(kalshi_df):,} rows from {kalshi_df['game_id'].nunique()} games")
    
    # [2/6] Load play-by-play data (optional - skip if no data)
    logger.info("[2/6] Loading play-by-play data...")
    try:
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        db_config = config['database']
        conn = connect_to_pbp_db(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password']
        )
        pbp_df = load_pbp_data(kalshi_df['game_id'].unique().tolist(), conn)
        logger.info(f"      Loaded {len(pbp_df):,} play-by-play events")
        
        if len(pbp_df) > 0:
            # [3/6] Merge data
            logger.info("[3/6] Merging Kalshi and play-by-play data...")
            pbp_by_minute = align_pbp_to_minutes(pbp_df)
            merged_df = merge_kalshi_pbp(kalshi_df, pbp_by_minute)
            logger.info(f"      Merged dataset: {len(merged_df):,} rows")
        else:
            logger.warning("      No PBP data found - using Kalshi data only")
            merged_df = kalshi_df.copy()
    except Exception as e:
        logger.warning(f"      Could not load PBP data ({e}) - using Kalshi data only")
        merged_df = kalshi_df.copy()
    
    # [4/6] Feature engineering
    logger.info("[4/6] Engineering features...")
    features_df = pd.DataFrame()
    
    # Copy IDs
    features_df['game_id'] = merged_df['game_id'].values
    features_df['game_minute'] = merged_df['game_minute'].values
    
    # Price features
    logger.info("      - Price features...")
    features_df['current_price'] = merged_df['close'].values
    features_df['price_move_1min'] = merged_df.groupby('game_id')['close'].pct_change() * 100
    features_df['price_move_3min'] = merged_df.groupby('game_id')['close'].pct_change(3) * 100
    features_df['price_move_5min'] = merged_df.groupby('game_id')['close'].pct_change(5) * 100
    features_df['volatility_5min'] = merged_df.groupby('game_id')['close'].rolling(5).std().reset_index(0, drop=True)
    
    # Market microstructure
    logger.info("      - Market features...")
    features_df['spread'] = (merged_df['high'] - merged_df['low']).values
    features_df['volume'] = merged_df['volume'].values
    features_df['volume_ma5'] = merged_df.groupby('game_id')['volume'].rolling(5).mean().reset_index(0, drop=True)
    features_df['volume_spike'] = features_df['volume'] / (features_df['volume_ma5'] + 1e-6)
    
    # Game state features
    logger.info("      - Game state features...")
    if 'score_home' in merged_df.columns and 'score_away' in merged_df.columns:
        features_df['score_diff'] = (merged_df['score_home'] - merged_df['score_away']).values
        features_df['score_diff_abs'] = features_df['score_diff'].abs()
        features_df['total_score'] = (merged_df['score_home'] + merged_df['score_away']).values
        
        # Scoring rate (change in total score over last 3 minutes)
        features_df['scoring_rate_3min'] = merged_df.groupby('game_id')['total_score'].diff(3).fillna(0)
        
        # Score momentum (is score differential increasing/decreasing)
        features_df['score_momentum'] = merged_df.groupby('game_id')['score_diff'].diff(1).fillna(0)
        
        # Is leading team extending lead?
        features_df['lead_extending'] = (
            (features_df['score_diff'].abs() > 5) & 
            (features_df['score_momentum'].abs() > 0)
        ).astype(int)
        
        logger.info(f"        Added PBP game state features")
    else:
        logger.warning("        No PBP score data - using placeholders")
        features_df['score_diff'] = 0
        features_df['score_diff_abs'] = 0
        features_df['total_score'] = 0
        features_df['scoring_rate_3min'] = 0
        features_df['score_momentum'] = 0
        features_df['lead_extending'] = 0
    
    # Time features
    features_df['time_remaining'] = merged_df.groupby('game_id')['game_minute'].transform('max') - merged_df['game_minute']
    if 'period' in merged_df.columns:
        features_df['period'] = merged_df['period'].values
    else:
        features_df['period'] = (merged_df['game_minute'] // 12 + 1).clip(upper=4)
    
    # Price regime
    logger.info("      - Price regime features...")
    features_df['is_extreme_low'] = (features_df['current_price'] <= 10).astype(int)
    features_df['is_extreme_high'] = (features_df['current_price'] >= 90).astype(int)
    features_df['is_extreme_price'] = (features_df['is_extreme_low'] | features_df['is_extreme_high']).astype(int)
    features_df['is_mid_price'] = ((features_df['current_price'] > 40) & (features_df['current_price'] < 60)).astype(int)
    
    # Context features
    logger.info("      - Context features...")
    features_df['is_close_game'] = (features_df['score_diff_abs'] <= 5).astype(int)
    features_df['is_late_game'] = (features_df['time_remaining'] <= 5).astype(int)
    features_df['is_very_late'] = (features_df['time_remaining'] <= 2).astype(int)
    
    # Mean reversion signal (large moves)
    features_df['large_move'] = (features_df['price_move_1min'].abs() > 5).astype(int)
    features_df['huge_move'] = (features_df['price_move_1min'].abs() > 10).astype(int)
    
    # Historical pattern (autocorrelation proxy)
    features_df['price_lag1'] = merged_df.groupby('game_id')['close'].shift(1).values
    features_df['price_lag2'] = merged_df.groupby('game_id')['close'].shift(2).values
    
    # [5/6] Create target variables
    logger.info("[5/6] Creating target variables (looking ahead)...")
    
    for hold_period in [3, 5, 7, 12, 15]:
        # Future price
        future_price = merged_df.groupby('game_id')['close'].shift(-hold_period).values
        entry_price = features_df['current_price'].values
        
        # Calculate P/L assuming mean reversion (fade) strategy
        # If price moved up, we bet it goes down (short)
        # If price moved down, we bet it goes up (long)
        price_move_direction = np.sign(features_df['price_move_1min'].fillna(0).values)
        
        # Calculate raw P/L
        raw_pl = np.where(
            price_move_direction > 0,
            entry_price - future_price,  # Short: profit if price goes down
            future_price - entry_price   # Long: profit if price goes up
        )
        
        # Calculate fees
        entry_fees = []
        exit_fees = []
        for i in range(len(features_df)):
            if not np.isnan(entry_price[i]) and not np.isnan(future_price[i]):
                entry_fees.append(calculate_kalshi_fees(100, entry_price[i], is_taker=True))
                exit_fees.append(calculate_kalshi_fees(100, future_price[i], is_taker=True))
            else:
                entry_fees.append(0)
                exit_fees.append(0)
        
        total_fees = np.array(entry_fees) + np.array(exit_fees)
        
        # Net P/L
        net_pl = raw_pl - total_fees
        
        # Targets
        features_df[f'future_price_{hold_period}min'] = future_price
        features_df[f'net_pl_{hold_period}min'] = net_pl
        features_df[f'profitable_{hold_period}min'] = (net_pl > 0.50).astype(int)
        features_df[f'very_profitable_{hold_period}min'] = (net_pl > 2.0).astype(int)
    
    # Determine optimal hold period (highest P/L)
    pl_cols = [f'net_pl_{h}min' for h in [3, 5, 7, 12, 15]]
    features_df['best_pl'] = features_df[pl_cols].max(axis=1)
    features_df['optimal_hold'] = features_df[pl_cols].idxmax(axis=1).str.extract('(\d+)').astype(float)
    
    # Binary: is any hold period profitable?
    profitable_cols = [f'profitable_{h}min' for h in [3, 5, 7, 12, 15]]
    features_df['any_profitable'] = features_df[profitable_cols].max(axis=1)
    
    logger.info(f"      Created targets for hold periods: 3, 5, 7, 12, 15 minutes")
    
    # [6/6] Clean and save
    logger.info("[6/6] Cleaning and saving dataset...")
    
    # Drop rows with critical NaN values
    initial_len = len(features_df)
    features_df = features_df.dropna(subset=['current_price', 'price_move_1min', 'any_profitable'])
    logger.info(f"      Dropped {initial_len - len(features_df):,} rows with missing critical values")
    
    # Fill remaining NaNs
    features_df = features_df.fillna(0)
    
    # Save
    output_path = 'ml_models/outputs/training_data.csv'
    features_df.to_csv(output_path, index=False)
    logger.info(f"      Saved to: {output_path}")
    
    # Summary
    logger.info("\n" + "="*100)
    logger.info("DATASET SUMMARY")
    logger.info("="*100)
    logger.info(f"\nTotal samples:          {len(features_df):,}")
    logger.info(f"Games:                  {features_df['game_id'].nunique()}")
    logger.info(f"Features:               {len([c for c in features_df.columns if not c.startswith(('net_pl_', 'profitable_', 'future_', 'game_id', 'best_', 'optimal_', 'any_'))])}")
    
    logger.info("\nTarget Distribution:")
    logger.info(f"  Any hold profitable:  {features_df['any_profitable'].sum():,} ({features_df['any_profitable'].mean():.1%})")
    
    for hold in [3, 5, 7, 12, 15]:
        n_profitable = features_df[f'profitable_{hold}min'].sum()
        pct = features_df[f'profitable_{hold}min'].mean()
        avg_pl = features_df[f'net_pl_{hold}min'].mean()
        logger.info(f"  {hold:2d}min hold:          {n_profitable:,} ({pct:.1%}) | Avg P/L: ${avg_pl:+.2f}")
    
    logger.info("\nPrice Distribution:")
    logger.info(f"  Extreme low (<=10c):  {features_df['is_extreme_low'].sum():,} ({features_df['is_extreme_low'].mean():.1%})")
    logger.info(f"  Mid (40-60c):         {features_df['is_mid_price'].sum():,} ({features_df['is_mid_price'].mean():.1%})")
    logger.info(f"  Extreme high (>=90c): {features_df['is_extreme_high'].sum():,} ({features_df['is_extreme_high'].mean():.1%})")
    
    logger.info("\nMove Distribution:")
    logger.info(f"  Large moves (>5%):    {features_df['large_move'].sum():,} ({features_df['large_move'].mean():.1%})")
    logger.info(f"  Huge moves (>10%):    {features_df['huge_move'].sum():,} ({features_df['huge_move'].mean():.1%})")
    
    logger.info("\n" + "="*100)
    logger.info("READY FOR MODEL TRAINING!")
    logger.info("="*100)
    
    return features_df


if __name__ == "__main__":
    df = prepare_ml_dataset()

