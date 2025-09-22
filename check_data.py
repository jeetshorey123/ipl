import json
import glob
import os

# Change to data directory
os.chdir('data')

# Get first 10 files
files = glob.glob('*.json')[:10]

events = set()
match_types = set()

for file in files:
    try:
        with open(file, 'r') as f:
            data = json.load(f)
            info = data.get('info', {})
            
            # Get event name
            event = info.get('event', {})
            event_name = event.get('name', 'Unknown')
            events.add(event_name)
            
            # Get match type
            match_type = info.get('match_type', 'Unknown')
            match_types.add(match_type)
            
    except Exception as e:
        print(f"Error reading {file}: {e}")

print("Sample Events:")
for event in sorted(events):
    print(f"  - {event}")

print("\nMatch Types:")
for match_type in sorted(match_types):
    print(f"  - {match_type}")