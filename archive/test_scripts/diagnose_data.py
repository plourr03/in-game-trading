"""
Quick diagnostic to see what's in the data
"""
import pandas as pd
import numpy as np

from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices

print("Loading data...")
kalshi_df = load_kalshi_games()
kalshi_df = fill_prices(kalshi_df)

# Pick one game
sample_game = kalshi_df['game_id'].iloc[1000]
game_data = kalshi_df[kalshi_df['game_id'] == sample_game].copy()

print(f"\nSample Game: {sample_game}")
print(f"Number of minutes: {len(game_data)}")
print(f"\nFirst 10 rows:")
print(game_data[['datetime', 'open', 'high', 'low', 'close', 'volume']].head(10))

# Calculate price changes
game_data['price_change'] = game_data['close'].diff()
game_data['price_change_pct'] = (game_data['price_change'] / game_data['close'].shift(1)).abs() * 100

print(f"\nPrice statistics:")
print(f"Min price: {game_data['close'].min():.2f}")
print(f"Max price: {game_data['close'].max():.2f}")
print(f"Avg price: {game_data['close'].mean():.2f}")
print(f"Price range: {game_data['close'].max() - game_data['close'].min():.2f}")

print(f"\nPrice change statistics:")
print(f"Max abs change: {game_data['price_change'].abs().max():.2f} cents")
print(f"Max pct change: {game_data['price_change_pct'].max():.2f}%")
print(f"Moves > 5%: {(game_data['price_change_pct'] > 5).sum()}")
print(f"Moves > 10%: {(game_data['price_change_pct'] > 10).sum()}")

# Show some big moves
big_moves = game_data[game_data['price_change_pct'] > 5].copy()
if len(big_moves) > 0:
    print(f"\nSample of big moves (>5%):")
    print(big_moves[['datetime', 'close', 'price_change', 'price_change_pct']].head(5))
else:
    print("\n⚠️ No moves > 5% found in this game!")

# Check price ranges
print(f"\nMinutes in different price ranges:")
print(f"1-20¢:  {((game_data['close'] >= 1) & (game_data['close'] <= 20)).sum()} minutes")
print(f"20-40¢: {((game_data['close'] >= 20) & (game_data['close'] <= 40)).sum()} minutes")
print(f"40-60¢: {((game_data['close'] >= 40) & (game_data['close'] <= 60)).sum()} minutes")
print(f"60-80¢: {((game_data['close'] >= 60) & (game_data['close'] <= 80)).sum()} minutes")
print(f"80-99¢: {((game_data['close'] >= 80) & (game_data['close'] <= 99)).sum()} minutes")

