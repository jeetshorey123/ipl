from data_processor import CricketDataProcessor
p=CricketDataProcessor('data/')
p.load_all_matches()
print('loaded:',len(p.matches_data))
print('players:',len(p.players_cache),'teams:',len(p.teams_cache),'venues:',len(p.venues_cache))
print('status:',p.get_loading_status())
