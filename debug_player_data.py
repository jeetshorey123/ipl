#!/usr/bin/env python3
"""
Test script to debug player data extraction
"""

import sys
import os
sys.path.append('.')

from data_processor import CricketDataProcessor

def test_player_data():
    print("Testing player data extraction...")
    
    # Initialize data processor
    processor = CricketDataProcessor('data/')
    
    # Get all players
    all_players = processor.get_all_players()
    print(f"Found {len(all_players)} players total")
    
    if not all_players:
        print("ERROR: No players found!")
        return
    
    # Test with first few players
    test_players = all_players[:5]
    print(f"Testing with players: {test_players}")
    
    for player in test_players:
        print(f"\n--- Testing player: {player} ---")
        
        # Get player match data
        player_matches = processor.get_player_match_data(player)
        print(f"Found {len(player_matches)} matches for {player}")
        
        if player_matches:
            match = player_matches[0]
            print(f"First match info:")
            print(f"  - Teams: {match['match_info'].get('teams', [])}")
            print(f"  - Player team: {match['player_team']}")
            print(f"  - Batting data entries: {len(match['batting_data'])}")
            print(f"  - Bowling data entries: {len(match['bowling_data'])}")
            
            if match['batting_data']:
                batting = match['batting_data'][0]
                print(f"  - Batting stats: runs={batting['runs']}, balls={batting['balls']}")
            
            if match['bowling_data']:
                bowling = match['bowling_data'][0]
                print(f"  - Bowling stats: runs_conceded={bowling['runs_conceded']}, balls={bowling['balls']}")
        else:
            print(f"  No match data found for {player}")

def test_specific_match():
    print("\n=== Testing specific match structure ===")
    
    processor = CricketDataProcessor('data/')
    
    if processor.matches_data:
        match = processor.matches_data[0]
        info = match.get('info', {})
        
        print(f"Match: {info.get('teams', [])} at {info.get('venue', 'Unknown')}")
        print(f"Players in match:")
        
        players = info.get('players', {})
        for team, team_players in players.items():
            print(f"  {team}: {team_players[:3]}... ({len(team_players)} total)")
        
        # Check innings structure
        innings = match.get('innings', [])
        print(f"\nInnings found: {len(innings)}")
        
        for i, inning in enumerate(innings):
            team = inning.get('team', 'Unknown')
            overs = inning.get('overs', [])
            print(f"  Inning {i+1}: {team} - {len(overs)} overs")
            
            if overs:
                # Check first over
                first_over = overs[0]
                deliveries = first_over.get('deliveries', [])
                print(f"    First over: {len(deliveries)} deliveries")
                
                if deliveries:
                    first_delivery = deliveries[0]
                    print(f"    First delivery: batter={first_delivery.get('batter')}, bowler={first_delivery.get('bowler')}")

if __name__ == "__main__":
    test_specific_match()
    test_player_data()