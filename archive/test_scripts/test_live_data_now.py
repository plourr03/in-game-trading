"""
Test Live Data Fetching - Kings @ Clippers
Verify we can get Kalshi and NBA data in real-time
"""
import os
import sys
sys.path.insert(0, os.getcwd())

from src.data.kalshi_api import KalshiAPIClient
from src.data.realtime_pbp import RealTimePBPFetcher
from datetime import datetime
import time

def test_live_data():
    print("="*80)
    print("LIVE DATA TEST - Kings @ Clippers")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    game_id = "0022500461"
    
    # 1. Test NBA Play-by-Play
    print("\n[1/2] Testing NBA Play-by-Play Data...")
    print("-"*80)
    
    pbp_fetcher = RealTimePBPFetcher()
    
    try:
        pbp_data = pbp_fetcher.fetch_game_pbp(game_id)
        
        if pbp_data and len(pbp_data) > 0:
            print(f"  [SUCCESS] Got {len(pbp_data)} play-by-play actions")
            
            latest = pbp_data[-1]
            print(f"\n  Latest Action:")
            print(f"    Period: {latest.get('period', 'N/A')}")
            print(f"    Clock: {latest.get('clock', 'N/A')}")
            print(f"    Score: {latest.get('scoreHome', 'N/A')} - {latest.get('scoreAway', 'N/A')}")
            print(f"    Description: {latest.get('description', 'N/A')[:60]}")
        else:
            print(f"  [WARNING] No PBP data available yet (game may not have started)")
            
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    # 2. Test Kalshi Market Data
    print("\n[2/2] Testing Kalshi Market Data...")
    print("-"*80)
    
    api_key = "484e8b29-4d36-43f7-a583-bb80a3d5e460"
    private_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEA5tpRZdn0YBQHosQ35Q7VbDU8HYEsanzhjQGr+LgXk8kiec+y
AS6XSSQOcCrmZyJQ947kS8Y9mkNRAiBIBjDlkqFheW+FA2+etD2iTsL1Nt7K+UZU
QWQLzi/UhgQux9Ni8kTPf/j8HbPoEHQqMJTGVXgKKZv1soRBU7iUwMr2fmjcB8aX
28pvlCQy8Ku2SPY+8lofqBWa8FNH7rbK5bw/Nvm5oDP9+8Q7KSnzKMK61FZPwK+w
AGRRIXRVfIEwNydUxP0UyB+VBzF6HAQ0FPJtFauh8m/Ky+Vv5BYrVbmGYx1dSh2v
edDz0sPMAB1zVstTjOwgEnRZ+CzV0KqckRE5GQIDAQABAoH/D/r8kUrV1sr2ihb6
0hPaya+sbyLQU6mtwlCy+2r3kN22tlgbtWz2ypQcbheQAOtaihgKqy0mfDx3hbGp
hSi5ICvrAC6yQ0f/jeTzIsbFXglaKQuW5ZhApatGlzmnNaG4bYZ/+vBWeizLRepu
MSkvN5KA6XtZlfZM0zCDozTJcjy43xNnrfHkPdWO8m+iPOnGlkB5YTZTRtF0gu+f
qaltpt7VVOwMfJDmUSJMZzted40dwGpFL9SDmwivy/rKjHHE3cFqLVSz+0ns9o/S
DTOS/XJipj5WpAZHan5YzfhrHkV53le8pzuxsy+GcRS1+8MDWWB2OFYLMYQWy3wt
IyyBAoGBAOs4lf3DEd4AgUWKLDeHbZ98+EubGPfggEMy/0Y0ROaqUqWkFvPpSomq
cfrgdiUgyU/Z2azBwMimSnnvBr+2nD0BxywQ1mV+Ja9Y5R1EbYc3j9gsi9hZDKGS
39fi8TOYrLhP0MBJ7zs5JCnLMu+X7F04txFgXy2LhklBKFjRKoHxAoGBAPs+8kxu
oPNHQWw9e8n6mxe9R0lxXHQoqgn/Wb8PsRERAr/Mdc2NUjV2L2CGn7BpgXly6opp
tpArrYR8qY03Wfredh78uZorCSyjrImiKPGc9tXn0ESpO8nM8h28bjrA3uxwSWYs
4i12Sg+L31bilsiZHM9kABSuHQbZmjrB94GpAoGAeRNpcXOlkMZlxCu5UuPs83la
PWCaW409uFlZuQNSrADkBcsO3YIqEe6gOOitJ7NWrDmQqDIbT6z5DQaSTMBsb6Ko
qPAJy7hBIZ76YDRGxKE+86EKYtSDge+eNPvl+A8QaNb8tt3XvH5PNQwZLebfjaSR
5unaVBFLkA1v/Te9T6ECgYEAu77M9xqQQVsU41qKf2M6tCGn/JSufsrITdI38VM7
gMJSaJrTyPd64CJhwuK2v/AHZYbfBvF6D//jmSZC2Rjsr0+/uuYll7PjFi10yCCa
MfqWZT/l3PkNiX4RyvC8+kCYFNzPrH+LwGctbrKaAWYvQNVRtxRGDy4Q2MaQvqml
V4kCgYEAoyYghkndzN3imdr3q9+wz4KWuG2WUotzTzabMIbMiGlgSrhSosQ5t8cb
oCizg+TETN1CIcprq65cDUgwBimkX0FJY6BKo61jEP7opdQfv60+4afsPVPYfiEn
Eqn7IDessCkTlntk81l4znaQl+PEfyRUXC1IdxGjjGm/qaHaJWg=
-----END RSA PRIVATE KEY-----"""
    
    kalshi = KalshiAPIClient(api_key, private_key)
    
    try:
        # Get markets for SAC
        markets = kalshi.get_markets(event_ticker="HIGHSAC")
        
        if markets:
            print(f"  [SUCCESS] Found {len(markets)} SAC markets")
            
            # Get current prices
            for market in markets[:3]:  # Show first 3
                ticker = market.get('ticker')
                yes_price = market.get('yes_bid', 0)
                
                print(f"\n  Market: {ticker}")
                print(f"    Yes Price: {yes_price}")
                print(f"    Subtitle: {market.get('subtitle', 'N/A')[:50]}")
        else:
            print(f"  [WARNING] No Kalshi markets found for SAC")
            
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    # 3. Test Kalshi Candlestick Data
    print("\n[3/3] Testing Kalshi Historical Prices...")
    print("-"*80)
    
    try:
        # Try to get any SAC market
        if markets:
            ticker = markets[0].get('ticker')
            print(f"  Getting candlesticks for {ticker}...")
            
            candles = kalshi.get_candlesticks(ticker)
            
            if candles:
                print(f"  [SUCCESS] Got {len(candles)} candlesticks")
                
                latest = candles[-1]
                print(f"\n  Latest Candle:")
                print(f"    Time: {latest.get('period_start_timestamp', 'N/A')}")
                print(f"    Close: {latest.get('close', 'N/A')}")
                print(f"    Volume: {latest.get('volume', 'N/A')}")
            else:
                print(f"  [WARNING] No candlestick data available yet")
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    test_live_data()

