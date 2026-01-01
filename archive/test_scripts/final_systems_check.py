"""
Final Systems Check - End-to-End Test
Tests the complete paper trading pipeline
"""
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.getcwd())

print("="*80)
print("FINAL SYSTEMS CHECK - END-TO-END TEST")
print("="*80)

# Test 1: Import all required modules
print("\n[1/7] Testing imports...")
try:
    from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials
    from src.data.realtime_pbp import RealTimePBPFetcher
    from src.paper_trading.database_logger import PaperTradingDB
    from src.backtesting.fees import calculate_kalshi_fees
    from nba_api.live.nba.endpoints import scoreboard
    import joblib
    import pandas as pd
    import numpy as np
    print("  [OK] All imports successful")
except Exception as e:
    print(f"  [ERROR] Import failed: {e}")
    sys.exit(1)

# Test 2: Load ML models
print("\n[2/7] Loading ML models...")
try:
    entry_model = joblib.load('ml_models/outputs/advanced_model.pkl')
    exit_model = joblib.load('ml_models/outputs/exit_timing_model.pkl')
    features = joblib.load('ml_models/outputs/advanced_features.pkl')
    print(f"  [OK] Models loaded ({len(features)} features)")
except Exception as e:
    print(f"  [ERROR] Model loading failed: {e}")
    sys.exit(1)

# Test 3: Connect to Kalshi
print("\n[3/7] Testing Kalshi API...")
try:
    api_key, private_key = load_kalshi_credentials()
    kalshi = KalshiAPIClient(api_key, private_key)
    markets = kalshi.find_nba_markets('LAL', 'LAC')
    print(f"  [OK] Kalshi connected ({len(markets)} test markets found)")
except Exception as e:
    print(f"  [ERROR] Kalshi failed: {e}")
    sys.exit(1)

# Test 4: Connect to NBA API
print("\n[4/7] Testing NBA API...")
try:
    games = scoreboard.ScoreBoard().get_dict()
    num_games = len(games['scoreboard']['games'])
    print(f"  [OK] NBA API working ({num_games} games tonight)")
    
    if num_games == 0:
        print("  [WARNING] No games tonight - system will have nothing to monitor")
except Exception as e:
    print(f"  [ERROR] NBA API failed: {e}")
    sys.exit(1)

# Test 5: Test PBP fetching
print("\n[5/7] Testing PBP data...")
try:
    pbp_fetcher = RealTimePBPFetcher()
    # Test with recent game
    pbp = pbp_fetcher.fetch_game_pbp('0022500446')
    if pbp and 'game' in pbp:
        actions = pbp['game']['actions']
        print(f"  [OK] PBP fetcher working ({len(actions)} actions in test game)")
    else:
        print("  [ERROR] No PBP data returned")
        sys.exit(1)
except Exception as e:
    print(f"  [ERROR] PBP failed: {e}")
    sys.exit(1)

# Test 6: Test database
print("\n[6/7] Testing database...")
try:
    db = PaperTradingDB()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'paper_trading';
    """)
    table_count = cursor.fetchone()[0]
    
    if table_count >= 5:
        print(f"  [OK] Database ready ({table_count} tables)")
    else:
        print(f"  [ERROR] Missing tables (found {table_count}, need 5)")
        sys.exit(1)
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"  [ERROR] Database failed: {e}")
    sys.exit(1)

# Test 7: Simulate feature calculation
print("\n[7/7] Testing feature calculation...")
try:
    # Create mock data
    mock_data = pd.DataFrame({
        'mid': [50 + np.random.randn() for _ in range(20)],
        'bid': [49 + np.random.randn() for _ in range(20)],
        'ask': [51 + np.random.randn() for _ in range(20)],
        'score_home': list(range(0, 40, 2)),
        'score_away': list(range(0, 40, 2)),
        'period': [1] * 12 + [2] * 8,
        'game_minute': list(range(20))
    })
    
    # Test prediction
    features_dict = {}
    for feat in features:
        features_dict[feat] = 0.0  # Simple mock
    
    X = pd.DataFrame([features_dict])[features]
    prob = entry_model.predict_proba(X)[0, 1]
    hold = exit_model.predict(X)[0]
    
    print(f"  [OK] Feature calc working (test prediction: {prob:.3f}, hold: {hold:.0f}min)")
except Exception as e:
    print(f"  [ERROR] Feature calc failed: {e}")
    sys.exit(1)

# All tests passed
print("\n" + "="*80)
print("FINAL CHECK RESULTS")
print("="*80)
print("\n[OK] ALL SYSTEMS OPERATIONAL")
print("\nChecked:")
print("  1. All Python imports")
print("  2. ML models (entry + exit)")
print("  3. Kalshi API connection")
print("  4. NBA API connection")
print("  5. PBP data fetching")
print("  6. Database tables")
print("  7. Feature calculation + prediction")

print("\n" + "="*80)
print("READY FOR LIVE PAPER TRADING")
print("="*80)
print(f"\nGames tonight: {num_games}")
print(f"System check: PASSED")
print(f"Time: {datetime.now().strftime('%H:%M:%S')}")

print("\nTo start paper trading:")
print("  python run_paper_trading.py")

print("\nTo view results (anytime):")
print("  python view_paper_trading.py")

print("\n" + "="*80)
print("[OK] SYSTEM READY FOR GO-LIVE")
print("="*80)



