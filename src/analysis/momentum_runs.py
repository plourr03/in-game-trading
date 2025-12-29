"""Momentum and run analysis - Area 4"""
import pandas as pd
import numpy as np
from typing import Dict, List
from ..features.momentum import detect_runs
from ..utils.helpers import get_logger

logger = get_logger(__name__)


def run_detection_pipeline(pbp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify all scoring runs (6-0, 8-0, 10-0, etc).
    
    Args:
        pbp_df: Play-by-play data
        
    Returns:
        DataFrame with run information
    """
    logger.info("Running full run detection pipeline...")
    
    # Detect runs of various sizes
    all_runs = []
    for min_points in [6, 8, 10, 12, 15]:
        runs = detect_runs(pbp_df, min_points=min_points)
        runs['min_threshold'] = min_points
        all_runs.append(runs)
    
    if all_runs:
        combined = pd.concat(all_runs, ignore_index=True)
        logger.info(f"Detected {len(combined)} total runs")
        return combined
    
    return pd.DataFrame()


def price_during_vs_after_run(merged_df: pd.DataFrame, runs_df: pd.DataFrame) -> Dict:
    """
    Compare price movement during runs vs after runs end.
    
    Args:
        merged_df: Merged Kalshi + PBP data
        runs_df: Detected runs
        
    Returns:
        Dictionary with run price statistics
    """
    logger.info("Analyzing price behavior during and after runs...")
    
    results = {
        'runs_analyzed': len(runs_df),
        'by_run_size': {},
        'overall': {}
    }
    
    price_changes_during = []
    price_changes_after = []
    
    for _, run in runs_df.iterrows():
        game_data = merged_df[merged_df['game_id'] == run['game_id']]
        
        # Price change during run
        run_data = game_data[
            (game_data['game_minute'] >= run['start_minute']) &
            (game_data['game_minute'] <= run['end_minute'])
        ]
        
        if len(run_data) >= 2:
            price_during = run_data['close'].iloc[-1] - run_data['close'].iloc[0]
            price_changes_during.append(price_during)
            
            # Price change after run (next 3 minutes)
            post_run = game_data[
                (game_data['game_minute'] > run['end_minute']) &
                (game_data['game_minute'] <= run['end_minute'] + 3)
            ]
            
            if len(post_run) > 0:
                price_after = post_run['close'].iloc[-1] - run_data['close'].iloc[-1]
                price_changes_after.append(price_after)
    
    if price_changes_during:
        results['overall']['mean_price_change_during'] = np.mean(price_changes_during)
        results['overall']['std_price_change_during'] = np.std(price_changes_during)
    
    if price_changes_after:
        results['overall']['mean_price_change_after'] = np.mean(price_changes_after)
        results['overall']['std_price_change_after'] = np.std(price_changes_after)
        
        # Check for reversals
        reversals = sum(1 for d, a in zip(price_changes_during, price_changes_after) 
                       if (d > 0 and a < 0) or (d < 0 and a > 0))
        results['overall']['reversal_rate'] = reversals / len(price_changes_after)
    
    return results


def run_reversal_probability(runs_df: pd.DataFrame, pbp_df: pd.DataFrame) -> Dict:
    """
    After 8-0 run, what % of time does opponent score next?
    
    Args:
        runs_df: Detected runs
        pbp_df: Play-by-play data
        
    Returns:
        Dictionary with reversal probabilities by run size
    """
    logger.info("Calculating run reversal probabilities...")
    
    results = {}
    
    for min_points in [6, 8, 10, 12]:
        relevant_runs = runs_df[runs_df['points'] >= min_points]
        reversals = 0
        total = 0
        
        for _, run in relevant_runs.iterrows():
            # Find next scoring event after run
            game_pbp = pbp_df[pbp_df['game_id'] == run['game_id']]
            next_scores = game_pbp[
                (game_pbp['game_minute'] > run['end_minute']) &
                (game_pbp['action_type'] == 'Made Shot')
            ].sort_values('game_minute')
            
            if len(next_scores) > 0:
                next_scorer = next_scores.iloc[0]['location']
                if next_scorer != run['team']:
                    reversals += 1
                total += 1
        
        if total > 0:
            results[f'{min_points}pt_run'] = {
                'reversal_rate': reversals / total,
                'total_runs': total
            }
    
    return results


def clutch_run_premium(merged_df: pd.DataFrame, runs_df: pd.DataFrame) -> Dict:
    """
    Compare price impact of Q4 runs vs Q1 runs.
    
    Args:
        merged_df: Merged data with period info
        runs_df: Detected runs
        
    Returns:
        Dictionary comparing run impacts by quarter
    """
    logger.info("Analyzing clutch run premium...")
    
    results = {'by_period': {}}
    
    for period in [1, 2, 3, 4]:
        # Get runs in this period
        period_runs = []
        
        for _, run in runs_df.iterrows():
            game_data = merged_df[
                (merged_df['game_id'] == run['game_id']) &
                (merged_df['game_minute'] >= run['start_minute']) &
                (merged_df['game_minute'] <= run['end_minute'])
            ]
            
            if len(game_data) > 0 and game_data['period'].iloc[0] == period:
                # Calculate price impact
                if len(game_data) >= 2:
                    price_impact = game_data['close'].iloc[-1] - game_data['close'].iloc[0]
                    period_runs.append({
                        'points': run['points'],
                        'price_impact': price_impact,
                        'price_impact_per_point': price_impact / run['points']
                    })
        
        if period_runs:
            df = pd.DataFrame(period_runs)
            results['by_period'][f'Q{period}'] = {
                'count': len(df),
                'mean_price_impact': df['price_impact'].mean(),
                'mean_impact_per_point': df['price_impact_per_point'].mean(),
                'std_impact': df['price_impact'].std()
            }
    
    # Calculate clutch premium (Q4 vs Q1)
    if 'Q4' in results['by_period'] and 'Q1' in results['by_period']:
        q4_impact = results['by_period']['Q4']['mean_impact_per_point']
        q1_impact = results['by_period']['Q1']['mean_impact_per_point']
        results['clutch_premium'] = q4_impact - q1_impact
    
    return results

