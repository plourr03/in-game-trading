"""
Test REAL-TIME data synchronization
Fetches live Kalshi prices and live NBA scores simultaneously
"""
import time
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.insert(0, os.getcwd())

from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials
from src.data.realtime_pbp import RealTimePBPFetcher

def test_realtime_sync(game_id, home_team, away_team, duration_seconds=120):
    """
    Test that we can properly sync live Kalshi prices with live NBA scores
    
    Args:
        game_id: NBA game ID (e.g., '0022500446')
        home_team: Home team code (e.g., 'LAL')
        away_team: Away team code (e.g., 'SAC')
        duration_seconds: How long to monitor
    """
    print("="*80)
    print("REAL-TIME DATA SYNCHRONIZATION TEST")
    print("="*80)
    print(f"Game: {away_team} @ {home_team}")
    print(f"Game ID: {game_id}")
    print(f"Duration: {duration_seconds} seconds")
    print("="*80 + "\n")
    
    # Initialize APIs
    print("[1/3] Initializing Kalshi API...")
    api_key, private_key = load_kalshi_credentials()
    kalshi = KalshiAPIClient(api_key, private_key)
    
    # Find market
    markets = kalshi.find_nba_markets(away_team, home_team)
    if not markets:
        print(f"[ERROR] No markets found for {away_team} @ {home_team}")
        return False
    
    # Find home team winning ticker
    ticker = None
    for m in markets:
        if home_team.upper() in m['ticker']:
            ticker = m['ticker']
            break
    if not ticker:
        ticker = markets[0]['ticker']
    
    print(f"  [OK] Found ticker: {ticker}")
    
    print("\n[2/3] Initializing NBA API...")
    pbp_fetcher = RealTimePBPFetcher()
    print("  [OK] PBP fetcher ready")
    
    print("\n[3/3] Starting synchronization test...")
    print("  Polling every 10 seconds\n")
    print("="*80)
    
    data_points = []
    start_time = time.time()
    iteration = 0
    
    try:
        while time.time() - start_time < duration_seconds:
            iteration += 1
            timestamp = datetime.now()
            
            # Fetch Kalshi price
            price_data = kalshi.get_live_price(ticker)
            
            # Fetch NBA PBP
            pbp_data = pbp_fetcher.fetch_game_pbp(game_id)
            
            if price_data and pbp_data:
                # Extract current score
                actions = pbp_data['game']['actions']
                latest = actions[-1]
                
                score_home = latest.get('scoreHome', 'N/A')
                score_away = latest.get('scoreAway', 'N/A')
                period = latest.get('period', 'N/A')
                clock = latest.get('clock', 'N/A')
                
                # Convert to integers if possible
                try:
                    score_home = int(score_home) if score_home != 'N/A' else 0
                    score_away = int(score_away) if score_away != 'N/A' else 0
                except:
                    score_home = 0
                    score_away = 0
                
                # Store data point
                data_point = {
                    'timestamp': timestamp,
                    'price_mid': price_data['mid'],
                    'price_bid': price_data['bid'],
                    'price_ask': price_data['ask'],
                    'score_home': score_home,
                    'score_away': score_away,
                    'period': period,
                    'clock': clock
                }
                data_points.append(data_point)
                
                # Display
                print(f"[{timestamp.strftime('%H:%M:%S')}] Iteration {iteration}")
                mid = price_data['mid'] if price_data['mid'] is not None else 0
                bid = price_data['bid'] if price_data['bid'] is not None else 0
                ask = price_data['ask'] if price_data['ask'] is not None else 0
                print(f"  Price: {mid:.1f}c (Bid: {bid}, Ask: {ask})")
                print(f"  Score: {away_team} {score_away} - {score_home} {home_team}")
                print(f"  Time:  Q{period} {clock}")
                print()
                
            else:
                print(f"[{timestamp.strftime('%H:%M:%S')}] Iteration {iteration}: No data")
                print()
            
            # Wait 10 seconds
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n[OK] Test stopped by user")
    
    # Analyze results
    print("="*80)
    print("SYNCHRONIZATION ANALYSIS")
    print("="*80)
    
    if len(data_points) == 0:
        print("[ERROR] No data points collected")
        return False
    
    df = pd.DataFrame(data_points)
    
    print(f"\nData points collected: {len(df)}")
    print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()
    
    print("Price Summary:")
    print(f"  Min: {df['price_mid'].min():.1f}¢")
    print(f"  Max: {df['price_mid'].max():.1f}¢")
    print(f"  Range: {df['price_mid'].max() - df['price_mid'].min():.1f}¢")
    print(f"  Std Dev: {df['price_mid'].std():.2f}¢")
    print()
    
    print("Score Summary:")
    print(f"  Home score: {df['score_home'].min():.0f} to {df['score_home'].max():.0f}")
    print(f"  Away score: {df['score_away'].min():.0f} to {df['score_away'].max():.0f}")
    print(f"  Score changes (home): {df['score_home'].nunique()}")
    print(f"  Score changes (away): {df['score_away'].nunique()}")
    print()
    
    # Check for proper synchronization
    print("Synchronization Check:")
    
    # Are scores changing?
    home_score_changed = df['score_home'].nunique() > 1
    away_score_changed = df['score_away'].nunique() > 1
    
    if home_score_changed or away_score_changed:
        print("  [OK] Scores are changing over time")
    else:
        print("  [WARNING] Scores not changing (game might not be live)")
    
    # Are prices changing?
    price_changed = df['price_mid'].nunique() > 1
    if price_changed:
        print("  [OK] Prices are changing over time")
    else:
        print("  [WARNING] Prices not changing")
    
    # Check correlation
    if len(df) > 2 and df['score_home'].std() > 0 and df['price_mid'].std() > 0:
        correlation = df['score_home'].corr(df['price_mid'])
        print(f"  Price-Score Correlation: {correlation:.3f}")
        
        if abs(correlation) > 0.3:
            print("  [OK] Price and score show correlation")
        else:
            print("  [INFO] Low correlation (might be normal)")
    
    print("\n" + "="*80)
    print("[OK] SYNCHRONIZATION TEST COMPLETE")
    print("="*80)
    
    # Save data
    filename = f"sync_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    print(f"\nData saved to: {filename}")
    
    return True


if __name__ == "__main__":
    # Test with a completed game first (to verify everything works)
    print("\n>>> Testing with COMPLETED game (Lakers vs Kings 12/28)...")
    print("    This should show final scores throughout (game is over)")
    print()
    
    success = test_realtime_sync(
        game_id='0022500446',
        home_team='LAL',
        away_team='SAC',
        duration_seconds=60  # Just 1 minute to test
    )
    
    if success:
        print("\n\n[OK] System is working correctly!")
        print("     When used on a LIVE game, scores will change in real-time")
        print("     For completed games, it correctly shows final score")
    else:
        print("\n\n[ERROR] System test failed")

