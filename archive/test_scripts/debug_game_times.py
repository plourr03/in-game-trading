"""
Debug script to check game start times from NBA API
"""
from nba_api.live.nba.endpoints import scoreboard
from datetime import datetime

board = scoreboard.ScoreBoard()
games_data = board.get_dict()

print("="*80)
print("GAME START TIMES DEBUG")
print("="*80)

for g in games_data['scoreboard']['games']:
    game_id = g['gameId']
    away = g['awayTeam']['teamTricode']
    home = g['homeTeam']['teamTricode']
    status = g.get('gameStatus', 1)
    start_time = g.get('gameTimeUTC', None)
    
    print(f"\n{away} @ {home} (Game {game_id})")
    print(f"  Status: {status} (1=not started, 2=in progress, 3=ended)")
    print(f"  Start Time UTC: {start_time}")
    
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            now_dt = datetime.now(start_dt.tzinfo)
            
            time_diff = (now_dt - start_dt).total_seconds() / 3600
            print(f"  Time since start: {time_diff:.1f} hours")
            
            if time_diff > 2:
                print(f"  -> SHOULD BE MARKED AS FINISHED")
        except Exception as e:
            print(f"  Error parsing: {e}")

