"""
Plot Paper Trading P/L Over Time
Visualizes cumulative profit/loss throughout the trading session
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import psycopg2
import yaml
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

def get_db_connection():
    """Connect to database"""
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    db_config = config['database']
    return psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )


def plot_session_pl(session_id=None):
    """Plot P/L over time for a session"""
    
    conn = get_db_connection()
    
    # Get the most recent session if not specified
    if session_id is None:
        query = """
            SELECT session_id, start_time, end_time, total_pl
            FROM paper_trading.sessions
            ORDER BY start_time DESC
            LIMIT 1
        """
        df_session = pd.read_sql(query, conn)
        
        if df_session.empty:
            print("No sessions found!")
            conn.close()
            return
        
        session_id = int(df_session['session_id'].iloc[0])
        start_time = df_session['start_time'].iloc[0]
        end_time = df_session['end_time'].iloc[0]
        total_pl = df_session['total_pl'].iloc[0]
    
    # Get all trades for this session
    query = """
        SELECT 
            trade_id,
            game_id,
            entry_timestamp,
            exit_timestamp,
            entry_price,
            exit_price,
            contracts,
            net_profit,
            won,
            probability
        FROM paper_trading.trades
        WHERE session_id = %s
        ORDER BY exit_timestamp
    """
    
    df_trades = pd.read_sql(query, conn, params=(session_id,))
    conn.close()
    
    if df_trades.empty:
        print(f"No trades found for session {session_id}")
        return
    
    # Calculate cumulative P/L
    df_trades['cumulative_pl'] = df_trades['net_profit'].cumsum()
    
    # Create the plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot 1: Cumulative P/L over time
    ax1.plot(df_trades['exit_timestamp'], df_trades['cumulative_pl'], 
             marker='o', linewidth=2, markersize=8, color='blue', label='Cumulative P/L')
    
    # Add horizontal line at 0
    ax1.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    
    # Color the area
    ax1.fill_between(df_trades['exit_timestamp'], df_trades['cumulative_pl'], 0,
                      where=(df_trades['cumulative_pl'] >= 0), alpha=0.3, color='green', label='Profit')
    ax1.fill_between(df_trades['exit_timestamp'], df_trades['cumulative_pl'], 0,
                      where=(df_trades['cumulative_pl'] < 0), alpha=0.3, color='red', label='Loss')
    
    # Mark individual trades
    wins = df_trades[df_trades['won'] == True]
    losses = df_trades[df_trades['won'] == False]
    
    ax1.scatter(wins['exit_timestamp'], wins['cumulative_pl'], 
                color='green', s=150, marker='^', label='Win', zorder=5, edgecolors='darkgreen', linewidths=2)
    ax1.scatter(losses['exit_timestamp'], losses['cumulative_pl'], 
                color='red', s=150, marker='v', label='Loss', zorder=5, edgecolors='darkred', linewidths=2)
    
    ax1.set_xlabel('Time', fontsize=12)
    ax1.set_ylabel('Cumulative P/L ($)', fontsize=12)
    ax1.set_title(f'Paper Trading Session {session_id} - Cumulative P/L Over Time', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Format y-axis as currency
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # Plot 2: Individual trade P/L
    colors = ['green' if won else 'red' for won in df_trades['won']]
    bars = ax2.bar(range(len(df_trades)), df_trades['net_profit'], color=colors, alpha=0.7, edgecolor='black')
    
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, df_trades['net_profit'])):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'${val:.2f}',
                ha='center', va='bottom' if height > 0 else 'top',
                fontsize=9, fontweight='bold')
    
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax2.set_xlabel('Trade Number', fontsize=12)
    ax2.set_ylabel('Trade P/L ($)', fontsize=12)
    ax2.set_title('Individual Trade Results', fontsize=14, fontweight='bold')
    ax2.set_xticks(range(len(df_trades)))
    ax2.set_xticklabels([f'T{i+1}' for i in range(len(df_trades))])
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Format y-axis as currency
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # Add summary text
    win_rate = (df_trades['won'].sum() / len(df_trades)) * 100
    total_pl = df_trades['net_profit'].sum()
    avg_pl = df_trades['net_profit'].mean()
    
    summary_text = f"""
    Session Summary:
    Total Trades: {len(df_trades)}
    Wins: {df_trades['won'].sum()} | Losses: {(~df_trades['won']).sum()}
    Win Rate: {win_rate:.1f}%
    Total P/L: ${total_pl:,.2f}
    Avg P/L: ${avg_pl:,.2f}
    """
    
    fig.text(0.02, 0.02, summary_text, fontsize=10, verticalalignment='bottom',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    
    # Save plot
    filename = f'paper_trading_session_{session_id}_pl.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\n[OK] Plot saved to: {filename}")
    
    plt.show()
    
    # Print trade details
    print("\n" + "="*80)
    print("TRADE DETAILS")
    print("="*80)
    print(f"{'#':<4} {'Time':<10} {'Game':<12} {'Entry':<8} {'Exit':<8} {'P/L':<12} {'Result':<8} {'Prob':<8}")
    print("-"*80)
    
    for i, row in df_trades.iterrows():
        time_str = row['exit_timestamp'].strftime('%H:%M:%S')
        result = "WIN" if row['won'] else "LOSS"
        result_color = "\033[92m" if row['won'] else "\033[91m"  # Green or Red
        reset_color = "\033[0m"
        
        print(f"{i+1:<4} {time_str:<10} {row['game_id']:<12} "
              f"${row['entry_price']:<7.0f} ${row['exit_price']:<7.0f} "
              f"{result_color}${row['net_profit']:>9.2f}{reset_color} "
              f"{result_color}{result:<8}{reset_color} "
              f"{row['probability']:.1%}")


def plot_price_movements(session_id=None):
    """Plot price movements for all games in session"""
    
    conn = get_db_connection()
    
    # Get the most recent session if not specified
    if session_id is None:
        query = """
            SELECT session_id
            FROM paper_trading.sessions
            ORDER BY start_time DESC
            LIMIT 1
        """
        df_session = pd.read_sql(query, conn)
        
        if df_session.empty:
            print("No sessions found!")
            conn.close()
            return
        
        session_id = int(df_session['session_id'].iloc[0])
    
    # Get price data
    query = """
        SELECT 
            timestamp,
            game_id,
            away_team,
            home_team,
            price_mid,
            score_home,
            score_away
        FROM paper_trading.price_data
        WHERE session_id = %s
        ORDER BY timestamp
    """
    
    df_prices = pd.read_sql(query, conn, params=(session_id,))
    
    # Get trades
    query = """
        SELECT 
            trade_id,
            game_id,
            entry_timestamp,
            exit_timestamp,
            entry_price,
            exit_price,
            won
        FROM paper_trading.trades
        WHERE session_id = %s
    """
    
    df_trades = pd.read_sql(query, conn, params=(session_id,))
    conn.close()
    
    if df_prices.empty:
        print(f"No price data found for session {session_id}")
        return
    
    # Plot each game
    games = df_prices['game_id'].unique()
    
    fig, axes = plt.subplots(len(games), 1, figsize=(14, 4*len(games)))
    
    if len(games) == 1:
        axes = [axes]
    
    for idx, game_id in enumerate(games):
        ax = axes[idx]
        
        # Filter data for this game
        game_prices = df_prices[df_prices['game_id'] == game_id].copy()
        game_trades = df_trades[df_trades['game_id'] == game_id]
        
        if game_prices.empty:
            continue
        
        game_label = f"{game_prices['away_team'].iloc[0]} @ {game_prices['home_team'].iloc[0]}"
        
        # Plot price line
        ax.plot(game_prices['timestamp'], game_prices['price_mid'], 
                linewidth=2, color='blue', label='Market Price')
        
        # Mark trade entries and exits
        for _, trade in game_trades.iterrows():
            # Entry
            ax.axvline(x=trade['entry_timestamp'], color='green', linestyle='--', alpha=0.5)
            ax.scatter(trade['entry_timestamp'], trade['entry_price'], 
                      color='green', s=200, marker='^', zorder=5, edgecolors='darkgreen', linewidths=2)
            
            # Exit
            color = 'darkgreen' if trade['won'] else 'darkred'
            ax.axvline(x=trade['exit_timestamp'], color=color, linestyle='--', alpha=0.5)
            ax.scatter(trade['exit_timestamp'], trade['exit_price'], 
                      color=color, s=200, marker='o', zorder=5, edgecolors='black', linewidths=2)
        
        ax.set_xlabel('Time', fontsize=10)
        ax.set_ylabel('Price (cents)', fontsize=10)
        ax.set_title(f'{game_label} - Price Movement & Trades', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
    
    plt.tight_layout()
    
    filename = f'paper_trading_session_{session_id}_prices.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"[OK] Price plot saved to: {filename}")
    
    plt.show()


if __name__ == "__main__":
    print("="*80)
    print("PAPER TRADING P/L VISUALIZATION")
    print("="*80)
    
    # Plot P/L over time
    plot_session_pl()
    
    # Plot price movements
    print("\n" + "="*80)
    print("Generating price movement charts...")
    print("="*80)
    plot_price_movements()

