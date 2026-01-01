"""
Live Trading Dashboard
Monitors paper trading in real-time and displays current status
Run this in a separate terminal while paper trading is running
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import psycopg2
import yaml
from datetime import datetime, timedelta
import time
from colorama import init, Fore, Back, Style

# Initialize colorama for Windows
init()

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


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_active_session():
    """Get the most recent active session"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT session_id, start_time, games_monitored
        FROM paper_trading.sessions
        WHERE end_time IS NULL
        ORDER BY start_time DESC
        LIMIT 1
    """)
    
    result = cur.fetchone()
    conn.close()
    
    if result:
        return {
            'session_id': result[0],
            'start_time': result[1],
            'games': result[2]
        }
    return None


def get_session_stats(session_id):
    """Get statistics for current session"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get trade counts and P/L
    cur.execute("""
        SELECT 
            COUNT(*) as total_trades,
            COUNT(CASE WHEN exit_time IS NULL THEN 1 END) as open_trades,
            COUNT(CASE WHEN exit_time IS NOT NULL THEN 1 END) as closed_trades,
            COALESCE(SUM(CASE WHEN exit_time IS NOT NULL THEN net_pl ELSE 0 END), 0) as total_pl,
            COALESCE(SUM(CASE WHEN exit_time IS NOT NULL AND net_pl > 0 THEN 1 ELSE 0 END), 0) as wins,
            COALESCE(SUM(CASE WHEN exit_time IS NOT NULL AND net_pl < 0 THEN 1 ELSE 0 END), 0) as losses
        FROM paper_trading.trades
        WHERE session_id = %s
    """, (session_id,))
    
    stats = cur.fetchone()
    conn.close()
    
    return {
        'total_trades': stats[0],
        'open_trades': stats[1],
        'closed_trades': stats[2],
        'total_pl': float(stats[3]),
        'wins': stats[4],
        'losses': stats[5]
    }


def get_open_positions(session_id):
    """Get all open positions"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            trade_id, game_id, ticker, side, entry_price, contracts,
            entry_time, entry_reason
        FROM paper_trading.trades
        WHERE session_id = %s AND exit_time IS NULL
        ORDER BY entry_time DESC
    """, (session_id,))
    
    positions = []
    for row in cur.fetchall():
        positions.append({
            'trade_id': row[0],
            'game_id': row[1],
            'ticker': row[2],
            'side': row[3],
            'entry_price': float(row[4]),
            'contracts': row[5],
            'entry_time': row[6],
            'entry_reason': row[7]
        })
    
    conn.close()
    return positions


def get_recent_trades(session_id, limit=10):
    """Get recent closed trades"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            trade_id, game_id, ticker, side, entry_price, exit_price,
            contracts, net_pl, entry_time, exit_time, exit_reason
        FROM paper_trading.trades
        WHERE session_id = %s AND exit_time IS NOT NULL
        ORDER BY exit_time DESC
        LIMIT %s
    """, (session_id, limit))
    
    trades = []
    for row in cur.fetchall():
        trades.append({
            'trade_id': row[0],
            'game_id': row[1],
            'ticker': row[2],
            'side': row[3],
            'entry_price': float(row[4]),
            'exit_price': float(row[5]),
            'contracts': row[6],
            'net_pl': float(row[7]),
            'entry_time': row[8],
            'exit_time': row[9],
            'exit_reason': row[10]
        })
    
    conn.close()
    return trades


def get_recent_signals(session_id, limit=5):
    """Get recent signals that didn't result in trades"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            game_id, ticker, signal, probability, timestamp, reason
        FROM paper_trading.signals
        WHERE session_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
    """, (session_id, limit))
    
    signals = []
    for row in cur.fetchall():
        signals.append({
            'game_id': row[0],
            'ticker': row[1],
            'signal': row[2],
            'probability': float(row[3]),
            'timestamp': row[4],
            'reason': row[5]
        })
    
    conn.close()
    return signals


def format_pl(pl):
    """Format P/L with color"""
    if pl > 0:
        return f"{Fore.GREEN}+${pl:.2f}{Style.RESET_ALL}"
    elif pl < 0:
        return f"{Fore.RED}-${abs(pl):.2f}{Style.RESET_ALL}"
    else:
        return f"${pl:.2f}"


def format_time_ago(dt):
    """Format time as 'X seconds/minutes ago'"""
    if dt is None:
        return "N/A"
    
    now = datetime.now()
    if dt.tzinfo is None:
        diff = now - dt
    else:
        diff = now.replace(tzinfo=dt.tzinfo) - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds/60)}m ago"
    else:
        return f"{int(seconds/3600)}h ago"


def display_dashboard():
    """Display the live dashboard"""
    
    while True:
        clear_screen()
        
        # Header
        print("=" * 100)
        print(f"{Back.BLUE}{Fore.WHITE} LIVE PAPER TRADING DASHBOARD {Style.RESET_ALL}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        
        # Get active session
        session = get_active_session()
        
        if not session:
            print(f"\n{Fore.YELLOW}[INFO] No active paper trading session found{Style.RESET_ALL}")
            print("\nTo start paper trading, run:")
            print("  python run_paper_trading.py")
            print("\nRefreshing in 10 seconds...")
            time.sleep(10)
            continue
        
        session_id = session['session_id']
        
        # Session info
        print(f"\n{Fore.CYAN}Session ID:{Style.RESET_ALL} {session_id}")
        print(f"{Fore.CYAN}Started:{Style.RESET_ALL} {session['start_time'].strftime('%H:%M:%S')}")
        print(f"{Fore.CYAN}Games:{Style.RESET_ALL} {', '.join(session['games'])}")
        
        # Get stats
        stats = get_session_stats(session_id)
        
        # Stats summary
        print(f"\n{Back.GREEN}{Fore.BLACK} SESSION STATS {Style.RESET_ALL}")
        print(f"Total Trades: {stats['total_trades']}  |  Open: {stats['open_trades']}  |  Closed: {stats['closed_trades']}")
        
        if stats['closed_trades'] > 0:
            win_rate = (stats['wins'] / stats['closed_trades']) * 100
            print(f"Wins: {Fore.GREEN}{stats['wins']}{Style.RESET_ALL}  |  Losses: {Fore.RED}{stats['losses']}{Style.RESET_ALL}  |  Win Rate: {win_rate:.1f}%")
        
        print(f"Total P/L: {format_pl(stats['total_pl'])}")
        
        # Open positions
        print(f"\n{Back.YELLOW}{Fore.BLACK} OPEN POSITIONS ({stats['open_trades']}) {Style.RESET_ALL}")
        
        if stats['open_trades'] > 0:
            positions = get_open_positions(session_id)
            
            print(f"{'ID':<6} {'Game':<12} {'Ticker':<30} {'Side':<6} {'Entry':<8} {'Contracts':<10} {'Time':<12} {'Reason':<30}")
            print("-" * 100)
            
            for pos in positions:
                side_color = Fore.GREEN if pos['side'] == 'YES' else Fore.RED
                print(f"{pos['trade_id']:<6} {pos['game_id']:<12} {pos['ticker']:<30} {side_color}{pos['side']:<6}{Style.RESET_ALL} "
                      f"{pos['entry_price']:<8.3f} {pos['contracts']:<10} {format_time_ago(pos['entry_time']):<12} "
                      f"{pos['entry_reason'][:28]:<30}")
        else:
            print("  No open positions")
        
        # Recent closed trades
        print(f"\n{Back.MAGENTA}{Fore.WHITE} RECENT TRADES (Last 5) {Style.RESET_ALL}")
        
        recent_trades = get_recent_trades(session_id, limit=5)
        
        if recent_trades:
            print(f"{'ID':<6} {'Game':<12} {'Side':<6} {'Entry':<8} {'Exit':<8} {'Contracts':<10} {'P/L':<12} {'Duration':<12} {'Exit Reason':<20}")
            print("-" * 100)
            
            for trade in recent_trades:
                duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 60
                side_color = Fore.GREEN if trade['side'] == 'YES' else Fore.RED
                
                print(f"{trade['trade_id']:<6} {trade['game_id']:<12} {side_color}{trade['side']:<6}{Style.RESET_ALL} "
                      f"{trade['entry_price']:<8.3f} {trade['exit_price']:<8.3f} {trade['contracts']:<10} "
                      f"{format_pl(trade['net_pl']):<20} {duration:<12.1f}m {trade['exit_reason'][:18]:<20}")
        else:
            print("  No closed trades yet")
        
        # Recent signals
        print(f"\n{Back.CYAN}{Fore.BLACK} RECENT SIGNALS (Last 5) {Style.RESET_ALL}")
        
        recent_signals = get_recent_signals(session_id, limit=5)
        
        if recent_signals:
            print(f"{'Game':<12} {'Ticker':<30} {'Signal':<8} {'Prob':<8} {'Time':<12} {'Reason':<30}")
            print("-" * 100)
            
            for sig in recent_signals:
                signal_color = Fore.GREEN if sig['signal'] == 'BUY' else (Fore.RED if sig['signal'] == 'SELL' else Fore.YELLOW)
                
                print(f"{sig['game_id']:<12} {sig['ticker']:<30} {signal_color}{sig['signal']:<8}{Style.RESET_ALL} "
                      f"{sig['probability']:<8.3f} {format_time_ago(sig['timestamp']):<12} {sig['reason'][:28]:<30}")
        else:
            print("  No signals generated yet")
        
        # Footer
        print("\n" + "=" * 100)
        print(f"{Fore.CYAN}Refreshing every 5 seconds... Press Ctrl+C to exit{Style.RESET_ALL}")
        print("=" * 100)
        
        time.sleep(5)


if __name__ == "__main__":
    try:
        display_dashboard()
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

