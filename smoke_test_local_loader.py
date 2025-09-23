import json
import time
from data_processor import CricketDataProcessor

if __name__ == "__main__":
    p = CricketDataProcessor('data/')
    p.start_background_local_load(max_workers=16, max_files=None)
    for i in range(15):
        s = p.get_loading_status()
        print(f"tick {i}", json.dumps(s))
        if not s.get('loading'):
            break
        time.sleep(1)
    print('final counts', len(p.matches_data), len(p.players_cache), len(p.teams_cache), len(p.venues_cache))
