import time
import json
from data_processor import CricketDataProcessor

if __name__ == "__main__":
    dp = CricketDataProcessor('data/')
    # Start background load with a strict cap of 3613 unique matches
    dp.start_background_local_load(max_workers=24, max_unique_matches=3613)
    print("Started background local load with cap=3613 unique matches...")
    for i in range(20):
        time.sleep(1)
        status = dp.get_loading_status()
        print(f"t+{i+1}s status=", json.dumps(status))
        if not status.get('loading'):
            break
    print("Final:", {
        'matches_loaded': len(dp.matches_data),
        'players': len(dp.players_cache),
        'teams': len(dp.teams_cache),
        'venues': len(dp.venues_cache)
    })
