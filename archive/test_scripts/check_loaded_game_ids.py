"""Check what game IDs were loaded after the fix"""
from src.data.loader import load_kalshi_games

print("Loading Kalshi data with fixed game IDs...")
df = load_kalshi_games()

print(f"\nGame ID dtype: {df['game_id'].dtype}")
print(f"\nFirst 10 unique game IDs:")
for gid in df['game_id'].unique()[:10]:
    print(f"  {gid} (type: {type(gid)})")

# Check if any have the '00' prefix
print(f"\nChecking if any game IDs are strings with '00' prefix...")
sample_ids = df['game_id'].head(20).tolist()
for gid in sample_ids:
    if isinstance(gid, str):
        print(f"  Found string ID: {gid}")
        break
else:
    print("  All game IDs are numeric (not strings)")

# Look for playoff games (424...)
playoff_games = df[df['game_id'].astype(str).str.contains('424', na=False)]
if len(playoff_games) > 0:
    print(f"\nFound {playoff_games['game_id'].nunique()} playoff games")
    print(f"Sample playoff game IDs:")
    for gid in playoff_games['game_id'].unique()[:5]:
        print(f"  {gid}")





