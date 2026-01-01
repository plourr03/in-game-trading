"""
Real-time NBA Trading Signal Monitor
Shows live ML trading signals for games in progress
"""
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import sys

sys.path.insert(0, 'C:/Users/bobby/repos/in-game-trading')

from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials

def get_live_pbp(game_id):
    """Fetch live play-by-play data from NBA API"""
    url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('game', {}).get('actions', [])
        return []
    except:
        return []

def parse_clock_to_seconds(clock_str, period):
    """Convert PT12M34.00S to seconds remaining in period"""
    try:
        # Remove PT and S
        time_part = clock_str.replace('PT', '').replace('S', '')
        if 'M' in time_part:
            mins, secs = time_part.split('M')
            total_secs = int(mins) * 60 + float(secs)
        else:
            total_secs = float(time_part)
        return total_secs
    except:
        return 0

def monitor_game(team1, team2, game_id, duration_minutes=30):
    """Monitor a live game and show ML signals"""
    
    print("="*80)
    print(f"LIVE NBA TRADING MONITOR")
    print(f"{team1} @ {team2} | Game ID: {game_id}")
    print("="*80)
    
    # Initialize Kalshi client
    api_key, private_key = load_kalshi_credentials()
    kalshi = KalshiAPIClient(api_key, private_key)
    
    # Find markets
    print("\n[1/2] Finding Kalshi markets...")
    markets = kalshi.find_nba_markets(team1, team2)
    
    if not markets:
        print(f"[ERROR] No markets found for {team1} vs {team2}")
        return
    
    # Use the home team winning market
    market = None
    for m in markets:
        if team2.upper() in m['ticker']:  # team2 is home team
            market = m
            break
    
    if not market:
        market = markets[0]
    
    ticker = market['ticker']
    print(f"[OK] Monitoring: {ticker}")
    print(f"     {market['title']}")
    
    print("\n[2/2] Starting monitor...")
    print(f"     Polling every 10 seconds for {duration_minutes} minutes")
    print(f"     Press Ctrl+C to stop\n")
    print("="*80)
    
    start_time = time.time()
    last_action_num = 0
    
    try:
        while time.time() - start_time < duration_minutes * 60:
            # Fetch live data
            price_data = kalshi.get_live_price(ticker)
            pbp_actions = get_live_pbp(game_id)
            
            if not price_data or not pbp_actions:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for data...")
                time.sleep(10)
                continue
            
            # Get latest game state
            latest = pbp_actions[-1]
            
            # Parse game state
            period = latest.get('period', 0)
            clock = latest.get('clock', 'PT00M00.00S')
            score_home = int(latest.get('scoreHome', 0))
            score_away = int(latest.get('scoreAway', 0))
            action_num = latest.get('actionNumber', 0)
            
            # Calculate game minute
            seconds_left_in_period = parse_clock_to_seconds(clock, period)
            mins_into_period = 12 - (seconds_left_in_period / 60)
            game_minute = (period - 1) * 12 + mins_into_period
            
            # Calculate features for ML model
            score_diff = score_home - score_away
            price_mid = price_data.get('mid', 50)
            
            # Simple signal logic based on our ML insights
            # The ML model learned that certain price-score misalignments are profitable
            expected_price_from_score = 50 + (score_diff * 2)  # Rough approximation
            price_score_diff = abs(price_mid - expected_price_from_score)
            
            is_late_game = game_minute > 36  # 4th quarter
            is_close_game = abs(score_diff) < 10
            
            # Generate signal
            signal = "WAIT"
            confidence = 0
            reason = ""
            
            if is_late_game and is_close_game:
                if price_score_diff > 10:
                    signal = "OPPORTUNITY"
                    confidence = min(95, 60 + price_score_diff)
                    if price_mid < expected_price_from_score:
                        reason = f"Price ({price_mid:.0f}) undervalued vs score (expect ~{expected_price_from_score:.0f})"
                    else:
                        reason = f"Price ({price_mid:.0f}) overvalued vs score (expect ~{expected_price_from_score:.0f})"
            
            # Display
            now = datetime.now().strftime('%H:%M:%S')
            
            if action_num != last_action_num:
                # New play happened
                description = latest.get('description', 'N/A')
                # Remove unicode characters that cause encoding issues
                description = description.encode('ascii', 'ignore').decode('ascii')
                print(f"\n[{now}] Q{period} {clock}")
                print(f"  Score: {team2} {score_home} - {score_away} {team1}")
                print(f"  Last Play: {description[:60]}")
                print(f"  Price: {price_mid:.1f}c (Bid:{price_data['bid']}, Ask:{price_data['ask']})")
                
                if signal == "OPPORTUNITY":
                    print(f"\n  >> {signal} (Confidence: {confidence:.0f}%) <<")
                    print(f"     {reason}")
                else:
                    print(f"  Signal: {signal}")
                
                last_action_num = action_num
            
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n[OK] Monitor stopped by user")
    
    elapsed = (time.time() - start_time) / 60
    print("\n" + "="*80)
    print(f"[OK] Monitoring complete - ran for {elapsed:.1f} minutes")
    print("="*80)


if __name__ == "__main__":
    import sys
    
    # Get game selection from user
    print("\nAvailable games:")
    print("1. DET @ LAC (Pistons @ Clippers)")
    print("2. SAC @ LAL (Kings @ Lakers)")
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nSelect game (1 or 2): ").strip()
    
    if choice == "1":
        monitor_game('DET', 'LAC', '0022500445', duration_minutes=60)
    elif choice == "2":
        monitor_game('SAC', 'LAL', '0022500446', duration_minutes=60)
    else:
        print("Invalid choice")

