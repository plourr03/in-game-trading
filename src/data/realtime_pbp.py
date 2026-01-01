"""
Real-time Play-by-Play Data Fetcher

Uses nba_api to fetch live game data for ML model
"""
import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import time


class RealTimePBPFetcher:
    """Fetch real-time play-by-play data from NBA API"""
    
    def __init__(self):
        self.base_url = "https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"
        self.cache = {}  # Cache responses to avoid excessive requests
        self.last_request_time = {}
        self.min_request_interval = 5  # seconds between requests for same game
    
    def fetch_game_pbp(self, game_id: str) -> Optional[Dict]:
        """
        Fetch play-by-play data for a game
        
        Args:
            game_id: 10-digit game ID (e.g., '0022000180')
            
        Returns:
            Dictionary with game play-by-play data or None if error
        """
        # Ensure game_id is 10 digits
        if len(str(game_id)) == 8:
            game_id = f"00{game_id}"
        
        # Check cache and rate limiting
        now = time.time()
        if game_id in self.last_request_time:
            elapsed = now - self.last_request_time[game_id]
            if elapsed < self.min_request_interval:
                # Return cached data if available
                return self.cache.get(game_id)
        
        # Fetch data
        url = self.base_url.format(game_id=game_id)
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Cache response
            self.cache[game_id] = data
            self.last_request_time[game_id] = now
            
            return data
        
        except requests.exceptions.RequestException as e:
            # Don't print 403 errors (game hasn't started yet)
            if '403' not in str(e):
                print(f"Error fetching PBP data for game {game_id}: {e}")
            return None
    
    def extract_current_scores(self, pbp_data: Dict) -> Dict[str, int]:
        """
        Extract current scores from play-by-play data
        
        Args:
            pbp_data: Raw PBP data from API
            
        Returns:
            Dictionary with 'home' and 'away' scores
        """
        if not pbp_data or 'game' not in pbp_data:
            return {'home': 0, 'away': 0}
        
        actions = pbp_data['game'].get('actions', [])
        
        if not actions:
            return {'home': 0, 'away': 0}
        
        # Get most recent action with scores
        for action in reversed(actions):
            if 'scoreHome' in action and 'scoreAway' in action:
                try:
                    return {
                        'home': int(action['scoreHome']),
                        'away': int(action['scoreAway'])
                    }
                except (ValueError, TypeError):
                    continue
        
        return {'home': 0, 'away': 0}
    
    def get_period_and_clock(self, pbp_data: Dict) -> Dict:
        """
        Extract current period and clock time
        
        Args:
            pbp_data: Raw PBP data from API
            
        Returns:
            Dictionary with 'period' and 'clock' (seconds remaining in period)
        """
        if not pbp_data or 'game' not in pbp_data:
            return {'period': 1, 'clock': 720}
        
        actions = pbp_data['game'].get('actions', [])
        
        if not actions:
            return {'period': 1, 'clock': 720}
        
        # Get most recent action
        latest_action = actions[-1]
        
        period = latest_action.get('period', 1)
        clock_str = latest_action.get('clock', 'PT12M00.00S')
        
        # Parse clock string (format: PT03M59.00S)
        try:
            # Extract minutes and seconds
            clock_str = clock_str.replace('PT', '').replace('S', '')
            if 'M' in clock_str:
                parts = clock_str.split('M')
                minutes = int(parts[0])
                seconds = float(parts[1]) if len(parts) > 1 else 0
            else:
                minutes = 0
                seconds = float(clock_str)
            
            clock_seconds = minutes * 60 + seconds
        except:
            clock_seconds = 720  # Default to 12 minutes
        
        return {
            'period': period,
            'clock': clock_seconds
        }
    
    def convert_to_dataframe(self, pbp_data: Dict) -> pd.DataFrame:
        """
        Convert PBP data to DataFrame format
        
        Args:
            pbp_data: Raw PBP data from API
            
        Returns:
            DataFrame with play-by-play events
        """
        if not pbp_data or 'game' not in pbp_data:
            return pd.DataFrame()
        
        actions = pbp_data['game'].get('actions', [])
        
        if not actions:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(actions)
        
        # Clean up
        df['game_id'] = pbp_data['game']['gameId']
        
        # Convert scores to numeric
        if 'scoreHome' in df.columns:
            df['score_home'] = pd.to_numeric(df['scoreHome'], errors='coerce').fillna(0).astype(int)
        else:
            df['score_home'] = 0
            
        if 'scoreAway' in df.columns:
            df['score_away'] = pd.to_numeric(df['scoreAway'], errors='coerce').fillna(0).astype(int)
        else:
            df['score_away'] = 0
        
        return df
    
    def get_game_state(self, game_id: str) -> Dict:
        """
        Get complete current game state
        
        Args:
            game_id: 10-digit game ID
            
        Returns:
            Dictionary with scores, period, clock, etc.
        """
        pbp_data = self.fetch_game_pbp(game_id)
        
        if not pbp_data:
            return {
                'game_id': game_id,
                'home_score': 0,
                'away_score': 0,
                'period': 1,
                'clock': 720,
                'status': 'error'
            }
        
        scores = self.extract_current_scores(pbp_data)
        time_info = self.get_period_and_clock(pbp_data)
        
        return {
            'game_id': game_id,
            'home_score': scores['home'],
            'away_score': scores['away'],
            'period': time_info['period'],
            'clock': time_info['clock'],
            'status': 'ok'
        }


def test_fetcher():
    """Test the real-time PBP fetcher"""
    print("Testing Real-Time PBP Fetcher")
    print("="*60)
    
    fetcher = RealTimePBPFetcher()
    
    # Test with a known valid game ID
    test_game_id = "0022000180"
    
    print(f"\nFetching data for game {test_game_id}...")
    pbp_data = fetcher.fetch_game_pbp(test_game_id)
    
    if pbp_data:
        print("[OK] Data fetched successfully!")
        
        # Extract scores
        scores = fetcher.extract_current_scores(pbp_data)
        print(f"  Home: {scores['home']}")
        print(f"  Away: {scores['away']}")
        
        # Extract time info
        time_info = fetcher.get_period_and_clock(pbp_data)
        print(f"  Period: {time_info['period']}")
        print(f"  Clock: {time_info['clock']:.0f} seconds")
        
        # Get complete game state
        game_state = fetcher.get_game_state(test_game_id)
        print(f"\nGame State:")
        for key, val in game_state.items():
            print(f"  {key}: {val}")
        
        # Convert to DataFrame
        df = fetcher.convert_to_dataframe(pbp_data)
        print(f"\nDataFrame: {len(df)} actions")
        if len(df) > 0:
            print(f"  Columns: {df.columns.tolist()[:10]}...")
            print(f"  Score range: {df['score_home'].min()}-{df['score_home'].max()} (home)")
    else:
        print("[ERROR] Failed to fetch data")
    
    print("\n" + "="*60)
    print("[OK] Test complete!")


if __name__ == "__main__":
    test_fetcher()





