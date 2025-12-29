"""
Check what Kalshi data is available for recent games
Tests different endpoints to see what we can fetch
"""
import sys
import os
sys.path.insert(0, os.getcwd())

from src.data.kalshi_api import KalshiAPIClient, load_kalshi_credentials
import requests
import json

# Initialize Kalshi
api_key, private_key = load_kalshi_credentials()
kalshi = KalshiAPIClient(api_key, private_key)

# Test with yesterday's Lakers game
print("Testing Kalshi data availability for recent game...")
print("="*80)

markets = kalshi.find_nba_markets('SAC', 'LAL')

if markets:
    print(f"\nFound {len(markets)} markets:")
    for m in markets:
        print(f"\n  Ticker: {m['ticker']}")
        print(f"  Title: {m['title']}")
        print(f"  Status: {m.get('status', 'N/A')}")
        print(f"  Close Time: {m.get('close_time', 'N/A')}")
        
        ticker = m['ticker']
        
        # Try different endpoints
        print(f"\n  Testing endpoints for {ticker}:")
        
        # 1. Market details
        try:
            path = f"/markets/{ticker}"
            headers = kalshi._get_auth_headers("GET", path)
            resp = requests.get(f"{kalshi.base_url}{path}", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                print(f"    ✓ /markets/{ticker} - Available")
                market_data = data.get('market', {})
                print(f"      Status: {market_data.get('status')}")
                print(f"      Last Price: {market_data.get('last_price', 'N/A')}")
            else:
                print(f"    ✗ /markets/{ticker} - {resp.status_code}")
        except Exception as e:
            print(f"    ✗ /markets/{ticker} - Error: {e}")
        
        # 2. Market history
        try:
            path = f"/markets/{ticker}/history"
            headers = kalshi._get_auth_headers("GET", path)
            resp = requests.get(f"{kalshi.base_url}{path}", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                history = data.get('history', [])
                print(f"    ✓ /markets/{ticker}/history - {len(history)} records")
                if history:
                    print(f"      Sample: {history[0]}")
            else:
                print(f"    ✗ /markets/{ticker}/history - {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"    ✗ /markets/{ticker}/history - Error: {e}")
        
        # 3. Market orderbook
        try:
            path = f"/markets/{ticker}/orderbook"
            headers = kalshi._get_auth_headers("GET", path)
            resp = requests.get(f"{kalshi.base_url}{path}", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                print(f"    ✓ /markets/{ticker}/orderbook - Available")
            else:
                print(f"    ✗ /markets/{ticker}/orderbook - {resp.status_code}")
        except Exception as e:
            print(f"    ✗ /markets/{ticker}/orderbook - Error: {e}")
        
        # 4. Market trades
        try:
            path = f"/markets/{ticker}/trades"
            headers = kalshi._get_auth_headers("GET", path)
            resp = requests.get(f"{kalshi.base_url}{path}", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                trades = data.get('trades', [])
                print(f"    ✓ /markets/{ticker}/trades - {len(trades)} trades")
                if trades:
                    print(f"      Sample: {trades[0]}")
            else:
                print(f"    ✗ /markets/{ticker}/trades - {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"    ✗ /markets/{ticker}/trades - Error: {e}")

print("\n" + "="*80)
print("\nConclusion:")
print("- If /history or /trades have data, we can download it")
print("- If not, data might not be available yet for recent games")
print("- Kalshi may take 1-2 days to populate historical data")
print("="*80)


