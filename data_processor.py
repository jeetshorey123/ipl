import json
import os
import glob
from collections import defaultdict
import pandas as pd
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from supabase_client import supabase_client
except Exception:
    supabase_client = None

logger = logging.getLogger(__name__)

class CricketDataProcessor:
    """Core data processor for cricket match data"""
    
    def __init__(self, data_directory):
        self.data_directory = data_directory
        self.matches_data = []
        self.players_cache = set()
        self.teams_cache = set()
        self.venues_cache = set()
        self._lock = threading.Lock()
        # Background loading state
        self._loading = False
        self._total_files = 0
        self._files_loaded = 0
        self._ingested_keys = set()
        # Supabase-only data source per requirements
        if not (supabase_client and getattr(supabase_client, 'is_connected', False)):
            logger.error("Supabase not configured or not connected. No local data fallback per requirements.")
        
        # Initialize calculators
        from player_stats import PlayerStatsCalculator
        from player_comparison import PlayerComparisonCalculator
        
        self.player_stats_calculator = PlayerStatsCalculator(self)
        self.player_comparison_calculator = PlayerComparisonCalculator(self)

    def _to_int(self, value, default: int = 0) -> int:
        """Safely convert assorted numeric-like values to int.
        Handles None, empty strings, numeric strings (including floats like '2.0'), and bools.
        """
        try:
            if value is None:
                return default
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                s = value.strip()
                if s == '':
                    return default
                # handle float-like strings as well
                return int(float(s))
            return default
        except Exception:
            return default
    
    def load_all_matches(self, limit_matches=200):
        """Load match data from JSON files with optional limit for development"""
        logger.info(f"Loading match data (limit: {limit_matches} matches for development)...")
        json_files = glob.glob(os.path.join(self.data_directory, "*.json"))
        
        loaded_count = 0
        for file_path in json_files:
            if loaded_count >= limit_matches:
                break
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    match_data = json.load(f)
                    self.matches_data.append(match_data)
                    loaded_count += 1
                    
                    # Cache unique values
                    if 'info' in match_data:
                        info = match_data['info']
                        
                        # Cache teams
                        if 'teams' in info:
                            self.teams_cache.update(info['teams'])
                        
                        # Cache venue
                        if 'venue' in info:
                            self.venues_cache.add(info['venue'])
                        
                        # Cache players
                        if 'players' in info:
                            for team, players in info['players'].items():
                                self.players_cache.update(players)
                                
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                continue
        
        logger.info(f"Loaded {len(self.matches_data)} matches (development mode - limited dataset)")
        logger.info(f"Found {len(self.players_cache)} unique players")
        logger.info(f"Found {len(self.teams_cache)} unique teams")
        logger.info(f"Found {len(self.venues_cache)} unique venues")

    def _extract_match_from_row(self, row: Dict[str, Any]):
        """Try to extract a match JSON object from a Supabase row with unknown schema.
        We look for a dict value containing 'info' and 'innings'.
        """
        # Handle JSON strings directly
        if isinstance(row, str):
            try:
                parsed = json.loads(row)
                return self._extract_match_from_row(parsed)
            except Exception:
                return None
        if isinstance(row, list) and row:
            # Some drivers can return list of JSONs
            for item in row:
                m = self._extract_match_from_row(item)
                if m:
                    return m
            return None
        if isinstance(row, dict):
            # Direct match JSON
            if 'info' in row and 'innings' in row:
                return row
            # Find nested JSON column
            for v in row.values():
                if isinstance(v, dict) and 'info' in v and 'innings' in v:
                    return v
                if isinstance(v, str):
                    try:
                        parsed = json.loads(v)
                        if isinstance(parsed, dict) and 'info' in parsed and 'innings' in parsed:
                            return parsed
                    except Exception:
                        pass
        return None

    def _ingest_match(self, match_data: Dict[str, Any]):
        """Thread-safe ingestion of a single parsed match object into caches."""
        if not match_data:
            return
        with self._lock:
            self.matches_data.append(match_data)
            info = match_data.get('info', {})
            if 'teams' in info:
                self.teams_cache.update(info['teams'])
            if 'venue' in info:
                self.venues_cache.add(info['venue'])
            if 'players' in info:
                for team, players in info['players'].items():
                    self.players_cache.update(players)
            self._files_loaded += 1

    def start_background_supabase_load(self, max_workers: int = 16, max_files: int | None = None):
        """Start loading ALL matches from Supabase in the background with concurrency.
        This avoids blocking startup and loads quickly. No artificial limits.
        """
        if not (supabase_client and getattr(supabase_client, 'is_connected', False)):
            logger.error("Supabase not connected; cannot start background load.")
            return
        if self._loading:
            logger.info("Background load already in progress")
            return

        self._loading = True
        self._files_loaded = 0
        self._ingested_keys = set()

        def worker():
            try:
                bucket = getattr(supabase_client, 'bucket_name', None)
                storage = supabase_client.supabase.storage.from_(bucket) if bucket else None
                # List all json keys across bucket (from root if no prefix)
                keys = supabase_client.list_json_files(bucket=bucket, prefix=supabase_client.bucket_prefix or '')
                if max_files is not None and isinstance(max_files, int) and max_files > 0:
                    keys = keys[:max_files]
                self._total_files = len(keys)
                if not keys:
                    # Fallback to table if no storage files
                    logger.info("No JSON files in storage; trying table fallback...")
                    rows = supabase_client.get_all_matches(limit=None)
                    for row in rows:
                        match_data = self._extract_match_from_row(row)
                        if match_data:
                            self._ingest_match(match_data)
                    return

                logger.info(f"Background loading {len(keys)} JSON files from Supabase Storage with {max_workers} workers... (limit: {max_files if max_files else 'all'})")
                # Download + parse concurrently
                def download_parse(key: str):
                    backoff = 0.2
                    attempts = 5
                    for attempt in range(attempts):
                        try:
                            data_bytes = storage.download(key)
                            text = data_bytes.decode('utf-8') if isinstance(data_bytes, (bytes, bytearray)) else str(data_bytes)
                            obj = json.loads(text)
                            # Accept either full match or nested structures
                            match_data = self._extract_match_from_row(obj)
                            if match_data:
                                self._ingest_match(match_data)
                                with self._lock:
                                    self._ingested_keys.add(key)
                            return
                        except Exception as de:
                            if attempt < attempts - 1:
                                time.sleep(backoff)
                                backoff *= 2
                            else:
                                logger.warning(f"Failed to download/parse '{key}' after {attempts} attempts: {de}")

                # Use a reasonable pool size
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(download_parse, k) for k in keys]
                    for _ in as_completed(futures):
                        pass
                # If any missing, try a second, smaller pass
                missing = []
                with self._lock:
                    if self._ingested_keys and self._total_files:
                        missing = [k for k in keys if k not in self._ingested_keys]
                if missing:
                    logger.info(f"Second pass for {len(missing)} missing files...")
                    with ThreadPoolExecutor(max_workers=max(2, min(6, len(missing)))) as executor:
                        futures = [executor.submit(download_parse, k) for k in missing]
                        for _ in as_completed(futures):
                            pass
                logger.info(f"Background load complete: {self._files_loaded}/{self._total_files} files ingested")
            except Exception as e:
                logger.error(f"Background load failed: {e}")
            finally:
                self._loading = False

        threading.Thread(target=worker, name="SupabaseBackgroundLoader", daemon=True).start()

    def reload_from_supabase(self, max_files: int | None = None):
        """Clear in-memory caches and re-start background load from Supabase.
        If max_files is provided, limit the storage load to first N JSON files."""
        try:
            with self._lock:
                self.matches_data = []
                self.players_cache = set()
                self.teams_cache = set()
                self.venues_cache = set()
                self._files_loaded = 0
                self._total_files = 0
            self.start_background_supabase_load(max_files=max_files)
            return {
                'matches_loaded': len(self.matches_data),
                'players_count': len(self.players_cache),
                'teams_count': len(self.teams_cache),
                'venues_count': len(self.venues_cache),
                'loading': self._loading
            }
        except Exception as e:
            logger.error(f"Failed to reload from Supabase: {e}")
            return {'error': str(e)}

    def get_loading_status(self) -> Dict[str, Any]:
        """Return background loading progress."""
        try:
            return {
                'loading': self._loading,
                'files_loaded': self._files_loaded,
                'total_files': self._total_files,
                'matches_loaded': len(self.matches_data),
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_all_players(self):
        """Get list of all players"""
        return list(self.players_cache)
    
    def get_all_teams(self):
        """Get list of all teams"""
        return list(self.teams_cache)
    
    def get_all_venues(self):
        """Get list of all venues"""
        return list(self.venues_cache)
    
    def get_all_countries(self):
        """Get list of all countries/cities"""
        countries = set()
        for match in self.matches_data:
            info = match.get('info', {})
            if 'city' in info:
                countries.add(info['city'])
        return list(countries)
    
    def get_match_categories(self):
        """Get available match categories (IPL vs International)"""
        categories = set()
        ipl_found = False
        international_found = False
        
        for match in self.matches_data:
            info = match.get('info', {})
            event_name = info.get('event', {}).get('name', '').lower()
            
            if 'ipl' in event_name or 'indian premier league' in event_name:
                ipl_found = True
            else:
                international_found = True
        
        result = []
        if ipl_found:
            result.append('ipl')
        if international_found:
            result.append('international')
            
        return result
    
    def get_available_years(self):
        """Get list of available years from matches"""
        years = set()
        for match in self.matches_data:
            info = match.get('info', {})
            match_dates = info.get('dates', [])
            if match_dates:
                year = match_dates[0][:4]  # Extract year from date like "2024-02-02"
                years.add(year)
        return sorted(list(years))
    
    def filter_matches(self, filters=None):
        """Filter matches based on criteria"""
        if not filters:
            return self.matches_data
        
        filtered_matches = []
        
        for match in self.matches_data:
            info = match.get('info', {})
            
            # Filter by venue
            if filters.get('venue') and info.get('venue') != filters['venue']:
                continue
            
            # Filter by format (match_type)
            if filters.get('format') and info.get('match_type') != filters['format']:
                continue
            
            # Filter by country (city)
            if filters.get('country') and info.get('city') != filters['country']:
                continue
            
            # Filter by years (can be multiple years)
            if filters.get('years'):
                years = filters['years'] if isinstance(filters['years'], list) else [filters['years']]
                match_dates = info.get('dates', [])
                if match_dates:
                    match_year = match_dates[0][:4]  # Extract year from date like "2024-02-02"
                    if match_year not in years:
                        continue
            
            # Filter by match type category (IPL vs International)
            if filters.get('match_category'):
                event_name = info.get('event', {}).get('name', '').lower()
                category = filters['match_category'].lower()
                
                if category == 'ipl':
                    # Look for IPL in event name
                    if 'ipl' not in event_name and 'indian premier league' not in event_name:
                        continue
                elif category == 'international':
                    # Exclude IPL matches for international
                    if 'ipl' in event_name or 'indian premier league' in event_name:
                        continue
            
            # Filter by team
            if filters.get('team'):
                teams = info.get('teams', [])
                if filters['team'] not in teams:
                    continue
            
            # Filter by date range
            if filters.get('start_date') or filters.get('end_date'):
                match_dates = info.get('dates', [])
                if match_dates:
                    match_date = datetime.strptime(match_dates[0], '%Y-%m-%d')
                    
                    if filters.get('start_date'):
                        start_date = datetime.strptime(filters['start_date'], '%Y-%m-%d')
                        if match_date < start_date:
                            continue
                    
                    if filters.get('end_date'):
                        end_date = datetime.strptime(filters['end_date'], '%Y-%m-%d')
                        if match_date > end_date:
                            continue
            
            filtered_matches.append(match)
        
        return filtered_matches
    
    def get_player_match_data(self, player_name, filters=None):
        """Get all match data for a specific player"""
        matches = self.filter_matches(filters)
        max_matches = None
        try:
            if filters and 'max_matches' in filters and filters['max_matches'] is not None:
                mv = filters['max_matches']
                if isinstance(mv, str):
                    mv = int(float(mv.strip())) if mv.strip() else None
                elif isinstance(mv, (int, float)):
                    mv = int(mv)
                max_matches = mv if (isinstance(mv, int) and mv > 0) else None
        except Exception:
            max_matches = None
        player_matches = []
        
        for match in matches:
            info = match.get('info', {})
            players = info.get('players', {})
            
            # Check if player is in this match
            player_team = None
            for team, team_players in players.items():
                if player_name in team_players:
                    player_team = team
                    break
            
            if not player_team:
                continue
            
            # Apply innings_type filter based on whether player's team batted first/second
            innings = match.get('innings', [])
            player_batted_first = None
            if innings and player_team:
                first_innings_team = innings[0].get('team') if len(innings) > 0 else None
                if first_innings_team == player_team:
                    player_batted_first = True
                else:
                    player_batted_first = False

            itype = (filters or {}).get('innings_type')
            if itype == 'batting_first' and player_batted_first is False:
                continue
            if itype == 'bowling_first' and player_batted_first is True:
                continue

            # Extract player's performance data
            match_data = {
                'match_info': info,
                'player_team': player_team,
                'batting_data': [],
                'bowling_data': [],
                'fielding_data': [],
                'innings_full': match.get('innings', [])
            }
            
            # Extract innings data
            for inning in innings:
                if inning.get('team') == player_team:
                    # Batting data
                    batting_stats = self._extract_batting_stats(inning, player_name, match, filters)
                    if batting_stats:
                        match_data['batting_data'].append(batting_stats)
                else:
                    # Bowling data
                    bowling_stats = self._extract_bowling_stats(inning, player_name, match, filters)
                    if bowling_stats:
                        match_data['bowling_data'].append(bowling_stats)
            
            player_matches.append(match_data)
            # Early exit if limit reached for diagnostic runs
            if max_matches and len(player_matches) >= max_matches:
                break
        
        return player_matches
    
    def _extract_batting_stats(self, inning, player_name, match=None, filters=None):
        """Extract batting statistics from an inning"""
        batting_stats = {
            'runs': 0,
            'balls': 0,
            'fours': 0,
            'sixes': 0,
            'ones': 0,
            'twos': 0,
            'dots': 0,
            'dismissal': None,
            'dismissal_type': None,
            'position': None
        }
        
        overs = inning.get('overs', [])
        # Apply phase filter to overs range if provided
        over_start, over_end = self._resolve_phase_over_range(match, filters)
        
        for idx, over in enumerate(overs, start=1):
            if over_start and over_end and not (over_start <= idx <= over_end):
                continue
            deliveries = over.get('deliveries', [])
            
            for delivery in deliveries:
                if delivery.get('batter') == player_name:
                    runs = self._to_int(delivery.get('runs', {}).get('batter', 0), 0)
                    batting_stats['runs'] += runs
                    batting_stats['balls'] += 1
                    
                    # Count run types
                    if runs == 0:
                        batting_stats['dots'] += 1
                    elif runs == 1:
                        batting_stats['ones'] += 1
                    elif runs == 2:
                        batting_stats['twos'] += 1
                    elif runs == 4:
                        batting_stats['fours'] += 1
                    elif runs == 6:
                        batting_stats['sixes'] += 1
                    
                    # Check for dismissal
                    if 'wickets' in delivery:
                        for wicket in delivery['wickets']:
                            if wicket.get('player_out') == player_name:
                                batting_stats['dismissal'] = True
                                batting_stats['dismissal_type'] = wicket.get('kind')
                                break
        
        return batting_stats if batting_stats['balls'] > 0 else None
    
    def _extract_bowling_stats(self, inning, player_name, match=None, filters=None):
        """Extract bowling statistics from an inning"""
        bowling_stats = {
            'overs': 0,
            'balls': 0,
            'runs_conceded': 0,
            'wickets': 0,
            'maidens': 0,
            'dots': 0,
            'fours_conceded': 0,
            'sixes_conceded': 0,
            'wides': 0,
            'no_balls': 0,
            'wicket_types': []
        }
        
        overs = inning.get('overs', [])
        over_start, over_end = self._resolve_phase_over_range(match, filters)
        
        for idx, over in enumerate(overs, start=1):
            if over_start and over_end and not (over_start <= idx <= over_end):
                continue
            deliveries = over.get('deliveries', [])
            over_runs = 0
            over_balls = 0
            over_legal_balls = 0
            
            for delivery in deliveries:
                if delivery.get('bowler') == player_name:
                    runs = self._to_int(delivery.get('runs', {}).get('total', 0), 0)
                    batter_runs = self._to_int(delivery.get('runs', {}).get('batter', 0), 0)
                    extras = self._to_int(delivery.get('runs', {}).get('extras', 0), 0)
                    
                    bowling_stats['balls'] += 1
                    over_balls += 1
                    
                    # Check for legal delivery
                    is_legal = True
                    if 'extras' in delivery:
                        extra_types = delivery['extras']
                        if 'wides' in extra_types:
                            bowling_stats['wides'] += self._to_int(extra_types['wides'], 0)
                            is_legal = False
                        if 'noballs' in extra_types:
                            bowling_stats['no_balls'] += self._to_int(extra_types['noballs'], 0)
                            is_legal = False
                    
                    if is_legal:
                        over_legal_balls += 1
                    
                    bowling_stats['runs_conceded'] += runs
                    over_runs += runs
                    
                    # Count boundary conceded
                    if batter_runs == 4:
                        bowling_stats['fours_conceded'] += 1
                    elif batter_runs == 6:
                        bowling_stats['sixes_conceded'] += 1
                    elif batter_runs == 0 and extras == 0:
                        bowling_stats['dots'] += 1
                    
                    # Check for wickets
                    if 'wickets' in delivery:
                        for wicket in delivery['wickets']:
                            # Only count if bowler gets the wicket (not run out, etc.)
                            wicket_type = wicket.get('kind', '')
                            if wicket_type not in ['run out', 'retired hurt', 'retired out']:
                                bowling_stats['wickets'] += 1
                                bowling_stats['wicket_types'].append(wicket_type)
            
            # Check if over was a maiden (legal balls = 6 and runs = 0)
            if over_legal_balls == 6 and over_runs == 0:
                bowling_stats['maidens'] += 1
        
        # Calculate overs bowled
        if bowling_stats['balls'] > 0:
            legal_balls = bowling_stats['balls'] - bowling_stats['wides'] - bowling_stats['no_balls']
            bowling_stats['overs'] = legal_balls // 6 + (legal_balls % 6) / 10
        
        return bowling_stats if bowling_stats['balls'] > 0 else None

    def _resolve_phase_over_range(self, match, filters):
        """Map phase filter into (start_over, end_over) inclusive based on match format.
        filters['phase'] expected values:
          - 't20_1_6','t20_7_12','t20_13_16','t20_17_20'
          - 'odi_1_10','odi_11_20','odi_21_30','odi_31_40','odi_41_50'
        Returns (None, None) if no restriction applies.
        """
        if not filters or not filters.get('phase'):
            return (None, None)
        phase = filters.get('phase')
        # Allow only phases matching the current format if available
        fmt = None
        if filters.get('format'):
            fmt = filters.get('format')
        elif match:
            fmt = match.get('info', {}).get('match_type')

        # Define mappings
        t20_map = {
            't20_1_6': (1, 6),
            't20_7_12': (7, 12),
            't20_13_16': (13, 16),
            't20_17_20': (17, 20),
        }
        odi_map = {
            'odi_1_10': (1, 10),
            'odi_11_20': (11, 20),
            'odi_21_30': (21, 30),
            'odi_31_40': (31, 40),
            'odi_41_50': (41, 50),
        }

        if phase in t20_map and (fmt is None or fmt == 'T20'):
            return t20_map[phase]
        if phase in odi_map and (fmt is None or fmt in ['ODI', 'ODM']):
            return odi_map[phase]
        return (None, None)
    
    def get_team_match_data(self, team_name, filters=None):
        """Get all match data for a specific team"""
        # The top-level filters (venue, format, country, years, match_category, team) apply first
        base_filters = {
            k: v for k, v in (filters or {}).items()
            if k in ['venue', 'format', 'country', 'years', 'match_category']
        }
        matches = self.filter_matches(base_filters)
        team_matches = []
        
        for match in matches:
            info = match.get('info', {})
            teams = info.get('teams', [])
            
            if team_name not in teams:
                continue
            
            # Determine opponent
            opponent = None
            for team in teams:
                if team != team_name:
                    opponent = team
                    break

            # If opponent filters provided, enforce them
            opp_filters = (filters or {}).get('opponents')
            if opp_filters:
                # accept both list and single string
                if isinstance(opp_filters, str):
                    opp_list = [opp_filters]
                else:
                    opp_list = list(opp_filters)
                if opponent not in opp_list:
                    continue
            
            # Determine result
            outcome = info.get('outcome', {})
            winner = outcome.get('winner')
            result = 'win' if winner == team_name else 'loss' if winner else 'draw'
            
            # Determine toss outcome
            toss = info.get('toss', {})
            toss_winner = toss.get('winner')
            toss_decision = toss.get('decision')
            won_toss = toss_winner == team_name
            
            match_data = {
                'match_info': info,
                'opponent': opponent,
                'result': result,
                'won_toss': won_toss,
                'toss_decision': toss_decision,
                'batting_first': None,
                'bowling_first': None,
                'team_score': None,
                'opponent_score': None,
                'innings_full': match.get('innings', [])
            }
            
            # Extract innings data
            innings = match.get('innings', [])
            for i, inning in enumerate(innings):
                if inning.get('team') == team_name:
                    if i == 0:
                        match_data['batting_first'] = True
                    elif i == 1:
                        match_data['batting_first'] = False
                    
                    # Calculate team score
                    match_data['team_score'] = self._calculate_team_score(inning)
                else:
                    # Opponent's innings
                    match_data['opponent_score'] = self._calculate_team_score(inning)
            
            # Apply innings_type filter at match level if requested
            innings_type = (filters or {}).get('innings_type')
            if innings_type == 'first' and match_data['batting_first'] is False:
                continue
            if innings_type == 'second' and match_data['batting_first'] is True:
                continue

            team_matches.append(match_data)
        
        return team_matches
    
    def _calculate_team_score(self, inning):
        """Calculate total score from an inning"""
        total_runs = 0
        total_wickets = 0
        
        overs = inning.get('overs', [])
        
        for over in overs:
            deliveries = over.get('deliveries', [])
            
            for delivery in deliveries:
                runs = self._to_int(delivery.get('runs', {}).get('total', 0), 0)
                total_runs += runs
                
                if 'wickets' in delivery:
                    total_wickets += len(delivery['wickets'])
        
        return {
            'runs': total_runs,
            'wickets': total_wickets,
            'overs': len(overs)
        }
    
    def get_venue_matches(self, venue_name, filters=None):
        """Get all matches played at a specific venue"""
        venue_filters = filters.copy() if filters else {}
        venue_filters['venue'] = venue_name
        
        return self.filter_matches(venue_filters)