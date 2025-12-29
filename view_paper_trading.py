"""
View Paper Trading Results from Database
Real-time analysis queries
"""
import psycopg2
import pandas as pd
import yaml
from datetime import datetime


def connect_db():
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


def get_latest_session():
    """Get most recent session ID"""
    conn = connect_db()
    df = pd.read_sql("""
        SELECT session_id, start_time, end_time, games_monitored, 
               total_signals, total_trades, total_pl, win_rate
        FROM paper_trading.sessions
        ORDER BY start_time DESC
        LIMIT 1;
    """, conn)
    conn.close()
    return df


def get_session_summary(session_id=None):
    """Get summary for a session"""
    if session_id is None:
        # Get latest session
        latest = get_latest_session()
        if latest.empty:
            print("No sessions found")
            return
        session_id = latest['session_id'].iloc[0]
    
    conn = connect_db()
    
    # Session info
    print("="*80)
    print("SESSION SUMMARY")
    print("="*80)
    
    session = pd.read_sql(f"""
        SELECT * FROM paper_trading.sessions WHERE session_id = {session_id};
    """, conn)
    
    print(f"\nSession ID: {session_id}")
    print(f"Start Time: {session['start_time'].iloc[0]}")
    print(f"End Time: {session['end_time'].iloc[0] if session['end_time'].iloc[0] else 'In Progress'}")
    print(f"Games Monitored: {session['games_monitored'].iloc[0]}")
    print(f"Total Signals: {session['total_signals'].iloc[0]}")
    print(f"Total Trades: {session['total_trades'].iloc[0]}")
    print(f"Total P/L: ${session['total_pl'].iloc[0]:.2f}")
    print(f"Win Rate: {session['win_rate'].iloc[0]:.1%}" if session['win_rate'].iloc[0] else "Win Rate: N/A")
    
    # Trade details
    print("\n" + "="*80)
    print("TRADE DETAILS")
    print("="*80)
    
    trades = pd.read_sql(f"""
        SELECT trade_id, game_id, entry_timestamp, exit_timestamp,
               entry_price, exit_price, net_profit, won, probability
        FROM paper_trading.trades
        WHERE session_id = {session_id}
        ORDER BY entry_timestamp;
    """, conn)
    
    if not trades.empty:
        print(f"\n{len(trades)} trades executed:")
        for idx, trade in trades.iterrows():
            status = "WIN" if trade['won'] else "LOSS"
            print(f"  [{status}] {trade['game_id']}: ${trade['entry_price']:.0f}c -> ${trade['exit_price']:.0f}c = ${trade['net_profit']:+.2f} (prob={trade['probability']:.1%})")
    else:
        print("\nNo trades completed yet")
    
    # Per-game performance
    print("\n" + "="*80)
    print("PER-GAME PERFORMANCE")
    print("="*80)
    
    per_game = pd.read_sql(f"""
        SELECT game_id,
               COUNT(*) as trades,
               SUM(CASE WHEN won THEN 1 ELSE 0 END) as wins,
               SUM(net_profit) as total_pl,
               AVG(probability) as avg_prob
        FROM paper_trading.trades
        WHERE session_id = {session_id}
        GROUP BY game_id
        ORDER BY total_pl DESC;
    """, conn)
    
    if not per_game.empty:
        print()
        for idx, game in per_game.iterrows():
            win_rate = game['wins'] / game['trades'] if game['trades'] > 0 else 0
            print(f"  {game['game_id']}: {game['trades']} trades, {win_rate:.1%} win rate, ${game['total_pl']:.2f} P/L")
    
    conn.close()


def view_signals(session_id=None, limit=20):
    """View recent signals"""
    if session_id is None:
        latest = get_latest_session()
        if latest.empty:
            print("No sessions found")
            return
        session_id = latest['session_id'].iloc[0]
    
    conn = connect_db()
    
    signals = pd.read_sql(f"""
        SELECT signal_id, timestamp, game_id, away_team, home_team,
               action, entry_price, probability, hold_minutes,
               score_home, score_away, period, executed
        FROM paper_trading.signals
        WHERE session_id = {session_id}
        ORDER BY timestamp DESC
        LIMIT {limit};
    """, conn)
    
    print("\n" + "="*80)
    print(f"RECENT SIGNALS (Latest {limit})")
    print("="*80 + "\n")
    
    if not signals.empty:
        for idx, sig in signals.iterrows():
            score_diff = sig['score_home'] - sig['score_away']
            exec_status = "[EXECUTED]" if sig['executed'] else "[PENDING]"
            print(f"{sig['timestamp']}: {sig['away_team']}@{sig['home_team']} Q{sig['period']}")
            print(f"  {exec_status} {sig['action']} ${sig['entry_price']:.0f}c (prob={sig['probability']:.1%}, hold={sig['hold_minutes']}min)")
            print(f"  Score: {sig['score_away']}-{sig['score_home']} (diff: {score_diff:+d})")
            print()
    else:
        print("No signals found")
    
    conn.close()


def view_price_data(session_id=None, game_id=None, limit=50):
    """View price/score data"""
    if session_id is None:
        latest = get_latest_session()
        if latest.empty:
            print("No sessions found")
            return
        session_id = latest['session_id'].iloc[0]
    
    conn = connect_db()
    
    query = f"""
        SELECT timestamp, game_id, away_team, home_team,
               price_mid, score_home, score_away, score_diff, period, game_minute
        FROM paper_trading.price_data
        WHERE session_id = {session_id}
    """
    
    if game_id:
        query += f" AND game_id = '{game_id}'"
    
    query += f" ORDER BY timestamp DESC LIMIT {limit};"
    
    data = pd.read_sql(query, conn)
    
    print("\n" + "="*80)
    print(f"PRICE DATA (Latest {limit})")
    print("="*80 + "\n")
    
    if not data.empty:
        for idx, row in data.iterrows():
            print(f"{row['timestamp']}: {row['away_team']}@{row['home_team']} Q{row['period']}")
            print(f"  Price: ${row['price_mid']:.0f}c | Score: {row['score_away']}-{row['score_home']} (diff: {row['score_diff']:+d})")
    else:
        print("No data found")
    
    conn.close()


def get_live_stats(session_id=None):
    """Get live statistics during trading"""
    if session_id is None:
        latest = get_latest_session()
        if latest.empty:
            print("No active session")
            return
        session_id = latest['session_id'].iloc[0]
    
    conn = connect_db()
    
    # Current stats
    stats = pd.read_sql(f"""
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN won THEN 1 ELSE 0 END) as wins,
            SUM(net_profit) as total_pl,
            AVG(net_profit) as avg_pl,
            AVG(probability) as avg_prob
        FROM paper_trading.trades
        WHERE session_id = {session_id};
    """, conn)
    
    signals = pd.read_sql(f"""
        SELECT COUNT(*) as total_signals
        FROM paper_trading.signals
        WHERE session_id = {session_id};
    """, conn)
    
    print("\n" + "="*80)
    print("LIVE TRADING STATISTICS")
    print("="*80)
    print(f"\nSession ID: {session_id}")
    print(f"Signals Generated: {signals['total_signals'].iloc[0]}")
    print(f"Trades Executed: {stats['total_trades'].iloc[0]}")
    
    if stats['total_trades'].iloc[0] > 0:
        win_rate = stats['wins'].iloc[0] / stats['total_trades'].iloc[0]
        print(f"Win Rate: {win_rate:.1%}")
        print(f"Total P/L: ${stats['total_pl'].iloc[0]:.2f}")
        print(f"Avg P/L per Trade: ${stats['avg_pl'].iloc[0]:.2f}")
        print(f"Avg Signal Probability: {stats['avg_prob'].iloc[0]:.1%}")
    
    conn.close()


def main():
    """Interactive menu"""
    print("\n" + "="*80)
    print("PAPER TRADING DATABASE VIEWER")
    print("="*80)
    
    while True:
        print("\nOptions:")
        print("  1. View latest session summary")
        print("  2. View recent signals")
        print("  3. View price data")
        print("  4. View live stats")
        print("  5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            get_session_summary()
        elif choice == '2':
            get_session_summary()
            view_signals()
        elif choice == '3':
            view_price_data()
        elif choice == '4':
            get_live_stats()
        elif choice == '5':
            break
        else:
            print("Invalid option")


if __name__ == "__main__":
    # Just show latest session summary
    get_session_summary()
    print("\n" + "="*80)
    print("For more options, run: python view_paper_trading.py")
    print("="*80)


