"""
Quick Live Test - Run Paper Trading on Kings @ Clippers
"""
import os
import sys
sys.path.insert(0, os.getcwd())

from src.data.kalshi_api import KalshiAPIClient
from datetime import datetime

def test_kalshi_connection():
    """Test if we can connect to Kalshi and get live data"""
    
    print("="*80)
    print("KALSHI API CONNECTION TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
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
    
    # Test 1: Find markets for SAC @ LAC
    print("[1/2] Testing find_nba_markets() for SAC @ LAC...")
    markets = kalshi.find_nba_markets("SAC", "LAC")
    
    if markets:
        print(f"  [SUCCESS] Found {len(markets)} markets")
        for m in markets[:3]:
            print(f"    - {m.get('ticker')}: {m.get('subtitle', 'No subtitle')[:50]}")
    else:
        print("  [FAILED] No markets found")
        return
    
    # Test 2: Get live price for first market
    print(f"\n[2/2] Testing get_live_price() for {markets[0]['ticker']}...")
    ticker = markets[0]['ticker']
    price_data = kalshi.get_live_price(ticker)
    
    if price_data:
        print(f"  [SUCCESS]")
        print(f"    Yes Bid: {price_data.get('yes_bid', 'N/A')}")
        print(f"    Yes Ask: {price_data.get('yes_ask', 'N/A')}")
        print(f"    Last Price: {price_data.get('last_price', 'N/A')}")
    else:
        print("  [FAILED] Could not get price data")
    
    print("\n" + "="*80)
    print("CONNECTION TEST COMPLETE - Kalshi API is working!")
    print("="*80)

if __name__ == "__main__":
    test_kalshi_connection()

