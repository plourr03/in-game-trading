"""
Test script to diagnose PBP data synchronization issue
Uses a recent completed game to verify score changes over time
"""
import requests
import pandas as pd
from datetime import datetime

def fetch_pbp(game_id):
    """Fetch play-by-play data"""
    url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def analyze_pbp_timeline(game_id):
    """Analyze how scores change over time in PBP data"""
    print("="*80)
    print(f"ANALYZING PBP DATA FOR GAME: {game_id}")
    print("="*80)
    
    pbp = fetch_pbp(game_id)
    
    if not pbp:
        print("[ERROR] Could not fetch PBP data")
        return
    
    actions = pbp.get('game', {}).get('actions', [])
    
    if not actions:
        print("[ERROR] No actions found")
        return
    
    print(f"\nTotal actions: {len(actions)}")
    
    # Sample actions at different points
    print("\n" + "="*80)
    print("SCORE PROGRESSION (Every 50 actions)")
    print("="*80)
    
    score_changes = []
    
    for i in range(0, len(actions), 50):
        action = actions[i]
        score_home = action.get('scoreHome', 'N/A')
        score_away = action.get('scoreAway', 'N/A')
        period = action.get('period', 'N/A')
        clock = action.get('clock', 'N/A')
        action_num = action.get('actionNumber', i)
        
        print(f"Action {action_num:4d}: Q{period} {clock:15s} | Score: {score_away}-{score_home}")
        
        if score_home != 'N/A' and score_away != 'N/A':
            score_changes.append({
                'action_num': action_num,
                'period': period,
                'clock': clock,
                'score_home': int(score_home),
                'score_away': int(score_away)
            })
    
    # Show last action
    last = actions[-1]
    print(f"Action {last.get('actionNumber'):4d}: Q{last.get('period')} {last.get('clock'):15s} | Score: {last.get('scoreAway')}-{last.get('scoreHome')}")
    
    # Analyze score changes
    print("\n" + "="*80)
    print("SCORE CHANGE ANALYSIS")
    print("="*80)
    
    if len(score_changes) > 1:
        print(f"First score: {score_changes[0]['score_away']}-{score_changes[0]['score_home']}")
        print(f"Last score:  {score_changes[-1]['score_away']}-{score_changes[-1]['score_home']}")
        print(f"\nScore changed: {'YES' if score_changes[0]['score_home'] != score_changes[-1]['score_home'] else 'NO'}")
        print(f"Total unique scores (home): {len(set(s['score_home'] for s in score_changes))}")
    
    # Check for the bug: all actions showing same score
    print("\n" + "="*80)
    print("BUG CHECK: Do all actions show the same score?")
    print("="*80)
    
    all_scores_home = []
    all_scores_away = []
    
    for action in actions:
        if 'scoreHome' in action and action['scoreHome']:
            try:
                all_scores_home.append(int(action['scoreHome']))
            except:
                pass
        if 'scoreAway' in action and action['scoreAway']:
            try:
                all_scores_away.append(int(action['scoreAway']))
            except:
                pass
    
    if all_scores_home:
        unique_home = len(set(all_scores_home))
        print(f"Unique home scores: {unique_home}")
        print(f"Range: {min(all_scores_home)} to {max(all_scores_home)}")
        
        if unique_home == 1:
            print("[BUG FOUND] All actions show the same home score!")
        else:
            print("[OK] Scores change throughout the game")
    
    return pbp, actions

# Test with recent games
print("\nTesting with Lakers vs Kings game from 12/28...")
pbp_data, actions = analyze_pbp_timeline('0022500446')

print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS")
print("="*80)

if pbp_data and actions:
    # Check if the issue is with how we're reading the data
    print("\nChecking first 5 actions with scores:")
    count = 0
    for action in actions:
        if 'scoreHome' in action and action['scoreHome'] and count < 5:
            print(f"  Period {action['period']}, Clock {action.get('clock')}: {action['scoreAway']}-{action['scoreHome']}")
            count += 1
    
    print("\nChecking last 5 actions with scores:")
    count = 0
    for action in reversed(actions):
        if 'scoreHome' in action and action['scoreHome'] and count < 5:
            print(f"  Period {action['period']}, Clock {action.get('clock')}: {action['scoreAway']}-{action['scoreHome']}")
            count += 1



