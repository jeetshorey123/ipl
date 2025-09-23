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
# Supabase is no longer used; local JSON mode only

load_dotenv()
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize data processor and start fast background local load (concurrent)
data_processor = CricketDataProcessor('data/')
try:
    local_limit_raw = (os.getenv('LOCAL_MAX_FILES') or '').strip().lower()
    local_limit = None
    if local_limit_raw:
        if local_limit_raw not in {'all', 'none', 'unlimited', 'null', 'inf', 'infinite'}:
            try:
                n = int(float(local_limit_raw))
                local_limit = None if n <= 0 else n
            except Exception:
                local_limit = None
    local_workers_raw = (os.getenv('LOCAL_MAX_WORKERS') or '').strip()
    try:
        local_workers = int(float(local_workers_raw)) if local_workers_raw else 24
    except Exception:
        local_workers = 24
    # Optional include pattern (e.g., '**/*.json' or '2024_*.json')
    include_pattern = (os.getenv('LOCAL_INCLUDE_PATTERN') or '').strip() or None
    # Enforce default cap of 3613 unique matches loaded (deduplicated) unless overridden
    uniq_raw = (os.getenv('LOCAL_MAX_UNIQUE_MATCHES') or '').strip()
    try:
        default_max_unique = int(float(uniq_raw)) if uniq_raw else 3613
    except Exception:
        default_max_unique = 3613
    # Start non-blocking background load from local data folder
    data_processor.start_background_local_load(max_workers=local_workers, max_files=local_limit, include_pattern=include_pattern, max_unique_matches=default_max_unique)
except Exception:
    logger.exception("Failed to start background local JSON load")
player_stats = PlayerStatsCalculator(data_processor)
venue_analyzer = VenueAnalyzer(data_processor)
team_analyzer = TeamAnalyzer(data_processor)
## Removed win predictor per request; focusing on teams, venues, and players only

## Removed Supabase environment and usage

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

## Removed predictions page route

## Removed Supabase status/sample endpoints

@app.route('/api/data/reload', methods=['POST'])
def reload_data():
    """Force reload from local data directory (clears caches)."""
    try:
        payload = request.get_json(silent=True) or {}
        max_files = payload.get('max_files')
        try:
            if isinstance(max_files, str):
                max_files = int(float(max_files.strip()))
        except Exception:
            max_files = None
        # Allow override of worker count via request
        max_workers = payload.get('max_workers')
        try:
            if isinstance(max_workers, str):
                max_workers = int(float(max_workers.strip()))
        except Exception:
            max_workers = None
        include_pattern = payload.get('include_pattern') or None
        # Optional override of unique match cap via request; default remains 3613
        max_unique = payload.get('max_unique_matches')
        try:
            if isinstance(max_unique, str):
                max_unique = int(float(max_unique.strip()))
        except Exception:
            max_unique = None
        if max_unique is None:
            uniq_env = (os.getenv('LOCAL_MAX_UNIQUE_MATCHES') or '').strip()
            try:
                max_unique = int(float(uniq_env)) if uniq_env else 3613
            except Exception:
                max_unique = 3613
        res = data_processor.reload_from_local(max_files=max_files, max_workers=(max_workers or 24), include_pattern=include_pattern, max_unique_matches=max_unique)
        return jsonify(res)
    except Exception as e:
        logger.error(f"Error reloading data: {e}")
        return jsonify({'error': str(e)}), 500

## Removed storage list/scan endpoints

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

@app.route('/api/data/unified-options')
def unified_options():
    """Return a single combined list of players, teams, and venues for one dropdown."""
    try:
        players = list(data_processor.get_all_players())
        teams = list(data_processor.get_all_teams())
        venues = list(data_processor.get_all_venues())
        def pack(kind, name):
            return {'type': kind, 'name': name}
        combined = [pack('player', p) for p in players] + [pack('team', t) for t in teams] + [pack('venue', v) for v in venues]
        # Sort case-insensitively by name
        combined.sort(key=lambda x: x['name'].lower())
        return jsonify({'options': combined, 'counts': {'players': len(players), 'teams': len(teams), 'venues': len(venues)}})
    except Exception as e:
        logger.error(f"Error getting unified options: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def unified_search():
    """Unified search across players, teams, and venues. Returns overall stats for the first exact match.
    Query parameters:
      - q: query string
      - type: optional 'player'|'team'|'venue' to disambiguate
    """
    try:
        q = (request.args.get('q') or '').strip()
        ql = q.lower()
        kind = (request.args.get('type') or '').strip().lower()
        if not q:
            return jsonify({'error': 'Missing q'}), 400
        # Try to disambiguate by exact case-insensitive match
        if not kind or kind == 'player':
            players = data_processor.get_all_players()
            for p in players:
                if p.lower() == ql:
                    stats = player_stats.get_player_stats(p, {})
                    return jsonify({'type': 'player', 'name': p, 'data': stats})
            if kind == 'player':
                return jsonify({'error': f'Player not found: {q}'}), 404
        if not kind or kind == 'team':
            teams = data_processor.get_all_teams()
            for t in teams:
                if t.lower() == ql:
                    stats = team_analyzer.get_team_stats(t, {})
                    return jsonify({'type': 'team', 'name': t, 'data': stats})
            if kind == 'team':
                return jsonify({'error': f'Team not found: {q}'}), 404
        if not kind or kind == 'venue':
            venues = data_processor.get_all_venues()
            for v in venues:
                if v.lower() == ql:
                    stats = venue_analyzer.get_venue_stats(v, {})
                    return jsonify({'type': 'venue', 'name': v, 'data': stats})
            if kind == 'venue':
                return jsonify({'error': f'Venue not found: {q}'}), 404
        # If no exact match, return suggestions
        suggest = []
        for p in data_processor.get_all_players():
            if ql in p.lower():
                suggest.append({'type': 'player', 'name': p})
                if len(suggest) >= 10:
                    break
        if len(suggest) < 10:
            for t in data_processor.get_all_teams():
                if ql in t.lower():
                    suggest.append({'type': 'team', 'name': t})
                    if len(suggest) >= 20:
                        break
        if len(suggest) < 20:
            for v in data_processor.get_all_venues():
                if ql in v.lower():
                    suggest.append({'type': 'venue', 'name': v})
                    if len(suggest) >= 30:
                        break
        return jsonify({'query': q, 'suggestions': suggest})
    except Exception as e:
        logger.error(f"Error in unified search: {e}")
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

## Removed prediction API

## Removed predictor retrain/status/save/load APIs

 

 

 

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
            'venues_count': len(getattr(dp, 'venues_cache', set()))
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

 

 

 

if __name__ == '__main__':
    # Disable reloader to avoid double-loading the heavy dataset on startup
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=5000)