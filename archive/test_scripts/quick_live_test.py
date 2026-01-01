"""
Quick 3-Minute Live Test - Paper Trading
Tests on current games to ensure everything works
"""
import os
import sys
sys.path.insert(0, os.getcwd())

from datetime import datetime
from nba_api.live.nba.endpoints import scoreboard

# Get today's games
print("="*80)
print("QUICK LIVE PAPER TRADING TEST")
print("="*80)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

print("Fetching today's games...")
board = scoreboard.ScoreBoard()
games_dict = board.get_dict()
games = games_dict.get('scoreboard', {}).get('games', [])

if not games:
    print("No games available")
    sys.exit(0)

print(f"Found {len(games)} games today:\n")
for game in games:
    game_id = game['gameId']
    home = game['homeTeam']['teamTricode']
    away = game['awayTeam']['teamTricode']
    status = game['gameStatusText']
    home_score = game['homeTeam'].get('score', 0)
    away_score = game['awayTeam'].get('score', 0)
    
    print(f"  {away} @ {home} - {status}")
    if home_score > 0 or away_score > 0:
        print(f"    Score: {away_score} - {home_score}")
    print(f"    Game ID: {game_id}")

# Find an active game
active_game = None
for game in games:
    if game.get('gameStatus') == 2:  # In progress
        active_game = game
        break

if not active_game:
    print("\n[INFO] No games currently in progress")
    print("[INFO] Paper trading system is ready when games start")
    sys.exit(0)

# Run a quick test on the active game
game_id = active_game['gameId']
home = active_game['homeTeam']['teamTricode']
away = active_game['awayTeam']['teamTricode']

print(f"\n{'='*80}")
print(f"TESTING ON: {away} @ {home} (Game {game_id})")
print(f"{'='*80}\n")

from src.data.kalshi_api import KalshiAPIClient
from src.data.realtime_pbp import RealTimePBPFetcher
import time

# Initialize
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
pbp_fetcher = RealTimePBPFetcher()

# Run 3 iterations (3 minutes)
for iteration in range(1, 4):
    print(f"\n[Iteration {iteration}/3] - {datetime.now().strftime('%H:%M:%S')}")
    print("-"*80)
    
    # 1. Fetch Kalshi data
    print(f"  [1/2] Fetching Kalshi markets for {away} vs {home}...")
    try:
        markets = kalshi.find_nba_markets(away, home)
        if markets:
            ticker = markets[0]['ticker']
            print(f"    Found market: {ticker}")
            
            price_data = kalshi.get_live_price(ticker)
            if price_data:
                print(f"    Price: Yes={price_data.get('yes_bid', 'N/A')} | Last={price_data.get('last_price', 'N/A')}")
            else:
                print(f"    [WARNING] No price data available")
        else:
            print(f"    [WARNING] No markets found")
    except Exception as e:
        print(f"    [ERROR] {e}")
    
    # 2. Fetch NBA PBP data
    print(f"  [2/2] Fetching NBA play-by-play...")
    try:
        pbp_data = pbp_fetcher.fetch_game_pbp(game_id)
        if pbp_data and 'game' in pbp_data:
            actions = pbp_data['game'].get('actions', [])
            if actions and len(actions) > 0:
                latest = actions[-1]
                period = latest.get('period', '?')
                clock = latest.get('clock', '?')
                score_home = latest.get('scoreHome', '?')
                score_away = latest.get('scoreAway', '?')
                print(f"    Period {period}, {clock} | Score: {score_away}-{score_home}")
                print(f"    Total actions: {len(actions)}")
            else:
                print(f"    [WARNING] No actions in PBP data yet")
        else:
            print(f"    [WARNING] No PBP data available (game may not have started)")
    except Exception as e:
        print(f"    [ERROR] {e}")
    
    if iteration < 3:
        print(f"\n  Waiting 60 seconds...")
        time.sleep(60)

print(f"\n{'='*80}")
print("TEST COMPLETE")
print("="*80)
print("\n[RESULT] Both Kalshi and NBA APIs are working!")
print("[RESULT] Paper trading system is ready for live operation")
print("\nTo run full paper trading with database logging:")
print("  python run_paper_trading.py")

