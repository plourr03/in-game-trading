"""
Split historical game data into train/validation/test sets for RL training.

Uses time-based split to avoid look-ahead bias:
- Training: 80% (oldest games)
- Validation: 10% (middle games)
- Test: 10% (most recent games)
"""
import os
from glob import glob
from datetime import datetime
import re


def extract_date_from_filename(filename: str) -> datetime:
    """
    Extract date from game filename.
    
    Format: GAMEID_AWAY_at_HOME_YYYY-MM-DD_candles.csv
    Example: 0022500001_PHX_at_LAL_2024-10-22_candles.csv
    """
    try:
        # Extract date using regex
        match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if match:
            date_str = match.group(1)
            return datetime.strptime(date_str, '%Y-%m-%d')
        else:
            # Fallback: use file modification time
            return datetime.fromtimestamp(os.path.getmtime(filename))
    except Exception as e:
        print(f"Warning: Could not parse date from {filename}: {e}")
        return datetime.fromtimestamp(os.path.getmtime(filename))


def split_games(
    data_dir: str = 'kalshi_data/jan_dec_2025_games',
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    output_dir: str = 'ml_models/outputs'
):
    """
    Split games into train/val/test sets based on date.
    
    Args:
        data_dir: Directory containing game CSV files
        train_ratio: Proportion for training (default 0.8)
        val_ratio: Proportion for validation (default 0.1)
        test_ratio: Proportion for test (default 0.1)
        output_dir: Directory to save split files
    """
    print("="*80)
    print("SPLITTING GAME DATA FOR RL TRAINING")
    print("="*80)
    
    # Get all game files
    game_files = glob(os.path.join(data_dir, '*_candles.csv'))
    print(f"\nFound {len(game_files)} games in {data_dir}")
    
    # Sort by date
    print("\nSorting games by date...")
    games_with_dates = [(f, extract_date_from_filename(f)) for f in game_files]
    games_with_dates.sort(key=lambda x: x[1])
    
    # Print date range
    oldest_date = games_with_dates[0][1]
    newest_date = games_with_dates[-1][1]
    print(f"Date range: {oldest_date.strftime('%Y-%m-%d')} to {newest_date.strftime('%Y-%m-%d')}")
    
    # Calculate split indices
    total_games = len(games_with_dates)
    train_end = int(total_games * train_ratio)
    val_end = int(total_games * (train_ratio + val_ratio))
    
    # Split games
    train_games = [f for f, d in games_with_dates[:train_end]]
    val_games = [f for f, d in games_with_dates[train_end:val_end]]
    test_games = [f for f, d in games_with_dates[val_end:]]
    
    print(f"\nSplit summary:")
    print(f"  Training:   {len(train_games)} games ({len(train_games)/total_games*100:.1f}%)")
    print(f"              {games_with_dates[0][1].strftime('%Y-%m-%d')} to {games_with_dates[train_end-1][1].strftime('%Y-%m-%d')}")
    print(f"  Validation: {len(val_games)} games ({len(val_games)/total_games*100:.1f}%)")
    if val_games:
        print(f"              {games_with_dates[train_end][1].strftime('%Y-%m-%d')} to {games_with_dates[val_end-1][1].strftime('%Y-%m-%d')}")
    print(f"  Test:       {len(test_games)} games ({len(test_games)/total_games*100:.1f}%)")
    if test_games:
        print(f"              {games_with_dates[val_end][1].strftime('%Y-%m-%d')} to {games_with_dates[-1][1].strftime('%Y-%m-%d')}")
    
    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)
    
    # Save splits to files
    train_file = os.path.join(output_dir, 'rl_train_games.txt')
    val_file = os.path.join(output_dir, 'rl_val_games.txt')
    test_file = os.path.join(output_dir, 'rl_test_games.txt')
    
    with open(train_file, 'w') as f:
        f.write('\n'.join(train_games))
    print(f"\n[OK] Saved training games to {train_file}")
    
    with open(val_file, 'w') as f:
        f.write('\n'.join(val_games))
    print(f"[OK] Saved validation games to {val_file}")
    
    with open(test_file, 'w') as f:
        f.write('\n'.join(test_games))
    print(f"[OK] Saved test games to {test_file}")
    
    print("\n" + "="*80)
    print("DATA SPLIT COMPLETE")
    print("="*80)
    
    return {
        'train': train_games,
        'val': val_games,
        'test': test_games,
        'train_file': train_file,
        'val_file': val_file,
        'test_file': test_file
    }


def load_split(split_name: str, output_dir: str = 'ml_models/outputs') -> list:
    """
    Load a previously saved data split.
    
    Args:
        split_name: One of 'train', 'val', or 'test'
        output_dir: Directory where split files are saved
        
    Returns:
        List of game file paths
    """
    split_file = os.path.join(output_dir, f'rl_{split_name}_games.txt')
    
    if not os.path.exists(split_file):
        raise FileNotFoundError(f"Split file not found: {split_file}")
    
    with open(split_file, 'r') as f:
        games = [line.strip() for line in f if line.strip()]
    
    return games


if __name__ == "__main__":
    # Run the split
    result = split_games()
    
    print(f"\nTo load splits in your code:")
    print(f"  from ml_models.rl_data_split import load_split")
    print(f"  train_games = load_split('train')")
    print(f"  val_games = load_split('val')")
    print(f"  test_games = load_split('test')")

