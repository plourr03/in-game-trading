"""Main analysis orchestrator script"""
import logging
import sys
from pathlib import Path
from datetime import datetime

# Import data modules
from src.data.loader import load_kalshi_games, connect_to_pbp_db, load_pbp_data
from src.data.preprocessor import fill_prices, add_team_to_kalshi
from src.data.aligner import align_pbp_to_minutes, merge_kalshi_pbp, handle_overtime
from src.data.validator import volume_coverage_report, timestamp_sanity_checks

# Import feature modules
from src.features.basic import compute_period_indicators
from src.features.events import compute_points_by_minute, identify_turnovers_by_minute, count_fouls_by_minute
from src.features.momentum import detect_runs, compute_rolling_points

# Import analysis modules
from src.analysis.price_reactions import price_change_after_event, overreaction_detection, reaction_by_point_value
from src.analysis.microstructure import calculate_spread_proxy, analyze_volume_patterns, liquidity_by_game_state
from src.analysis.momentum_runs import run_detection_pipeline, price_during_vs_after_run
from src.analysis.efficiency import autocorrelation_analysis, simple_rule_backtest
from src.analysis.volatility import volatility_by_minute, volatility_by_score_diff
from src.analysis.segmentation import segment_by_pregame_odds, segment_by_final_margin
from src.analysis.edge_cases import detect_garbage_time, overtime_analysis, comeback_games
from src.analysis.tradability import fee_impact_by_price, optimal_position_sizing

# Import models
from src.models.baseline_winprob import logistic_regression_baseline
from src.models.fair_value import calculate_fair_value, compare_to_market

# Import backtesting
from src.backtesting.rules import SimpleRuleStrategy
from src.backtesting.framework import Backtester

# Import utilities
from src.utils.config import load_config, get_db_config
from src.utils.helpers import get_logger

logger = get_logger(__name__, level=logging.INFO)


def main():
    """Run complete Kalshi NBA trading analysis pipeline."""
    
    logger.info("=" * 80)
    logger.info("KALSHI NBA IN-GAME TRADING ANALYSIS")
    logger.info("=" * 80)
    
    try:
        # Load configuration
        logger.info("\n[1/7] Loading configuration...")
        config = load_config()
        db_config = get_db_config(config)
        
        # Load and prepare data
        logger.info("\n[2/7] Loading and preparing data...")
        kalshi_df = load_kalshi_games(config['paths']['kalshi_data'])
        kalshi_df = fill_prices(kalshi_df)
        kalshi_df = add_team_to_kalshi(kalshi_df)
        
        # Connect to database and load play-by-play
        conn = connect_to_pbp_db(**db_config)
        game_ids = kalshi_df['game_id'].unique().tolist()
        pbp_df = load_pbp_data(game_ids, conn)
        pbp_df = align_pbp_to_minutes(pbp_df)
        pbp_df = handle_overtime(pbp_df)
        
        logger.info(f"Loaded {len(kalshi_df)} Kalshi rows, {len(pbp_df)} PBP events")
        
        # Run data quality checks
        logger.info("\n[3/7] Running data quality validation...")
        volume_report = volume_coverage_report(kalshi_df)
        logger.info(f"Volume coverage: {volume_report['overall_coverage']:.1%}")
        
        # Feature engineering
        logger.info("\n[4/7] Engineering features...")
        
        # Merge data for first game as example
        sample_game_id = kalshi_df['game_id'].iloc[0]
        merged_sample = merge_kalshi_pbp(kalshi_df, pbp_df, sample_game_id)
        logger.info(f"Sample merged data: {len(merged_sample)} rows")
        
        # Detect runs
        runs = run_detection_pipeline(pbp_df)
        logger.info(f"Detected {len(runs)} scoring runs")
        
        # Execute analysis modules
        logger.info("\n[5/7] Executing analysis modules...")
        results = {}
        
        # Price reactions
        logger.info("  - Price reaction analysis...")
        results['price_reactions'] = price_change_after_event(merged_sample, 'Made Shot')
        results['overreactions'] = overreaction_detection(kalshi_df)
        
        # Market microstructure
        logger.info("  - Market microstructure...")
        results['volume_patterns'] = analyze_volume_patterns(kalshi_df)
        results['spread'] = calculate_spread_proxy(kalshi_df).mean()
        
        # Momentum runs
        logger.info("  - Momentum run analysis...")
        results['run_price_behavior'] = price_during_vs_after_run(merged_sample, runs)
        
        # Efficiency tests
        logger.info("  - Market efficiency tests...")
        results['autocorrelation'] = autocorrelation_analysis(kalshi_df)
        
        # Test simple rules
        test_rules = [
            {'name': 'fade_momentum', 'direction': 'sell'},
            {'name': 'contrarian', 'direction': 'sell'},
        ]
        results['rule_backtest'] = simple_rule_backtest(merged_sample, test_rules)
        
        # Volatility
        logger.info("  - Volatility analysis...")
        results['volatility_by_minute'] = volatility_by_minute(kalshi_df)
        results['volatility_by_score'] = volatility_by_score_diff(kalshi_df)
        
        # Segmentation
        logger.info("  - Segmentation analysis...")
        results['segments_pregame'] = segment_by_pregame_odds(kalshi_df)
        results['segments_margin'] = segment_by_final_margin(kalshi_df)
        
        # Edge cases
        logger.info("  - Edge case analysis...")
        results['garbage_time'] = detect_garbage_time(kalshi_df)
        results['overtime'] = overtime_analysis(kalshi_df)
        results['comebacks'] = comeback_games(kalshi_df)
        
        # Tradability
        logger.info("  - Tradability assessment...")
        results['fee_impact'] = fee_impact_by_price()
        results['position_sizing'] = optimal_position_sizing(0.05, 10000, 0.25)
        
        # Generate visualizations
        logger.info("\n[6/7] Generating visualizations...")
        logger.info("  (Visualization outputs not implemented - use results directly)")
        
        # Compile final report
        logger.info("\n[7/7] Compiling analysis report...")
        save_results(results)
        
        # Print key findings
        print_key_findings(results)
        
        logger.info("\n" + "=" * 80)
        logger.info("Analysis complete! Results saved to outputs/")
        logger.info("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


def save_results(results: dict):
    """Save analysis results to files."""
    import json
    import pickle
    
    output_dir = Path("outputs/metrics")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save as pickle for full data
    pickle_path = output_dir / f"results_{timestamp}.pkl"
    with open(pickle_path, 'wb') as f:
        pickle.dump(results, f)
    
    logger.info(f"Results saved to {pickle_path}")


def print_key_findings(results: dict):
    """Print key findings to console."""
    print("\n" + "="*80)
    print("KEY FINDINGS")
    print("="*80)
    
    # Overreaction analysis
    if 'overreactions' in results:
        or_data = results['overreactions']
        print(f"\nOverreaction Analysis:")
        print(f"  - Total large moves: {or_data.get('total_large_moves', 0)}")
        print(f"  - Reversal rate (1 min): {or_data.get('reversal_rate_1min', 0):.1%}")
        print(f"  - Reversal rate (3 min): {or_data.get('reversal_rate_3min', 0):.1%}")
        
        if or_data.get('reversal_rate_3min', 0) > 0.55:
            print("  ✓ POTENTIAL EDGE: Mean reversion after large moves")
        else:
            print("  ✗ No significant reversal pattern")
    
    # Volume patterns
    if 'volume_patterns' in results:
        vol_data = results['volume_patterns']
        print(f"\nMarket Microstructure:")
        print(f"  - Mean volume: {vol_data['overall_stats']['mean_volume']:.0f}")
        print(f"  - % with volume: {vol_data['overall_stats']['pct_with_volume']:.1%}")
    
    # Autocorrelation
    if 'autocorrelation' in results:
        ac_data = results['autocorrelation']
        print(f"\nAutocorrelation Analysis:")
        for lag, data in ac_data.get('lags', {}).items():
            if data.get('significant', False):
                print(f"  - Lag {lag}: {data.get('interpretation', 'N/A')} (p={data.get('p_value', 1):.3f})")
    
    # Fee impact
    if 'fee_impact' in results:
        fee_data = results['fee_impact']
        print(f"\nFee Impact:")
        print(f"  - Break-even edge at 50%: {fee_data[fee_data['price']==50]['break_even_edge_pct'].iloc[0]:.2f}%")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()

