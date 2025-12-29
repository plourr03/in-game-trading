"""
Trading Engine - Visualization
===============================

Creates charts showing in-game probabilities, buy/sell signals,
and P/L tracking.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns
from typing import Dict, List
import os

sns.set_style("whitegrid")


class TradeVisualizer:
    """Visualizer for trading results"""
    
    def __init__(self):
        """Initialize visualizer"""
        pass
    
    def plot_game(self, game_df: pd.DataFrame, trades: List[Dict], save_path: str):
        """
        Plot a single game with trades
        
        Args:
            game_df: Game data
            trades: List of trade dictionaries
            save_path: Path to save figure
        """
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        
        # Plot 1: Price with buy/sell signals
        ax1 = axes[0]
        ax1.plot(game_df['game_minute'], game_df['close'], 
                linewidth=2, color='#2E86AB', label='Price')
        
        if len(trades) > 0:
            # Plot buy signals
            buy_minutes = [t['entry_minute'] for t in trades]
            buy_prices = [t['entry_price'] for t in trades]
            ax1.scatter(buy_minutes, buy_prices, marker='^', s=200, 
                       color='#06D6A0', edgecolors='black', linewidth=1.5, 
                       label='BUY', zorder=3)
            
            # Plot sell signals
            sell_minutes = [t['exit_minute'] for t in trades]
            sell_prices = [t['exit_price'] for t in trades]
            ax1.scatter(sell_minutes, sell_prices, marker='v', s=200,
                       color='#EF476F', edgecolors='black', linewidth=1.5,
                       label='SELL', zorder=3)
            
            # Draw trade lines
            for t in trades:
                color = '#06D6A0' if t['net_profit'] > 0 else '#EF476F'
                ax1.plot([t['entry_minute'], t['exit_minute']],
                        [t['entry_price'], t['exit_price']],
                        color=color, alpha=0.3, linewidth=2, linestyle='--')
        
        ax1.set_xlabel('Game Minute', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Price (cents)', fontsize=12, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.set_title(f'Game {game_df["game_id"].iloc[0]} - Trading Activity', 
                     fontsize=13, fontweight='bold')
        
        # Plot 2: Cumulative P/L
        ax2 = axes[1]
        
        if len(trades) > 0:
            cum_pl = np.cumsum([t['net_profit'] for t in trades])
            trade_nums = range(1, len(trades) + 1)
            
            ax2.plot(trade_nums, cum_pl, linewidth=2.5, color='#118AB2',
                    marker='o', markersize=6)
            ax2.fill_between(trade_nums, 0, cum_pl,
                           where=(np.array(cum_pl) >= 0),
                           alpha=0.3, color='#06D6A0')
            ax2.fill_between(trade_nums, 0, cum_pl,
                           where=(np.array(cum_pl) < 0),
                           alpha=0.3, color='#EF476F')
            ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
            
            # Summary stats
            total_pl = sum(t['net_profit'] for t in trades)
            wins = sum(1 for t in trades if t['net_profit'] > 0)
            win_rate = wins / len(trades)
            
            summary = f"Trades: {len(trades)} | Win Rate: {win_rate:.1%} | Total: ${total_pl:,.2f}"
            ax2.text(0.5, 0.95, summary, transform=ax2.transAxes,
                    fontsize=11, fontweight='bold', ha='center', va='top',
                    bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        ax2.set_xlabel('Trade Number', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Cumulative P/L ($)', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.set_title('Cumulative Profit & Loss', fontsize=13, fontweight='bold')
        
        plt.tight_layout()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()


def plot_game_trading(result: Dict, save_path: str = None):
    """
    Create comprehensive trading visualization for a single game.
    
    Args:
        result: Dictionary from GameSimulator.simulate_game()
        save_path: Optional path to save figure
    """
    game_data = result['game_data']
    positions = result['positions']
    signals = result['signals']
    performance = result['performance']
    game_id = result['game_id']
    
    # Create figure with subplots
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), height_ratios=[2, 1, 1])
    fig.suptitle(f'Live Trading Simulation - Game {game_id}', fontsize=16, fontweight='bold')
    
    # ========================================================================
    # SUBPLOT 1: Price Chart with Buy/Sell Signals
    # ========================================================================
    ax1 = axes[0]
    
    # Plot price
    ax1.plot(game_data['datetime'], game_data['close'], 
             linewidth=2, color='#2E86AB', label='Market Price', zorder=1)
    
    # Mark buy signals
    if not positions.empty:
        buys = positions.copy()
        ax1.scatter(buys['entry_time'], buys['entry_price'],
                   marker='^', s=200, color='#06D6A0', edgecolors='black',
                   linewidth=1.5, label='BUY', zorder=3)
        
        # Mark sell signals
        ax1.scatter(buys['exit_time'], buys['exit_price'],
                   marker='v', s=200, color='#EF476F', edgecolors='black',
                   linewidth=1.5, label='SELL', zorder=3)
        
        # Draw lines connecting buy/sell
        for _, pos in buys.iterrows():
            color = '#06D6A0' if pos['is_winner'] else '#EF476F'
            alpha = 0.3
            ax1.plot([pos['entry_time'], pos['exit_time']],
                    [pos['entry_price'], pos['exit_price']],
                    color=color, alpha=alpha, linewidth=2, linestyle='--', zorder=2)
    
    ax1.set_ylabel('Price (cents)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Game Time', fontsize=12, fontweight='bold')
    ax1.legend(loc='best', framealpha=0.9, fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_title('In-Game Probability with Trading Signals', fontsize=13, fontweight='bold')
    
    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    # ========================================================================
    # SUBPLOT 2: Cumulative P/L
    # ========================================================================
    ax2 = axes[1]
    
    if not positions.empty:
        # Sort positions by exit time
        pos_sorted = positions.sort_values('exit_time').copy()
        pos_sorted['cumulative_pl'] = pos_sorted['pl_dollars'].cumsum()
        
        # Plot cumulative P/L
        ax2.plot(pos_sorted['exit_time'], pos_sorted['cumulative_pl'],
                linewidth=2.5, color='#118AB2', marker='o', markersize=6,
                markerfacecolor='white', markeredgewidth=2)
        
        # Fill area
        ax2.fill_between(pos_sorted['exit_time'], 0, pos_sorted['cumulative_pl'],
                        where=(pos_sorted['cumulative_pl'] >= 0),
                        alpha=0.3, color='#06D6A0', label='Profit')
        ax2.fill_between(pos_sorted['exit_time'], 0, pos_sorted['cumulative_pl'],
                        where=(pos_sorted['cumulative_pl'] < 0),
                        alpha=0.3, color='#EF476F', label='Loss')
        
        # Zero line
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
        
        # Final P/L text
        final_pl = pos_sorted['cumulative_pl'].iloc[-1]
        color = '#06D6A0' if final_pl >= 0 else '#EF476F'
        ax2.text(0.02, 0.95, f'Final P/L: ${final_pl:+.2f}',
                transform=ax2.transAxes, fontsize=12, fontweight='bold',
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor=color, alpha=0.7))
    
    ax2.set_ylabel('Cumulative P/L ($)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('Cumulative Profit & Loss', fontsize=13, fontweight='bold')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    # ========================================================================
    # SUBPLOT 3: Trade Summary
    # ========================================================================
    ax3 = axes[2]
    ax3.axis('off')
    
    # Create summary table
    summary_text = f"""
    TRADING SUMMARY
    {'='*60}
    
    Total Trades:          {performance['total_trades']}
    Wins:                  {performance['wins']} ({performance['win_rate']:.1%})
    Losses:                {performance['losses']}
    
    Total P/L:             ${performance['total_pl_dollars']:+.2f}
    Average P/L:           {performance['avg_pl_pct']:+.2f}%
    Total Fees:            ${performance['total_fees']:.2f}
    
    {'='*60}
    """
    
    if not positions.empty:
        summary_text += f"""
    Best Trade:            ${positions['pl_dollars'].max():+.2f} ({positions['pl_pct'].max():+.2f}%)
    Worst Trade:           ${positions['pl_dollars'].min():+.2f} ({positions['pl_pct'].min():+.2f}%)
    Avg Hold Time:         {positions['hold_minutes'].mean():.1f} minutes
        """
    
    ax3.text(0.1, 0.95, summary_text, transform=ax3.transAxes,
            fontsize=10, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    plt.tight_layout()
    
    # Save if path provided
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\nSaved visualization to: {save_path}")
    
    return fig


def plot_multi_game_summary(results: List[Dict], save_path: str = None):
    """
    Create summary visualization across multiple games.
    
    Args:
        results: List of result dictionaries from simulate_game()
        save_path: Optional path to save figure
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Multi-Game Trading Summary', fontsize=16, fontweight='bold')
    
    # Compile all positions
    all_positions = pd.concat([r['positions'] for r in results if not r['positions'].empty])
    
    # ========================================================================
    # SUBPLOT 1: P/L Distribution
    # ========================================================================
    ax1 = axes[0, 0]
    
    if not all_positions.empty:
        wins = all_positions[all_positions['is_winner']]
        losses = all_positions[~all_positions['is_winner']]
        
        ax1.hist(wins['pl_pct'], bins=20, alpha=0.7, color='#06D6A0', label=f'Wins ({len(wins)})', edgecolor='black')
        ax1.hist(losses['pl_pct'], bins=20, alpha=0.7, color='#EF476F', label=f'Losses ({len(losses)})', edgecolor='black')
        
        ax1.axvline(x=0, color='black', linestyle='--', linewidth=2)
        ax1.set_xlabel('P/L (%)', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Frequency', fontsize=11, fontweight='bold')
        ax1.set_title('P/L Distribution', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
    
    # ========================================================================
    # SUBPLOT 2: Win Rate by Strategy
    # ========================================================================
    ax2 = axes[0, 1]
    
    if not all_positions.empty:
        strategy_stats = all_positions.groupby('strategy').agg({
            'is_winner': ['sum', 'count']
        }).reset_index()
        strategy_stats.columns = ['strategy', 'wins', 'total']
        strategy_stats['win_rate'] = strategy_stats['wins'] / strategy_stats['total']
        strategy_stats = strategy_stats.sort_values('win_rate', ascending=True)
        
        colors = ['#06D6A0' if wr >= 0.5 else '#EF476F' for wr in strategy_stats['win_rate']]
        
        ax2.barh(range(len(strategy_stats)), strategy_stats['win_rate'], color=colors, edgecolor='black')
        ax2.set_yticks(range(len(strategy_stats)))
        ax2.set_yticklabels(strategy_stats['strategy'], fontsize=9)
        ax2.set_xlabel('Win Rate', fontsize=11, fontweight='bold')
        ax2.set_title('Win Rate by Strategy', fontsize=12, fontweight='bold')
        ax2.axvline(x=0.5, color='black', linestyle='--', linewidth=2)
        ax2.grid(True, alpha=0.3, axis='x')
    
    # ========================================================================
    # SUBPLOT 3: Cumulative P/L Across All Games
    # ========================================================================
    ax3 = axes[1, 0]
    
    if not all_positions.empty:
        all_positions_sorted = all_positions.sort_values('exit_time').copy()
        all_positions_sorted['cumulative_pl'] = all_positions_sorted['pl_dollars'].cumsum()
        
        ax3.plot(range(len(all_positions_sorted)), all_positions_sorted['cumulative_pl'],
                linewidth=2.5, color='#118AB2')
        ax3.fill_between(range(len(all_positions_sorted)), 0, all_positions_sorted['cumulative_pl'],
                        where=(all_positions_sorted['cumulative_pl'] >= 0),
                        alpha=0.3, color='#06D6A0')
        ax3.fill_between(range(len(all_positions_sorted)), 0, all_positions_sorted['cumulative_pl'],
                        where=(all_positions_sorted['cumulative_pl'] < 0),
                        alpha=0.3, color='#EF476F')
        
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax3.set_xlabel('Trade Number', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Cumulative P/L ($)', fontsize=11, fontweight='bold')
        ax3.set_title('Cumulative P/L Across All Trades', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        
        # Final P/L annotation
        final_pl = all_positions_sorted['cumulative_pl'].iloc[-1]
        color = '#06D6A0' if final_pl >= 0 else '#EF476F'
        ax3.text(0.98, 0.95, f'Final: ${final_pl:+.2f}',
                transform=ax3.transAxes, fontsize=11, fontweight='bold',
                horizontalalignment='right', verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor=color, alpha=0.7))
    
    # ========================================================================
    # SUBPLOT 4: Summary Statistics
    # ========================================================================
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    total_trades = len(all_positions)
    total_wins = all_positions['is_winner'].sum()
    total_pl = all_positions['pl_dollars'].sum()
    total_fees = all_positions['fees'].sum()
    avg_pl = all_positions['pl_pct'].mean()
    
    summary_text = f"""
    OVERALL SUMMARY
    {'='*40}
    
    Games Traded:       {len(results)}
    Total Trades:       {total_trades}
    Wins:               {total_wins} ({total_wins/total_trades:.1%})
    Losses:             {total_trades - total_wins}
    
    Total P/L:          ${total_pl:+.2f}
    Avg P/L per Trade:  {avg_pl:+.2f}%
    Total Fees:         ${total_fees:.2f}
    
    Best Trade:         ${all_positions['pl_dollars'].max():+.2f}
    Worst Trade:        ${all_positions['pl_dollars'].min():+.2f}
    {'='*40}
    """
    
    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
            fontsize=11, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    plt.tight_layout()
    
    # Save if path provided
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\nSaved multi-game summary to: {save_path}")
    
    return fig

