"""
Add comprehensive play-by-play features to find more trading opportunities
"""
import pandas as pd
import numpy as np
import yaml
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.loader import load_kalshi_games, load_pbp_data, connect_to_pbp_db
from src.data.preprocessor import fill_prices, calculate_game_minute
from src.data.aligner import align_pbp_to_minutes, merge_kalshi_pbp
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def create_advanced_pbp_features():
    """Create comprehensive PBP features for better prediction"""
    
    logger.info("="*100)
    logger.info("CREATING ADVANCED PLAY-BY-PLAY FEATURES")
    logger.info("="*100)
    
    # Load Kalshi data
    logger.info("\n[1/5] Loading Kalshi data...")
    kalshi_df = load_kalshi_games()
    kalshi_df = fill_prices(kalshi_df)
    kalshi_df['datetime'] = pd.to_datetime(kalshi_df['datetime'])
    kalshi_df['game_minute'] = kalshi_df['datetime'].dt.hour * 60 + kalshi_df['datetime'].dt.minute
    logger.info(f"      Loaded {len(kalshi_df):,} rows from {kalshi_df['game_id'].nunique()} games")
    
    # Load PBP data
    logger.info("\n[2/5] Loading play-by-play data...")
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    db_config = config['database']
    conn = connect_to_pbp_db(**db_config)
    
    pbp_game_ids = kalshi_df['game_id'].unique().tolist()
    pbp_df = load_pbp_data(pbp_game_ids, conn)
    logger.info(f"      Loaded {len(pbp_df):,} play-by-play events")
    
    # Merge
    logger.info("\n[3/5] Merging Kalshi and play-by-play data...")
    pbp_by_minute = align_pbp_to_minutes(pbp_df)
    
    all_merged = []
    for game_id in kalshi_df['game_id'].unique():
        game_kalshi = kalshi_df[kalshi_df['game_id'] == game_id].copy()
        game_pbp = pbp_by_minute[pbp_by_minute['game_id'] == game_id].copy() if game_id in pbp_by_minute['game_id'].values else pd.DataFrame()
        
        if len(game_pbp) > 0:
            merged = pd.merge(
                game_kalshi,
                game_pbp[['game_id', 'game_minute', 'score_home', 'score_away']],
                on=['game_id', 'game_minute'],
                how='left'
            )
        else:
            merged = game_kalshi.copy()
            merged['score_home'] = 0
            merged['score_away'] = 0
        
        all_merged.append(merged)
    
    merged_df = pd.concat(all_merged, ignore_index=True)
    
    # Fill scores
    merged_df['score_home'] = pd.to_numeric(merged_df['score_home'], errors='coerce').ffill().bfill().fillna(0)
    merged_df['score_away'] = pd.to_numeric(merged_df['score_away'], errors='coerce').ffill().bfill().fillna(0)
    
    logger.info("\n[4/5] Engineering COMPREHENSIVE features...")
    
    df = merged_df.copy()
    
    # Basic price features
    logger.info("  - Price features...")
    df['current_price'] = df['close']
    df['spread'] = df['high'] - df['low']
    df['price_move_1min'] = df.groupby('game_id')['close'].pct_change() * 100
    df['price_move_2min'] = df.groupby('game_id')['close'].pct_change(2) * 100
    df['price_move_3min'] = df.groupby('game_id')['close'].pct_change(3) * 100
    df['price_move_5min'] = df.groupby('game_id')['close'].pct_change(5) * 100
    df['price_move_10min'] = df.groupby('game_id')['close'].pct_change(10) * 100
    df['volatility_3min'] = df.groupby('game_id')['close'].rolling(3).std().reset_index(0, drop=True)
    df['volatility_5min'] = df.groupby('game_id')['close'].rolling(5).std().reset_index(0, drop=True)
    df['volatility_10min'] = df.groupby('game_id')['close'].rolling(10).std().reset_index(0, drop=True)
    
    # Volume features
    logger.info("  - Volume features...")
    df['volume_ma3'] = df.groupby('game_id')['volume'].rolling(3).mean().reset_index(0, drop=True)
    df['volume_ma5'] = df.groupby('game_id')['volume'].rolling(5).mean().reset_index(0, drop=True)
    df['volume_ma10'] = df.groupby('game_id')['volume'].rolling(10).mean().reset_index(0, drop=True)
    df['volume_spike'] = df['volume'] / (df['volume_ma5'] + 1e-6)
    df['volume_trend'] = df.groupby('game_id')['volume'].pct_change(5) * 100
    
    # Score-based features
    logger.info("  - Score features...")
    df['score_diff'] = df['score_home'] - df['score_away']
    df['score_diff_abs'] = df['score_diff'].abs()
    df['score_total'] = df['score_home'] + df['score_away']
    df['score_diff_1min'] = df.groupby('game_id')['score_diff'].diff(1)
    df['score_diff_3min'] = df.groupby('game_id')['score_diff'].diff(3)
    df['score_diff_5min'] = df.groupby('game_id')['score_diff'].diff(5)
    df['scoring_rate_1min'] = df.groupby('game_id')['score_total'].diff(1)
    df['scoring_rate_3min'] = df.groupby('game_id')['score_total'].diff(3) / 3
    df['scoring_rate_5min'] = df.groupby('game_id')['score_total'].diff(5) / 5
    
    # Momentum features
    logger.info("  - Momentum features...")
    df['home_momentum_3min'] = df.groupby('game_id')['score_home'].diff(3)
    df['away_momentum_3min'] = df.groupby('game_id')['score_away'].diff(3)
    df['home_momentum_5min'] = df.groupby('game_id')['score_home'].diff(5)
    df['away_momentum_5min'] = df.groupby('game_id')['score_away'].diff(5)
    df['lead_change_recent'] = (df.groupby('game_id')['score_diff'].apply(lambda x: (x * x.shift(1)) < 0).reset_index(0, drop=True)).astype(int)
    
    # Game state features
    logger.info("  - Game state features...")
    df['time_remaining'] = df.groupby('game_id')['game_minute'].transform('max') - df['game_minute']
    df['period'] = (df['game_minute'] // 12 + 1).clip(upper=4)
    df['minutes_into_period'] = df['game_minute'] % 12
    df['is_period_1'] = (df['period'] == 1).astype(int)
    df['is_period_2'] = (df['period'] == 2).astype(int)
    df['is_period_3'] = (df['period'] == 3).astype(int)
    df['is_period_4'] = (df['period'] == 4).astype(int)
    df['is_early_period'] = (df['minutes_into_period'] <= 3).astype(int)
    df['is_late_period'] = (df['minutes_into_period'] >= 9).astype(int)
    
    # Binary indicators
    logger.info("  - Binary indicators...")
    df['is_close_game'] = (df['score_diff_abs'] <= 5).astype(int)
    df['is_very_close'] = (df['score_diff_abs'] <= 3).astype(int)
    df['is_blowout'] = (df['score_diff_abs'] >= 15).astype(int)
    df['is_late_game'] = (df['time_remaining'] <= 5).astype(int)
    df['is_very_late'] = (df['time_remaining'] <= 2).astype(int)
    df['is_crunch_time'] = ((df['time_remaining'] <= 5) & (df['score_diff_abs'] <= 5)).astype(int)
    df['is_extreme_low'] = (df['current_price'] <= 10).astype(int)
    df['is_extreme_high'] = (df['current_price'] >= 90).astype(int)
    df['is_extreme_price'] = (df['is_extreme_low'] | df['is_extreme_high']).astype(int)
    df['is_mid_price'] = ((df['current_price'] > 40) & (df['current_price'] < 60)).astype(int)
    df['large_move'] = (df['price_move_1min'].abs() > 5).astype(int)
    df['huge_move'] = (df['price_move_1min'].abs() > 10).astype(int)
    df['price_accelerating'] = ((df['price_move_1min'].abs() > df.groupby('game_id')['price_move_1min'].shift(1).abs())).astype(int)
    
    # Relative features
    logger.info("  - Relative features...")
    df['score_vs_expectation'] = df['score_total'] - (df['game_minute'] * 2.2)  # Expected ~100 points per game
    df['pace'] = df['score_total'] / (df['game_minute'] + 1)
    df['price_score_alignment'] = (np.sign(df['current_price'] - 50) == np.sign(df['score_diff'])).astype(int)
    df['price_score_misalignment'] = (~df['price_score_alignment'].astype(bool)).astype(int)
    
    # Advanced patterns
    logger.info("  - Pattern features...")
    df['consecutive_scores'] = (df['scoring_rate_1min'] > 0).astype(int)
    df['scoring_drought'] = (df['scoring_rate_3min'] < 2).astype(int)
    df['high_scoring'] = (df['scoring_rate_3min'] > 5).astype(int)
    df['comeback_attempt'] = ((df['score_diff'] < 0) & (df['home_momentum_3min'] > df['away_momentum_3min'])).astype(int)
    
    # Price patterns
    logger.info("  - Price pattern features...")
    df['price_reversing'] = (np.sign(df['price_move_1min']) != np.sign(df.groupby('game_id')['price_move_1min'].shift(1))).astype(int)
    df['price_trending_up'] = ((df['price_move_1min'] > 0) & (df.groupby('game_id')['price_move_1min'].shift(1) > 0)).astype(int)
    df['price_trending_down'] = ((df['price_move_1min'] < 0) & (df.groupby('game_id')['price_move_1min'].shift(1) < 0)).astype(int)
    df['price_range_5min'] = df.groupby('game_id')['close'].rolling(5).apply(lambda x: x.max() - x.min()).reset_index(0, drop=True)
    
    # Create target
    logger.info("  - Creating targets...")
    df['future_price_1min'] = df.groupby('game_id')['close'].shift(-1)
    df['future_price_3min'] = df.groupby('game_id')['close'].shift(-3)
    df['future_price_5min'] = df.groupby('game_id')['close'].shift(-5)
    df['future_price_7min'] = df.groupby('game_id')['close'].shift(-7)
    
    df['profit_1min'] = df['future_price_1min'] - df['current_price']
    df['profit_3min'] = df['future_price_3min'] - df['current_price']
    df['profit_5min'] = df['future_price_5min'] - df['current_price']
    df['profit_7min'] = df['future_price_7min'] - df['current_price']
    
    # Target: any hold period profitable
    df['any_profitable'] = ((df['profit_3min'] > 3) | (df['profit_5min'] > 3) | (df['profit_7min'] > 3)).astype(int)
    
    # Drop NaN
    logger.info("  - Cleaning data...")
    df = df.fillna(0)
    df = df[df['time_remaining'] > 0]  # Remove last minute
    
    logger.info(f"\n[5/5] Feature engineering complete!")
    logger.info(f"      Total features: {len([c for c in df.columns if c not in ['game_id', 'datetime', 'game_minute']])-10}")
    logger.info(f"      Total samples: {len(df):,}")
    logger.info(f"      Positive rate: {df['any_profitable'].mean():.1%}")
    
    # Save
    output_path = 'ml_models/outputs/advanced_training_data.csv'
    df.to_csv(output_path, index=False)
    logger.info(f"\n      Saved: {output_path}")
    
    return df


if __name__ == "__main__":
    df = create_advanced_pbp_features()

