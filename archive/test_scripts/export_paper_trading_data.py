"""
Export Paper Trading Data to Kalshi Format
Converts collected paper trading data into training data format
"""
import pandas as pd
import psycopg2
import yaml
import os
from datetime import datetime

def export_session_data(session_id=None, output_folder='kalshi_data/jan_dec_2025_games'):
    """Export paper trading session data to Kalshi CSV format"""
    
    print("="*80)
    print("EXPORTING PAPER TRADING DATA TO TRAINING FORMAT")
    print("="*80)
    
    # Connect to database
    print("\n[1/4] Connecting to database...")
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    db_config = config['database']
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )
    print("  [OK] Connected")
    
    # Get latest session if not specified
    print("\n[2/4] Finding session to export...")
    if session_id is None:
        session_df = pd.read_sql("""
            SELECT session_id, start_time, games_monitored, total_signals, total_trades
            FROM paper_trading.sessions 
            ORDER BY start_time DESC LIMIT 1;
        """, conn)
        
        if session_df.empty:
            print("  [ERROR] No sessions found")
            conn.close()
            return
        
        session_id = session_df['session_id'].iloc[0]
        print(f"  [OK] Using latest session: {session_id}")
        print(f"      Start time: {session_df['start_time'].iloc[0]}")
        print(f"      Games: {session_df['games_monitored'].iloc[0]}")
        print(f"      Signals: {session_df['total_signals'].iloc[0]}")
        print(f"      Trades: {session_df['total_trades'].iloc[0]}")
    
    # Get price data
    print(f"\n[3/4] Fetching price data from session {session_id}...")
    prices = pd.read_sql(f"""
        SELECT 
            timestamp as datetime,
            ticker,
            price_mid as close,
            price_bid as open,
            price_ask as high,
            price_mid as low,
            0 as volume,
            game_id,
            away_team,
            home_team,
            TO_CHAR(timestamp, 'YYYY-MM-DD') as game_date
        FROM paper_trading.price_data
        WHERE session_id = {session_id}
        ORDER BY game_id, timestamp;
    """, conn)
    
    if prices.empty:
        print("  [ERROR] No price data found")
        conn.close()
        return
    
    print(f"  [OK] Found {len(prices)} price points across {prices['ticker'].nunique()} games")
    
    # Create output folder
    print(f"\n[4/4] Saving to {output_folder}...")
    os.makedirs(output_folder, exist_ok=True)
    
    # Save each game separately
    saved = 0
    skipped = 0
    
    for ticker in prices['ticker'].unique():
        if ticker is None or pd.isna(ticker):
            skipped += 1
            continue
            
        game_data = prices[prices['ticker'] == ticker].copy()
        
        # Reorder columns to match training data format
        game_data = game_data[['datetime', 'open', 'high', 'low', 'close', 'volume', 
                               'ticker', 'game_id', 'away_team', 'home_team', 'game_date']]
        
        # Check if file already exists
        output_file = os.path.join(output_folder, f"{ticker}.csv")
        if os.path.exists(output_file):
            print(f"  [SKIP] {ticker} - file already exists")
            skipped += 1
            continue
        
        # Save to CSV
        game_data.to_csv(output_file, index=False)
        print(f"  [OK] Saved {len(game_data)} rows for {ticker}")
        saved += 1
    
    conn.close()
    
    # Summary
    print("\n" + "="*80)
    print("EXPORT COMPLETE")
    print("="*80)
    print(f"Saved: {saved} new games")
    print(f"Skipped: {skipped} games (already exist)")
    print(f"Output folder: {output_folder}")
    
    if saved > 0:
        print("\nNext steps:")
        print("  1. Retrain your model with the new data:")
        print("     cd ml_models")
        print("     python prepare_training_data.py")
        print("     python train_models.py")
        print("\n  2. Test the updated model:")
        print("     python test_optimized_model.py")
    
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Export paper trading data to training format')
    parser.add_argument('--session', type=int, default=None,
                       help='Session ID to export (default: latest)')
    parser.add_argument('--output', type=str, default='kalshi_data/jan_dec_2025_games',
                       help='Output folder for CSV files')
    
    args = parser.parse_args()
    
    export_session_data(session_id=args.session, output_folder=args.output)



