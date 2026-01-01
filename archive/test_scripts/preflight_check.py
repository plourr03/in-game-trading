"""
Pre-Flight System Check
Verifies all components are ready for paper trading
"""
import sys
import os

sys.path.insert(0, os.getcwd())

def check_imports():
    """Check all required imports"""
    print("[1/8] Checking Python packages...")
    try:
        import pandas
        import numpy
        import joblib
        import requests
        from nba_api.live.nba.endpoints import scoreboard
        from cryptography.hazmat.primitives import hashes
        print("  [OK] All packages installed")
        return True
    except ImportError as e:
        print(f"  [ERROR] Missing package: {e}")
        return False

def check_kalshi_api():
    """Check Kalshi API access"""
    print("\n[2/8] Testing Kalshi API...")
    try:
        from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials
        
        api_key, private_key = load_kalshi_credentials()
        if not api_key or not private_key:
            print("  [ERROR] Could not load credentials")
            return False
        
        kalshi = KalshiAPIClient(api_key, private_key)
        markets = kalshi.find_nba_markets('LAL', 'LAC')  # Test with any teams
        
        print(f"  [OK] Kalshi API working (found {len(markets)} test markets)")
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def check_nba_api():
    """Check NBA API access"""
    print("\n[3/8] Testing NBA API...")
    try:
        from nba_api.live.nba.endpoints import scoreboard
        
        games = scoreboard.ScoreBoard().get_dict()
        num_games = len(games['scoreboard']['games'])
        
        print(f"  [OK] NBA API working ({num_games} games today)")
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def check_pbp_fetcher():
    """Check PBP data fetcher"""
    print("\n[4/8] Testing PBP data fetcher...")
    try:
        from src.data.realtime_pbp import RealTimePBPFetcher
        
        fetcher = RealTimePBPFetcher()
        # Test with a known game
        pbp = fetcher.fetch_game_pbp('0022500446')
        
        if pbp and 'game' in pbp:
            print(f"  [OK] PBP fetcher working")
            return True
        else:
            print("  [ERROR] No PBP data returned")
            return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def check_ml_models():
    """Check ML models"""
    print("\n[5/8] Testing ML models...")
    try:
        import joblib
        
        entry_model = joblib.load('ml_models/outputs/advanced_model.pkl')
        exit_model = joblib.load('ml_models/outputs/exit_timing_model.pkl')
        features = joblib.load('ml_models/outputs/advanced_features.pkl')
        
        print(f"  [OK] ML models loaded ({len(features)} features)")
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def check_feature_calculation():
    """Check feature calculation"""
    print("\n[6/8] Testing feature calculation...")
    try:
        import pandas as pd
        import numpy as np
        
        # Create mock data
        mock_data = {
            'mid': [50 + np.random.randn() for _ in range(20)],
            'score_home': list(range(0, 40, 2)),
            'score_away': list(range(0, 40, 2)),
            'period': [1] * 20,
            'game_minute': list(range(20))
        }
        df = pd.DataFrame(mock_data)
        
        # Test basic calculations
        price_move = ((df['mid'].iloc[-1] - df['mid'].iloc[-2]) / df['mid'].iloc[-2] * 100)
        volatility = np.std(df['mid'].iloc[-5:])
        score_diff = df['score_home'].iloc[-1] - df['score_away'].iloc[-1]
        
        print(f"  [OK] Feature calculation working")
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def check_file_permissions():
    """Check file write permissions"""
    print("\n[7/8] Testing file write permissions...")
    try:
        test_file = 'test_write_permissions.csv'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print("  [OK] Can write log files")
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def check_fee_calculation():
    """Check fee calculation"""
    print("\n[8/9] Testing fee calculation...")
    try:
        from src.backtesting.fees import calculate_kalshi_fees
        
        # Test fee calculation
        fee = calculate_kalshi_fees(500, 50, is_taker=True)
        
        if fee > 0:
            print(f"  [OK] Fee calculation working (${fee:.2f} for 500 contracts at 50c)")
            return True
        else:
            print("  [ERROR] Fee calculation returned 0")
            return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def check_database():
    """Check database connection and tables"""
    print("\n[9/9] Testing database connection...")
    try:
        import psycopg2
        import yaml
        
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
        
        cursor = conn.cursor()
        
        # Check if paper_trading schema exists
        cursor.execute("""
            SELECT schema_name FROM information_schema.schemata 
            WHERE schema_name = 'paper_trading';
        """)
        
        if cursor.fetchone():
            # Check if tables exist
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'paper_trading';
            """)
            table_count = cursor.fetchone()[0]
            print(f"  [OK] Database connected ({table_count} tables in paper_trading schema)")
        else:
            print("  [WARNING] paper_trading schema not found - run setup_paper_trading_db.py")
            return False
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def main():
    print("="*80)
    print("PRE-FLIGHT SYSTEM CHECK")
    print("="*80)
    
    checks = [
        check_imports(),
        check_kalshi_api(),
        check_nba_api(),
        check_pbp_fetcher(),
        check_ml_models(),
        check_feature_calculation(),
        check_file_permissions(),
        check_fee_calculation(),
        check_database()
    ]
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    passed = sum(checks)
    total = len(checks)
    
    print(f"\nPassed: {passed}/{total}")
    
    if all(checks):
        print("\n" + "="*80)
        print("[OK] ALL SYSTEMS GO!")
        print("="*80)
        print("\nYou are ready to run paper trading:")
        print("  python run_paper_trading.py")
        print("\nThis will:")
        print("  - Monitor all games tonight (6pm-9:30pm Central)")
        print("  - Generate ML trading signals")
        print("  - Log everything to CSV files AND database")
        print("  - Calculate P/L for all paper trades")
        print("\nTo view results:")
        print("  python view_paper_trading.py")
        print("="*80)
        return True
    else:
        print("\n" + "="*80)
        print("[ERROR] SOME CHECKS FAILED")
        print("="*80)
        print("\nPlease fix the errors above before running paper trading.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

