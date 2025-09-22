import os
import sys
import json
from dotenv import load_dotenv

# Ensure repository root is on sys.path when running this script directly
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from data_processor import CricketDataProcessor
from player_stats import PlayerStatsCalculator
from app import app

"""
Quick script to check player analysis for a single player using only N matches from
already loaded Supabase Storage data.
Usage (PowerShell):
  . .\.venv\Scripts\Activate.ps1
  $env:SUPABASE_URL='https://xnfzscwsvxzotqrdpnqf.supabase.co'
  # Ensure SUPABASE_SERVICE_ROLE_KEY is present in environment
  python .\scripts\check_player_stats.py "Virat Kohli" 5
"""

load_dotenv()

def main():
    import sys
    if len(sys.argv) < 3:
        print("Usage: python scripts/check_player_stats.py <player_name> <max_matches>")
        sys.exit(1)
    player_name = sys.argv[1]
    try:
        max_matches = int(float(sys.argv[2]))
    except Exception:
        max_matches = 5

    # Use Flask test client to hit reload with limit and then query player stats
    client = app.test_client()
    client.post('/api/data/reload', json={'max_files': max_matches})
    import time
    # wait until at least 1 match is loaded or short timeout
    for _ in range(40):
        h = client.get('/api/data/health').get_json() or {}
        if (h.get('matches_loaded') or 0) >= 1:
            break
        time.sleep(0.25)
    # Now fetch stats (limited to first max_matches matches for the player)
    resp = client.get(f"/api/player-stats/{player_name}?max_matches={max_matches}")
    stats = resp.get_json()
    print(json.dumps(stats, indent=2))

if __name__ == '__main__':
    main()
