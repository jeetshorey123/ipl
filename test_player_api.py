#!/usr/bin/env python3
"""
Test the player stats API endpoint
"""

import sys
sys.path.append('.')

from player_stats import PlayerStatsCalculator
from data_processor import CricketDataProcessor

def test_player_stats_api():
    print("Testing player stats calculation...")
    
    # Initialize
    processor = CricketDataProcessor('data/')
    stats_calc = PlayerStatsCalculator(processor)
    
    # Test with a player we know has data
    test_player = 'MS Dhoni'
    print(f"\nTesting with player: {test_player}")
    
    # Get stats without filters
    stats = stats_calc.get_player_stats(test_player)
    
    if 'error' in stats:
        print(f"ERROR: {stats['error']}")
    else:
        print(f"Success! Player stats calculated:")
        print(f"  - Total matches: {stats['total_matches']}")
        print(f"  - Batting stats: {stats['batting']}")
        print(f"  - Bowling stats: {stats['bowling']}")
    
    # Test with IPL filter
    print(f"\nTesting with IPL filter...")
    ipl_stats = stats_calc.get_player_stats(test_player, {'match_category': 'ipl'})
    
    if 'error' in ipl_stats:
        print(f"IPL ERROR: {ipl_stats['error']}")
    else:
        print(f"IPL Success! Total matches: {ipl_stats['total_matches']}")
    
    # Test with International filter
    print(f"\nTesting with International filter...")
    intl_stats = stats_calc.get_player_stats(test_player, {'match_category': 'international'})
    
    if 'error' in intl_stats:
        print(f"International ERROR: {intl_stats['error']}")
    else:
        print(f"International Success! Total matches: {intl_stats['total_matches']}")

if __name__ == "__main__":
    test_player_stats_api()