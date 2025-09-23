from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
from datetime import datetime
import logging
from dotenv import load_dotenv

# Import our data processing modules
from data_processor import CricketDataProcessor
from player_stats import PlayerStatsCalculator
from venue_analyzer import VenueAnalyzer
from team_analyzer import TeamAnalyzer
from win_predictor import WinPredictor
from supabase_client import get_supabase_status, supabase_client

load_dotenv()
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize data processor and choose data source (Supabase vs Local JSON)
data_processor = CricketDataProcessor('data/')

# Decide source based on env var USE_LOCAL_DATA=true|false
use_local_data = str(os.getenv('USE_LOCAL_DATA', '')).strip().lower() in ('1', 'true', 'yes', 'on')
if use_local_data:
    try:
        # Optional limit via LOCAL_MAX_FILES (fallback to count of JSON files)
        local_max_env = os.getenv('LOCAL_MAX_FILES') or os.getenv('SUPABASE_MAX_FILES')
        limit_matches = None
        try:
            limit_matches = int(float(local_max_env)) if local_max_env else None
        except Exception:
            limit_matches = None
        if limit_matches is None:
            try:
                from glob import glob
                limit_matches = len(glob(os.path.join('data', '*.json')))
            except Exception:
                limit_matches = 200  # fallback
        logger.info(f"Loading local JSON data (limit {limit_matches}) from ./data")
        data_processor.load_all_matches(limit_matches=limit_matches)
    except Exception:
        logger.exception("Failed to load local JSON data")
else:
    # Begin background loading of matches from Supabase for fast startup
    try:
        max_files_env = os.getenv('SUPABASE_MAX_FILES')
        try:
            # Default to 5 files if not explicitly configured
            max_files_val = int(float(max_files_env)) if max_files_env else 5
        except Exception:
            max_files_val = 5
        data_processor.start_background_supabase_load(max_workers=16, max_files=max_files_val)
    except Exception:
        logger.exception("Failed to start background load")
player_stats = PlayerStatsCalculator(data_processor)
venue_analyzer = VenueAnalyzer(data_processor)
team_analyzer = TeamAnalyzer(data_processor)
win_predictor = WinPredictor(data_processor)

# Supabase environment (loaded but not required for local JSON processing)
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_PROJECT_ID = os.getenv('SUPABASE_PROJECT_ID')

@app.route('/')
def home():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/players')
def players():
    """Players page"""
    return render_template('players.html')


@app.route('/players-comparison')
def players_comparison():
    """Player comparison page"""
    return render_template('players_comparison.html')

@app.route('/venues')
def venues():
    """Venues page"""
    return render_template('venues.html')

@app.route('/teams')
def teams():
    """Teams page"""
    return render_template('teams.html')

@app.route('/predictions')
def predictions():
    """Win predictions page"""
    return render_template('predictions_new.html')

@app.route('/api/supabase/status')
def supabase_status():
    """Return Supabase connectivity and table info."""
    try:
        status = get_supabase_status()
        # Try listing storage top-level if configured
        try:
            if supabase_client and supabase_client.is_connected and supabase_client.bucket_name:
                files = supabase_client.supabase.storage.from_(supabase_client.bucket_name).list(supabase_client.bucket_prefix or '')
                status['storage']['top_level_count'] = len(files)
        except Exception as se:
            status['storage']['list_error'] = str(se)
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting Supabase status: {e}")
        return jsonify({'connected': False, 'error': str(e)})

@app.route('/api/supabase/sample')
def supabase_sample():
    """Fetch a small sample of rows and show extraction outcome."""
    try:
        if not supabase_client or not supabase_client.is_connected:
            return jsonify({'error': 'Supabase not connected'}), 400
        # Try from storage bucket first
        rows = []
        used_source = 'bucket'
        try:
            rows = supabase_client.get_all_matches_from_bucket(limit=3)
        except Exception:
            rows = []
        if not rows:
            used_source = 'table'
            rows = supabase_client.get_all_matches(limit=3)
        from data_processor import CricketDataProcessor
        dp = CricketDataProcessor('data/')
        samples = []
        for row in rows:
            try:
                match = dp._extract_match_from_row(row)
                ok = bool(match and 'info' in match and 'innings' in match)
                keys = list(row.keys()) if isinstance(row, dict) else (['<json-from-bucket>'] if isinstance(row, dict) else [])
                samples.append({'row_type': type(row).__name__, 'row_keys': keys, 'extracted': ok, 'info_keys': list(match.get('info', {}).keys()) if ok else []})
            except Exception as e:
                samples.append({'error': str(e)})
        return jsonify({'source': used_source, 'count': len(rows), 'samples': samples})
    except Exception as e:
        logger.error(f"Error fetching Supabase sample: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/reload', methods=['POST'])
def reload_data():
    """Force reload from Supabase (clears caches)."""
    try:
        payload = request.get_json(silent=True) or {}
        max_files = payload.get('max_files')
        try:
            if isinstance(max_files, str):
                max_files = int(float(max_files.strip()))
        except Exception:
            max_files = None
        res = data_processor.reload_from_supabase(max_files=max_files)
        return jsonify(res)
    except Exception as e:
        logger.error(f"Error reloading data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/storage/list')
def storage_list():
    """List objects and directories at a given prefix for debugging storage layout."""
    try:
        if not supabase_client or not supabase_client.is_connected or not supabase_client.bucket_name:
            return jsonify({'error': 'Supabase storage not configured'}), 400
        prefix = request.args.get('prefix', default=supabase_client.bucket_prefix or '')
        bucket = supabase_client.bucket_name
        storage = supabase_client.supabase.storage.from_(bucket)
        items = storage.list(prefix)
        out = []
        for it in items:
            if isinstance(it, dict):
                out.append({k: it.get(k) for k in ['name', 'id', 'updated_at', 'metadata', 'created_at'] if k in it})
        return jsonify({'bucket': bucket, 'prefix': prefix, 'count': len(out), 'items': out})
    except Exception as e:
        logger.error(f"Error listing storage: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/storage/scan')
def storage_scan():
    """Recursively scan storage to enumerate JSON files and effective prefix."""
    try:
        if not supabase_client or not supabase_client.is_connected or not supabase_client.bucket_name:
            return jsonify({'error': 'Supabase storage not configured'}), 400
        # Use the client crawl via get_all_matches_from_bucket but without downloading all contents
        bucket = supabase_client.bucket_name
        storage = supabase_client.supabase.storage.from_(bucket)

        def crawl(path: str):
            to_visit = [path]
            files = []
            visited = set()
            while to_visit:
                raw_p = to_visit.pop(0)
                p = (raw_p or '').strip('/')
                if p in visited:
                    continue
                visited.add(p)
                try:
                    items = storage.list(p if p else '')
                except Exception:
                    continue
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    name = it.get('name')
                    if not name:
                        continue
                    full_path = f"{p}/{name}" if p else name
                    meta = it.get('metadata') or {}
                    mimetype = meta.get('mimetype') or meta.get('contentType')
                    is_file = bool(mimetype) or ('.' in name)
                    if is_file and name.lower().endswith('.json'):
                        files.append(full_path)
                    elif not is_file:
                        to_visit.append(full_path)
            return files

        prefixes_to_try = []
        if supabase_client.bucket_prefix is not None:
            prefixes_to_try.extend([supabase_client.bucket_prefix, (supabase_client.bucket_prefix.rstrip('/') + '/') if supabase_client.bucket_prefix else ''])
        prefixes_to_try.extend(['', 'data', 'data/', 'matches', 'matches/', 'json', 'json/', '2024', '2024/'])

        seen = set()
        found = []
        for p in prefixes_to_try:
            if p in seen:
                continue
            seen.add(p)
            f = crawl(p)
            if f:
                found = f
                effective_prefix = p
                break
        return jsonify({'bucket': bucket, 'effective_prefix': effective_prefix if found else (supabase_client.bucket_prefix or ''), 'json_count': len(found), 'sample': found[:10]})
    except Exception as e:
        logger.error(f"Error scanning storage: {e}")
        return jsonify({'error': str(e)}), 500

# API Endpoints

@app.route('/api/data/years')
def get_available_years():
    """Get available years from the data"""
    try:
        years = data_processor.get_available_years()
        return jsonify({
            'years': years,
            'total_years': len(years)
        })
    except Exception as e:
        logger.error(f"Error getting available years: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/players')
def get_data_players():
    """Get all available players for dropdown lists"""
    try:
        players = list(data_processor.get_all_players())
        return jsonify({
            'players': sorted(players),
            'total_players': len(players)
        })
    except Exception as e:
        logger.error(f"Error getting players: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/players/compare')
def compare_players():
    """Compare two players with head-to-head analysis"""
    try:
        player1 = request.args.get('player1', '').strip()
        player2 = request.args.get('player2', '').strip()
        
        if not player1 or not player2:
            return jsonify({'error': 'Both player1 and player2 parameters are required'}), 400
        
        if player1 == player2:
            return jsonify({'error': 'Cannot compare a player with themselves'}), 400
        
        # Parse filters
        filters = {}
        filters_param = request.args.get('filters')
        if filters_param:
            try:
                filters = json.loads(filters_param)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid filters format'}), 400
        
        comparison_data = data_processor.player_comparison_calculator.compare_players(
            player1, player2, filters
        )
        
        return jsonify(comparison_data)
        
    except Exception as e:
        logger.error(f"Error in player comparison API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/players/<player_name>')
def get_player_stats(player_name):
    """Get comprehensive player statistics"""
    try:
        filters = {
            'venue': request.args.get('venue'),
            'format': request.args.get('format'),
            'phase': request.args.get('phase'),
            'phase_role': request.args.get('phase_role'),
            'country': request.args.get('country'),
            'match_category': request.args.get('match_category'),  # 'ipl' or 'international'
            'batting_first': request.args.get('batting_first'),
            'bowling_first': request.args.get('bowling_first'),
            'team': request.args.get('team'),
            # diagnostic/limit parameter: analyze only first N matches
            'max_matches': request.args.get('max_matches')
        }
        
        # Remove None values from filters
        filters = {k: v for k, v in filters.items() if v is not None}
        
        stats = data_processor.player_stats_calculator.get_player_stats(player_name, filters)
        
        if 'error' in stats:
            return jsonify(stats), 400
            
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting player stats for {player_name}: {e}")
        return jsonify({'error': f'Error analyzing player data: {str(e)}'}), 500

@app.route('/api/player-stats/<player_name>')
def get_player_stats_legacy(player_name):
    """Legacy endpoint for player statistics"""
    return get_player_stats(player_name)

@app.route('/api/player-comparison')
def compare_multiple_players():
    """Compare multiple players"""
    try:
        players = request.args.getlist('players')
        if len(players) < 2:
            return jsonify({'error': 'At least 2 players required for comparison'}), 400
        
        filters = {
            'venue': request.args.get('venue'),
            'format': request.args.get('format'),
            'country': request.args.get('country')
        }
        
        comparison = player_stats.compare_players(players, filters)
        return jsonify(comparison)
    except Exception as e:
        logger.error(f"Error comparing players: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dismissal-analysis/<player_name>')
def get_dismissal_analysis(player_name):
    """Get detailed dismissal analysis for a player"""
    try:
        filters = {
            'venue': request.args.get('venue'),
            'format': request.args.get('format')
        }
        
        analysis = player_stats.get_dismissal_analysis(player_name, filters)
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Error getting dismissal analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/run-distribution/<player_name>')
def get_run_distribution(player_name):
    """Get run distribution analysis for a player"""
    try:
        filters = {
            'venue': request.args.get('venue'),
            'format': request.args.get('format')
        }
        
        distribution = player_stats.get_run_distribution(player_name, filters)
        return jsonify(distribution)
    except Exception as e:
        logger.error(f"Error getting run distribution: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/venue-stats')
def get_venue_stats():
    """Get venue statistics"""
    try:
        venue = request.args.get('venue')
        if not venue:
            venues = venue_analyzer.get_all_venues()
            return jsonify({'venues': venues})
        
        stats = venue_analyzer.get_venue_stats(venue)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting venue stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/team-stats/<team_name>')
def get_team_stats(team_name):
    """Get team statistics"""
    try:
        filters = {
            'venue': request.args.get('venue'),
            'format': request.args.get('format'),
            'country': request.args.get('country'),
            'match_category': request.args.get('match_category'),
            'innings_type': request.args.get('innings_type'),
            'batting_order': request.args.get('batting_order')
        }
        # Parse years if provided as JSON array string
        years_param = request.args.get('years')
        if years_param:
            try:
                filters['years'] = json.loads(years_param)
            except json.JSONDecodeError:
                logger.warning("Invalid years parameter provided to team-stats; expected JSON array of strings")
        # Parse opponents list if provided
        opponents_param = request.args.get('opponents')
        if opponents_param:
            try:
                filters['opponents'] = json.loads(opponents_param)
            except json.JSONDecodeError:
                logger.warning("Invalid opponents parameter provided to team-stats; expected JSON array of strings")
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        stats = team_analyzer.get_team_stats(team_name, filters)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting team stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/team-comparison')
def compare_teams():
    """Compare teams"""
    try:
        teams = request.args.getlist('teams')
        if len(teams) < 2:
            return jsonify({'error': 'At least 2 teams required for comparison'}), 400
        
        filters = {
            'venue': request.args.get('venue'),
            'format': request.args.get('format')
        }
        
        comparison = team_analyzer.compare_teams(teams, filters)
        return jsonify(comparison)
    except Exception as e:
        logger.error(f"Error comparing teams: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict-win', methods=['POST'])
def predict_win():
    """Predict match outcome"""
    try:
        data = request.get_json()
        team1 = data.get('team1')
        team2 = data.get('team2')
        venue = data.get('venue')
        format_type = data.get('format')
        toss_winner = data.get('toss_winner')
        toss_decision = data.get('toss_decision')
        team1_players = data.get('team1_players') or []
        team2_players = data.get('team2_players') or []
        
        prediction = win_predictor.predict_match_outcome({
            'team1': team1,
            'team2': team2,
            'venue': venue,
            'format': format_type,
            'toss_winner': toss_winner,
            'toss_decision': toss_decision,
            'team1_players': team1_players,
            'team2_players': team2_players
        })
        
        return jsonify(prediction)
    except Exception as e:
        logger.error(f"Error predicting win: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/all-players')
def get_all_players():
    """Get list of all players"""
    try:
        players = data_processor.get_all_players()
        return jsonify({'players': sorted(players)})
    except Exception as e:
        logger.error(f"Error getting all players: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/all-teams')
def get_all_teams():
    """Get list of all teams"""
    try:
        teams = data_processor.get_all_teams()
        return jsonify({'teams': sorted(teams)})
    except Exception as e:
        logger.error(f"Error getting all teams: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/all-venues')
def get_all_venues():
    """Get list of all venues"""
    try:
        venues = data_processor.get_all_venues()
        return jsonify({'venues': sorted(venues)})
    except Exception as e:
        logger.error(f"Error getting all venues: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/venue-overview')
def get_venue_overview():
    """Get venue overview with optional filters"""
    try:
        venue = request.args.get('venue', '')
        format_type = request.args.get('format', '')
        country = request.args.get('country', '')
        years_param = request.args.get('years')
        years = None
        if years_param:
            try:
                years = json.loads(years_param)
            except json.JSONDecodeError:
                years = None
        
        venues = data_processor.get_all_venues()
        
        filtered_venues = []
        for venue_name in venues:
            v_filters = {}
            if format_type:
                v_filters['format'] = format_type
            if country:
                v_filters['country'] = country
            if years:
                v_filters['years'] = years
            
            # Fetch basic stats for overview via venue_analyzer
            stats = venue_analyzer.get_venue_stats(venue_name, v_filters)
            if 'error' in stats:
                continue
            
            if venue and venue.lower() not in venue_name.lower():
                continue
            
            # Compose a compact overview record
            cities = stats.get('general', {}).get('cities', {}) or {}
            country_name = next(iter(cities.keys())) if isinstance(cities, dict) and cities else ''
            overview = {
                'venue': venue_name,
                'country': country_name,
                'total_matches': stats.get('general', {}).get('total_matches', 0),
                'avg_score': stats.get('batting', {}).get('average_score', 0),
                'bat_first_wins': stats.get('toss', {}).get('bat_first_win_percentage', 0),
                'bowl_first_wins': stats.get('toss', {}).get('bowl_first_win_percentage', 0)
            }
            filtered_venues.append(overview)
        
        return jsonify({'venues': filtered_venues})
    except Exception as e:
        logger.error(f"Error getting venue overview: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/health')
def data_health():
    """Basic data health check: counts of matches, players, teams, venues."""
    try:
        dp = data_processor
        base = {
            'matches_loaded': len(dp.matches_data),
            'players_count': len(getattr(dp, 'players_cache', set())),
            'teams_count': len(getattr(dp, 'teams_cache', set())),
            'venues_count': len(getattr(dp, 'venues_cache', set())),
            'supabase_connected': True if 'supabase_client' in globals() and supabase_client and supabase_client.is_connected else False
        }
        status = dp.get_loading_status() if hasattr(dp, 'get_loading_status') else {}
        # Include background loading status
        base.update({'loading': status.get('loading'), 'files_loaded': status.get('files_loaded'), 'total_files': status.get('total_files')})
        return jsonify(base)
    except Exception as e:
        logger.error(f"Error in data health: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/venue-analysis/<venue_name>')
def venue_analysis(venue_name):
    """Detailed analysis for a single venue."""
    try:
        filters = {
            'format': request.args.get('format'),
            'country': request.args.get('country')
        }
        years_param = request.args.get('years')
        if years_param:
            try:
                filters['years'] = json.loads(years_param)
            except json.JSONDecodeError:
                pass
        filters = {k: v for k, v in filters.items() if v is not None}
        stats = venue_analyzer.get_venue_stats(venue_name, filters)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error in venue analysis API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/all-countries')
def get_all_countries():
    """Get all available countries/cities"""
    try:
        countries = data_processor.get_all_countries()
        return jsonify({'countries': countries})
    except Exception as e:
        logger.error(f"Error getting countries: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/match-categories')
def get_match_categories():
    """Get available match categories"""
    try:
        categories = data_processor.get_match_categories()
        return jsonify({'categories': categories})
    except Exception as e:
        logger.error(f"Error getting match categories: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict-match', methods=['POST'])
def predict_match():
    """Predict match outcome based on team composition"""
    try:
        data = request.get_json()
        
        # Extract team data
        team1_data = data.get('team1', {})
        team2_data = data.get('team2', {})
        venue = data.get('venue', '')
        format_type = data.get('format', '')
        toss_winner = data.get('toss_winner', '')
        toss_decision = data.get('toss_decision', '')
        
        # Use win predictor to make prediction
        win_predictor = data_processor.win_predictor
        
        # Create a simplified prediction based on basic team strength
        # This is a basic implementation - you could enhance it with more complex analysis
        team1_strength = calculate_team_strength(team1_data.get('players', []))
        team2_strength = calculate_team_strength(team2_data.get('players', []))
        
        # Simple probability calculation
        total_strength = team1_strength + team2_strength
        team1_probability = (team1_strength / total_strength) * 100 if total_strength > 0 else 50
        team2_probability = 100 - team1_probability
        
        # Add venue and format factors (simplified)
        if venue and format_type:
            venue_factor = get_venue_factor(venue, format_type)
            team1_probability = max(10, min(90, team1_probability + venue_factor))
            team2_probability = 100 - team1_probability
        
        result = {
            'team1_probability': round(team1_probability, 1),
            'team2_probability': round(team2_probability, 1),
            'predicted_winner': team1_data.get('name') if team1_probability > team2_probability else team2_data.get('name'),
            'confidence': max(team1_probability, team2_probability),
            'factors': {
                'team1_strength': team1_strength,
                'team2_strength': team2_strength,
                'venue': venue,
                'format': format_type
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error predicting match: {e}")
        return jsonify({'error': str(e)}), 500

def calculate_team_strength(players):
    """Calculate basic team strength based on player statistics"""
    try:
        total_strength = 0
        player_count = 0
        
        for player in players:
            if not player:
                continue
                
            try:
                # Get player stats
                player_stats = data_processor.player_stats_calculator.get_player_stats(player)
                
                # Calculate basic strength metrics
                batting_strength = 0
                bowling_strength = 0
                
                if player_stats.get('total_runs', 0) > 0:
                    batting_avg = player_stats.get('batting_average', 0)
                    strike_rate = player_stats.get('strike_rate', 0)
                    batting_strength = (batting_avg * 0.6) + (strike_rate * 0.4)
                
                if player_stats.get('total_wickets', 0) > 0:
                    bowling_avg = player_stats.get('bowling_average', 50)
                    economy = player_stats.get('economy_rate', 10)
                    bowling_strength = (50 - bowling_avg) + (10 - economy)
                
                player_strength = max(batting_strength, bowling_strength)
                total_strength += player_strength
                player_count += 1
                
            except Exception as e:
                logger.warning(f"Error calculating strength for player {player}: {e}")
                continue
        
        return total_strength / max(player_count, 1)
        
    except Exception as e:
        logger.error(f"Error calculating team strength: {e}")
        return 50  # Default neutral strength

def get_venue_factor(venue, format_type):
    """Get venue-specific factors for prediction"""
    try:
        # Simple venue factors - could be enhanced with historical data
        venue_factors = {
            'T20': 0,  # Neutral for T20
            'ODI': 0,  # Neutral for ODI  
            'Test': 0  # Neutral for Test
        }
        return venue_factors.get(format_type, 0)
    except Exception as e:
        logger.error(f"Error getting venue factor: {e}")
        return 0

if __name__ == '__main__':
    # Disable reloader to avoid double-loading the heavy dataset on startup
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=5000)