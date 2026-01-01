"""
Detailed Trade Timeline
Shows exactly when each trade happened and game context
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import psycopg2
import yaml
import pandas as pd
from datetime import datetime

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


def get_trade_timeline(session_id=5):
    """Get detailed timeline of all trades"""
    
    conn = get_db_connection()
    
    # Get trades with entry/exit details
    query = """
        SELECT 
            t.trade_id,
            t.game_id,
            t.entry_timestamp,
            t.exit_timestamp,
            t.entry_minute,
            t.exit_minute,
            t.entry_price,
            t.exit_price,
            t.contracts,
            t.entry_score_home,
            t.entry_score_away,
            t.exit_score_home,
            t.exit_score_away,
            t.net_profit,
            t.won,
            t.probability,
            t.hold_duration_actual,
            s.ticker
        FROM paper_trading.trades t
        LEFT JOIN paper_trading.signals s ON t.signal_id = s.signal_id
        WHERE t.session_id = %s
        ORDER BY t.entry_timestamp
    """
    
    df = pd.read_sql(query, conn, params=(session_id,))
    conn.close()
    
    # Determine team names from game_id and ticker
    game_info = {
        '0022500461': ('SAC', 'LAC'),  # Sacramento @ LA Clippers
        '0022500460': ('DET', 'LAL'),  # Detroit @ LA Lakers
        '0022500459': ('BOS', 'UTA'),  # Boston @ Utah
        '0022500458': ('PHI', 'MEM')   # Philadelphia @ Memphis
    }
    
    print("="*100)
    print("DETAILED TRADE TIMELINE - SESSION 5")
    print("="*100)
    print()
    
    for idx, row in df.iterrows():
        trade_num = idx + 1
        game_id = row['game_id']
        away, home = game_info.get(game_id, ('???', '???'))
        
        entry_time = row['entry_timestamp'].strftime('%I:%M:%S %p')
        exit_time = row['exit_timestamp'].strftime('%I:%M:%S %p')
        
        duration = row['hold_duration_actual']
        result = "WIN" if row['won'] else "LOSS"
        result_symbol = "[WIN]" if row['won'] else "[LOSS]"
        
        print(f"{'='*100}")
        print(f"TRADE #{trade_num} - {result_symbol} {result}")
        print(f"{'='*100}")
        print(f"Game:           {away} @ {home} (Game ID: {game_id})")
        print(f"Ticker:         {row['ticker']}")
        print()
        print(f"ENTRY:")
        print(f"  Time:         {entry_time}")
        print(f"  Game Minute:  {row['entry_minute']:.1f}")
        print(f"  Score:        {away} {row['entry_score_away']} - {row['entry_score_home']} {home}")
        print(f"  Entry Price:  ${row['entry_price']:.2f}")
        print(f"  Contracts:    {row['contracts']}")
        print(f"  ML Prob:      {row['probability']:.1%}")
        print()
        print(f"EXIT:")
        print(f"  Time:         {exit_time}")
        print(f"  Game Minute:  {row['exit_minute']:.1f}")
        print(f"  Score:        {away} {row['exit_score_away']} - {row['exit_score_home']} {home}")
        print(f"  Exit Price:   ${row['exit_price']:.2f}")
        print(f"  Duration:     {duration} minutes")
        print()
        print(f"RESULT:")
        print(f"  Price Move:   ${row['entry_price']:.2f} -> ${row['exit_price']:.2f} ({row['exit_price']-row['entry_price']:+.2f})")
        
        if row['won']:
            print(f"  Net Profit:   ${row['net_profit']:.2f} [WIN]")
        else:
            print(f"  Net Loss:     ${row['net_profit']:.2f} [LOSS]")
        
        print()
    
    # Summary by game
    print("="*100)
    print("SUMMARY BY GAME")
    print("="*100)
    print()
    
    for game_id, (away, home) in game_info.items():
        game_trades = df[df['game_id'] == game_id]
        
        if len(game_trades) == 0:
            continue
        
        wins = game_trades['won'].sum()
        losses = len(game_trades) - wins
        total_pl = game_trades['net_profit'].sum()
        
        print(f"{away} @ {home}:")
        print(f"  Total Trades: {len(game_trades)}")
        print(f"  Wins/Losses:  {wins}W - {losses}L")
        print(f"  Total P/L:    ${total_pl:,.2f}")
        print(f"  First Trade:  {game_trades.iloc[0]['entry_timestamp'].strftime('%I:%M %p')}")
        print(f"  Last Trade:   {game_trades.iloc[-1]['exit_timestamp'].strftime('%I:%M %p')}")
        print()
    
    # Timeline visualization
    print("="*100)
    print("TIMELINE VISUALIZATION")
    print("="*100)
    print()
    print("Time        | Game        | Action | Price  | Score           | P/L")
    print("-"*100)
    
    # Combine entries and exits for chronological view
    events = []
    
    for idx, row in df.iterrows():
        game_id = row['game_id']
        away, home = game_info.get(game_id, ('???', '???'))
        game_label = f"{away}@{home}"
        
        # Entry event
        events.append({
            'timestamp': row['entry_timestamp'],
            'game': game_label,
            'action': 'ENTRY',
            'price': row['entry_price'],
            'score': f"{row['entry_score_away']}-{row['entry_score_home']}",
            'pl': None,
            'trade_num': idx + 1
        })
        
        # Exit event
        events.append({
            'timestamp': row['exit_timestamp'],
            'game': game_label,
            'action': 'EXIT',
            'price': row['exit_price'],
            'score': f"{row['exit_score_away']}-{row['exit_score_home']}",
            'pl': row['net_profit'],
            'trade_num': idx + 1,
            'won': row['won']
        })
    
    # Sort by timestamp
    events.sort(key=lambda x: x['timestamp'])
    
    for event in events:
        time_str = event['timestamp'].strftime('%I:%M:%S %p')
        pl_str = ""
        if event['pl'] is not None:
            if event['won']:
                pl_str = f"${event['pl']:+7.2f} [W]"
            else:
                pl_str = f"${event['pl']:+7.2f} [L]"
        
        action_str = f"T{event['trade_num']} {event['action']}"
        
        print(f"{time_str:<12} {event['game']:<12} {action_str:<12} ${event['price']:<6.0f} {event['score']:<16} {pl_str}")


if __name__ == "__main__":
    get_trade_timeline()

