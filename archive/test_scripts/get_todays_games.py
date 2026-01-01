from nba_api.live.nba.endpoints import scoreboard

games = scoreboard.ScoreBoard().get_dict()
print('Games today:')
for g in games['scoreboard']['games']:
    away = g['awayTeam']['teamTricode']
    home = g['homeTeam']['teamTricode']
    game_id = g['gameId']
    print(f"  {away} @ {home} - Game ID: {game_id}")



