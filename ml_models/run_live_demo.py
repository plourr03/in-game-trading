"""
Test the advanced model on actual games to see trades in action
"""
import pandas as pd
import numpy as np
import joblib
import sys
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.backtesting.fees import calculate_kalshi_fees
from src.utils.helpers import get_logger

logger = get_logger(__name__)


def simulate_game(game_id, model, features, df):
    """Simulate trading on a single game"""
    
    game_df = df[df['game_id'] == game_id].copy()
    
    if len(game_df) == 0:
        return None
    
    # Get predictions
    X = game_df[features].fillna(0).replace([np.inf, -np.inf], 0)
    game_df['pred_proba'] = model.predict_proba(X)[:, 1]
    
    # Entries at threshold 0.50
    threshold = 0.50
    entries = game_df[game_df['pred_proba'] >= threshold].copy()
    
    if len(entries) == 0:
        return None
    
    # Simulate trades
    entries['hold_minutes'] = 5
    entries['exit_price'] = entries['current_price'] + entries['profit_5min']
    entries['profit_cents'] = entries['profit_5min']
    
    # Calculate P/L
    contracts = 100
    entries['buy_fee'] = entries.apply(
        lambda row: calculate_kalshi_fees(row['current_price'], contracts, 'buy'),
        axis=1
    )
    entries['sell_fee'] = entries.apply(
        lambda row: calculate_kalshi_fees(row['exit_price'], contracts, 'sell'),
        axis=1
    )
    entries['net_profit'] = (entries['profit_cents'] - entries['buy_fee'] - entries['sell_fee']) * contracts / 100
    entries['won'] = (entries['net_profit'] > 0).astype(int)
    
    return {
        'game_id': game_id,
        'trades': len(entries),
        'wins': entries['won'].sum(),
        'win_rate': entries['won'].mean(),
        'total_pl': entries['net_profit'].sum(),
        'entries_df': entries[['game_minute', 'current_price', 'pred_proba', 'profit_cents', 
                               'exit_price', 'net_profit', 'won']].copy(),
        'game_df': game_df[['game_minute', 'current_price', 'score_home', 'score_away']].copy()
    }


def plot_game_trades(result, output_path):
    """Plot game with trades"""
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    game_df = result['game_df']
    entries = result['entries_df']
    
    # Plot 1: Price and trades
    ax1.plot(game_df['game_minute'], game_df['current_price'], 'b-', linewidth=1, alpha=0.6, label='Market Price')
    
    # Mark entries
    wins = entries[entries['won'] == 1]
    losses = entries[entries['won'] == 0]
    
    ax1.scatter(wins['game_minute'], wins['current_price'], c='green', s=100, marker='^', 
               label=f'Wins ({len(wins)})', zorder=5, edgecolors='darkgreen', linewidths=1.5)
    ax1.scatter(losses['game_minute'], losses['current_price'], c='red', s=100, marker='v',
               label=f'Losses ({len(losses)})', zorder=5, edgecolors='darkred', linewidths=1.5)
    
    ax1.set_ylabel('Price (¢)', fontsize=12, fontweight='bold')
    ax1.set_title(f"Game {result['game_id']}: {result['trades']} trades, "
                 f"{result['win_rate']:.1%} win rate, ${result['total_pl']:.2f} P/L",
                 fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    
    # Plot 2: Score differential
    game_df['score_diff'] = game_df['score_home'] - game_df['score_away']
    ax2.plot(game_df['game_minute'], game_df['score_diff'], 'purple', linewidth=2, label='Score Differential')
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax2.fill_between(game_df['game_minute'], 0, game_df['score_diff'], 
                     where=(game_df['score_diff'] >= 0), color='green', alpha=0.2, label='Home Leading')
    ax2.fill_between(game_df['game_minute'], 0, game_df['score_diff'],
                     where=(game_df['score_diff'] < 0), color='red', alpha=0.2, label='Away Leading')
    
    # Mark trade times
    for minute in entries['game_minute']:
        ax2.axvline(x=minute, color='orange', alpha=0.3, linewidth=1)
    
    ax2.set_xlabel('Game Minute', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Score Differential', fontsize=12, fontweight='bold')
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def run_live_demo():
    """Run live demo on random games"""
    
    logger.info("="*100)
    logger.info("ADVANCED MODEL LIVE DEMO")
    logger.info("="*100)
    
    # Load data
    logger.info("\nLoading data...")
    df = pd.read_csv('ml_models/outputs/advanced_training_data.csv')
    
    # Load model
    model = joblib.load('ml_models/outputs/advanced_model.pkl')
    features = joblib.load('ml_models/outputs/advanced_features.pkl')
    
    # Test on last 20% (test set)
    split_idx = int(len(df) * 0.8)
    test_df = df[split_idx:].copy()
    test_games = test_df['game_id'].unique()
    
    logger.info(f"Test set: {len(test_games)} games")
    
    # Pick 5 random games with good trade volume
    np.random.seed(42)
    results = []
    
    for game_id in test_games:
        result = simulate_game(game_id, model, features, test_df)
        if result and result['trades'] >= 10:  # At least 10 trades
            results.append(result)
    
    # Sort by most trades and take top 5
    results.sort(key=lambda x: x['trades'], reverse=True)
    top_results = results[:5]
    
    logger.info(f"\nFound {len(top_results)} games with 10+ trades")
    
    # Plot each game
    os.makedirs('ml_models/outputs/demo_trades', exist_ok=True)
    
    for i, result in enumerate(top_results, 1):
        logger.info(f"\n[{i}/5] Game {result['game_id']}: {result['trades']} trades, "
                   f"{result['win_rate']:.1%} win rate, ${result['total_pl']:.2f} P/L")
        
        output_path = f"ml_models/outputs/demo_trades/game_{result['game_id']}.png"
        plot_game_trades(result, output_path)
        logger.info(f"      Saved: {output_path}")
    
    # Summary
    total_trades = sum(r['trades'] for r in top_results)
    total_wins = sum(r['wins'] for r in top_results)
    total_pl = sum(r['total_pl'] for r in top_results)
    avg_win_rate = total_wins / total_trades if total_trades > 0 else 0
    
    logger.info("\n" + "="*100)
    logger.info("DEMO SUMMARY (5 games, 100 contracts/trade)")
    logger.info("="*100)
    logger.info(f"  Total Trades:   {total_trades}")
    logger.info(f"  Wins:           {total_wins}")
    logger.info(f"  Win Rate:       {avg_win_rate:.1%}")
    logger.info(f"  Total P/L:      ${total_pl:.2f}")
    logger.info(f"  Avg P/L/Game:   ${total_pl / len(top_results):.2f}")
    
    # Summary table
    print("\n" + "="*100)
    print("PER-GAME BREAKDOWN")
    print("="*100)
    summary_df = pd.DataFrame([{
        'game_id': r['game_id'],
        'trades': r['trades'],
        'win_rate': f"{r['win_rate']:.1%}",
        'total_pl': f"${r['total_pl']:.2f}"
    } for r in top_results])
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    run_live_demo()




