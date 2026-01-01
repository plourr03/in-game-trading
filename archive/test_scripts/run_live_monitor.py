"""
Real-time trading signal monitor
Fetches live Kalshi prices and NBA play-by-play data, runs ML model predictions
"""
import sys
import time
import pandas as pd
import numpy as np
from datetime import datetime
import logging

from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials
from src.data.realtime_pbp import RealtimeNBAPBP, calculate_game_minute
from trading_engine.signals.ml_signal_generator import MLSignalGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def monitor_game(team1: str, team2: str, game_id: str, duration_minutes: int = 30):
    """
    Monitor a live game and display trading signals
    
    Args:
        team1: First team abbreviation (e.g., 'LAL')
        team2: Second team abbreviation (e.g., 'SAC')
        game_id: NBA game ID
        duration_minutes: How long to monitor
    """
    print("="*80)
    print(f"LIVE TRADING MONITOR: {team1} @ {team2}")
    print(f"Game ID: {game_id}")
    print("="*80)
    
    # Load credentials
    api_key, private_key = load_kalshi_credentials()
    if not api_key:
        print("[ERROR] Failed to load Kalshi credentials")
        return
    
    # Initialize clients
    kalshi = KalshiAPIClient(api_key, private_key)
    nba_api = RealtimeNBAPBP()
    ml_model = MLSignalGenerator()
    
    print("\n[1/3] Finding Kalshi markets...")
    markets = kalshi.find_nba_markets(team1, team2)
    
    if not markets:
        print(f"[ERROR] No Kalshi markets found for {team1} vs {team2}")
        return
    
    # Use first market (usually the main game winner market)
    market = markets[0]
    ticker = market['ticker']
    print(f"[OK] Monitoring market: {ticker}")
    print(f"     {market['title']}")
    
    print("\n[2/3] Loading ML model...")
    if not ml_model.entry_model:
        print("[ERROR] ML model failed to load")
        return
    print(f"[OK] ML model ready")
    
    print("\n[3/3] Starting live monitor...")
    print(f"     Will run for {duration_minutes} minutes")
    print(f"     Polling every 10 seconds")
    print("\n" + "="*80)
    
    # Store history for feature calculation
    price_history = []
    
    start_time = time.time()
    iteration = 0
    
    try:
        while time.time() - start_time < duration_minutes * 60:
            iteration += 1
            
            # Fetch current data
            price_data = kalshi.get_live_price(ticker)
            pbp_data = nba_api.get_live_pbp(game_id)
            
            if not price_data or pbp_data.empty:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for data...")
                time.sleep(10)
                continue
            
            # Get latest game state
            latest_play = pbp_data.iloc[-1]
            
            # Create a data point for the model
            current_time = datetime.now()
            data_point = {
                'datetime': current_time,
                'ticker': ticker,
                'price': price_data['mid'],
                'yes_bid': price_data['bid'],
                'yes_ask': price_data['ask'],
                'volume': 0,  # We don't have volume from orderbook
                'game_id': game_id,
                'score_home': latest_play['SCOREMARGIN'],  # We'll parse this
                'score_away': 0,  # Will calculate
                'period': latest_play['PERIOD'],
                'pctimestring': latest_play['PCTIMESTRING']
            }
            
            # Add to history
            price_history.append(data_point)
            
            # Need at least 10 minutes of data for features
            if len(price_history) < 10:
                print(f"[{current_time.strftime('%H:%M:%S')}] Collecting data... ({len(price_history)}/10 samples)")
                time.sleep(10)
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(price_history[-60:])  # Last 60 samples (10 minutes if polling every 10s)
            
            # Generate signal
            try:
                signal = ml_model.generate_signal(df, df.index[-1])
                
                # Display current state
                print(f"\n[{current_time.strftime('%H:%M:%S')}] Iteration {iteration}")
                print(f"  Price: {price_data['mid']:.1f}c (Bid: {price_data['bid']:.0f}, Ask: {price_data['ask']:.0f})")
                print(f"  Score: {latest_play.get('SCORE', 'N/A')}")
                print(f"  Period: {latest_play['PERIOD']}, Time: {latest_play['PCTIMESTRING']}")
                
                if signal['action'] == 'BUY':
                    print(f"  >> SIGNAL: BUY <<")
                    print(f"     Confidence: {signal['confidence']:.1%}")
                    print(f"     Expected Hold: {signal['suggested_hold_minutes']} minutes")
                    print(f"     Position Size: {signal['position_size']} contracts")
                elif signal['action'] == 'HOLD':
                    print(f"  Signal: HOLD (Confidence: {signal['confidence']:.1%})")
                else:
                    print(f"  Signal: WAIT (Confidence: {signal['confidence']:.1%})")
                
            except Exception as e:
                print(f"  [ERROR] Failed to generate signal: {e}")
            
            # Wait before next poll
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n[OK] Monitor stopped by user")
    
    print("\n" + "="*80)
    print(f"[OK] Monitoring complete - ran for {(time.time() - start_time)/60:.1f} minutes")
    print(f"     Collected {len(price_history)} data points")
    print("="*80)


if __name__ == "__main__":
    # Monitor Lakers @ Kings game
    monitor_game(
        team1='LAL',
        team2='SAC', 
        game_id='0022400445',  # Today's game
        duration_minutes=30
    )



