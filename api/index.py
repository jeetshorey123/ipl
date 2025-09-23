from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
from collections import defaultdict
from datetime import datetime
import logging
import time

# Import our data processing modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data_processor import CricketDataProcessor
from player_stats import PlayerStatsCalculator
from venue_analyzer import VenueAnalyzer
from team_analyzer import TeamAnalyzer
# Optional: supabase status if needed
from supabase_client import supabase_client
# WinPredictor removed to reduce deployment size

app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize data processor (Supabase-only; local path unused)
data_processor = CricketDataProcessor('../data/')
# Start background Supabase load (env-configurable)
try:
    max_files_env = os.getenv('SUPABASE_MAX_FILES')
    max_workers_env = os.getenv('SUPABASE_MAX_WORKERS')
    try:
        max_files_val = int(float(max_files_env)) if (max_files_env not in [None, '', 'none', 'null']) else None
        if isinstance(max_files_val, int) and max_files_val <= 0:
            max_files_val = None
    except Exception:
        max_files_val = None
    try:
        max_workers_val = int(float(max_workers_env)) if max_workers_env else 24
        if max_workers_val < 4:
            max_workers_val = 4
        if max_workers_val > 64:
            max_workers_val = 64
    except Exception:
        max_workers_val = 24
    data_processor.start_background_supabase_load(max_workers=max_workers_val, max_files=max_files_val)
except Exception:
    logging.getLogger(__name__).exception("Failed to start background load in Vercel handler")

player_stats = PlayerStatsCalculator(data_processor)
venue_analyzer = VenueAnalyzer(data_processor)
team_analyzer = TeamAnalyzer(data_processor)

@app.context_processor
def inject_static_version():
    """Inject a cache-busting version string for static assets.
    Prefer Vercel commit SHA or env override; fallback to hourly timestamp.
    """
    ver = os.getenv('STATIC_VERSION') or os.getenv('VERCEL_GIT_COMMIT_SHA')
    if not ver:
        # change hourly to avoid excessive invalidation
        ver = str(int(time.time() // 3600))
    return dict(STATIC_VERSION=ver)

@app.route('/')
def home():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/players')
def players():
    """Players page"""
    return render_template('players.html')

@app.route('/players-enhanced')
def players_enhanced():
    """Enhanced player analysis page"""
    return render_template('players_enhanced.html')

@app.route('/players-comparison')
def players_comparison():
    """Player comparison page"""
    return render_template('players_comparison.html')

@app.route('/venues')
def venues():
    """Venues analysis page"""
    return render_template('venues.html')

@app.route('/teams')
def teams():
    """Teams analysis page"""
    return render_template('teams.html')

@app.route('/predictions')
def predictions():
    return "Predictions feature disabled", 410

# Health and data endpoints required by frontend
@app.route('/api/data/health')
def data_health():
    try:
        dp = data_processor
        base = {
            'matches_loaded': len(dp.matches_data),
            'players_count': len(getattr(dp, 'players_cache', set())),
            'teams_count': len(getattr(dp, 'teams_cache', set())),
            'venues_count': len(getattr(dp, 'venues_cache', set())),
            'supabase_connected': True if supabase_client and supabase_client.is_connected else False
        }
        status = dp.get_loading_status() if hasattr(dp, 'get_loading_status') else {}
        if isinstance(status, dict):
            base.update(status)
        return jsonify(base)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in data health: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/players')
def api_data_players():
    try:
        players = list(data_processor.get_all_players())
        return jsonify({'players': sorted(players), 'total_players': len(players)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/retry-missing', methods=['POST'])
def api_retry_missing():
    try:
        payload = request.get_json(silent=True) or {}
        max_workers = payload.get('max_workers')
        try:
            if isinstance(max_workers, str):
                max_workers = int(float(max_workers.strip()))
            elif not isinstance(max_workers, int):
                max_workers = None
        except Exception:
            max_workers = None
        res = data_processor.retry_missing_files(max_workers=max_workers or 6)
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoints
@app.route('/api/player-stats/<player_name>')
def get_player_stats(player_name):
    """Get comprehensive statistics for a specific player"""
    try:
        year = request.args.get('year', type=int)
        innings_type = request.args.get('innings_type', 'overall')  # batting_first, bowling_first, or overall
        venue = request.args.get('venue')
        
        stats = player_stats.get_player_stats(player_name, year=year, innings_type=innings_type, venue=venue)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting player stats for {player_name}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/compare-players')
def compare_players():
    """Compare two players"""
    try:
        player1 = request.args.get('player1')
        player2 = request.args.get('player2')
        year = request.args.get('year', type=int)
        innings_type = request.args.get('innings_type', 'overall')
        venue = request.args.get('venue')
        
        if not player1 or not player2:
            return jsonify({'error': 'Both players are required'}), 400
        
        comparison = player_stats.compare_players(player1, player2, year=year, innings_type=innings_type, venue=venue)
        return jsonify(comparison)
    except Exception as e:
        logger.error(f"Error comparing players: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/players')
def get_players():
    """Get list of all players"""
    try:
        players = player_stats.get_all_players()
        return jsonify(sorted(players))
    except Exception as e:
        logger.error(f"Error getting players: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/years')
def get_years():
    """Get list of available years"""
    try:
        years = player_stats.get_available_years()
        return jsonify(sorted(years, reverse=True))
    except Exception as e:
        logger.error(f"Error getting years: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/venues')
def get_venues():
    """Get list of all venues"""
    try:
        venues = venue_analyzer.get_all_venues()
        return jsonify(sorted(venues))
    except Exception as e:
        logger.error(f"Error getting venues: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/venue-stats/<venue_name>')
def get_venue_stats(venue_name):
    """Get statistics for a specific venue"""
    try:
        # Accept optional filters (format, country, years as JSON array)
        filters = {}
        fmt = request.args.get('format')
        if fmt:
            filters['format'] = fmt
        country = request.args.get('country')
        if country:
            filters['country'] = country
        years_raw = request.args.get('years')
        if years_raw:
            try:
                # years may be JSON array or comma-separated
                if years_raw.strip().startswith('['):
                    import json as _json
                    filters['years'] = _json.loads(years_raw)
                else:
                    filters['years'] = [y.strip() for y in years_raw.split(',') if y.strip()]
            except Exception:
                pass
        stats = venue_analyzer.get_venue_stats(venue_name, filters)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting venue stats for {venue_name}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams')
def get_teams():
    """Get list of all teams"""
    try:
        teams = team_analyzer.get_all_teams()
        return jsonify(sorted(teams))
    except Exception as e:
        logger.error(f"Error getting teams: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/team-stats/<team_name>')
def get_team_stats(team_name):
    """Get statistics for a specific team"""
    try:
        stats = team_analyzer.get_team_stats(team_name)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting team stats for {team_name}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict-match', methods=['POST'])
def predict_match():
    return jsonify({'error': 'Prediction feature disabled for deployment size constraints'}), 410

@app.route('/api/dashboard')
def get_dashboard_data():
    """Get summary data for dashboard"""
    try:
        total_matches = len(data_processor.matches_data)
        total_players = len(player_stats.get_all_players())
        total_venues = len(venue_analyzer.get_all_venues())
        total_teams = len(team_analyzer.get_all_teams())
        
        # Get some interesting stats
        venue_stats = []
        for venue in list(venue_analyzer.get_all_venues())[:5]:  # Top 5 venues
            stats = venue_analyzer.get_venue_stats(venue)
            venue_stats.append({
                'venue': venue,
                'matches': stats.get('total_matches', 0),
                'avg_score': stats.get('avg_first_innings_score', 0)
            })
        
        return jsonify({
            'total_matches': total_matches,
            'total_players': total_players,
            'total_venues': total_venues,
            'total_teams': total_teams,
            'venue_stats': venue_stats
        })
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ----- Additional endpoints to support Venues UI -----

@app.route('/api/all-venues')
def api_all_venues():
    """Return all venues wrapped in an object for frontend convenience."""
    try:
        venues = sorted(venue_analyzer.get_all_venues())
        return jsonify({'venues': venues, 'total': len(venues)})
    except Exception as e:
        logger.error(f"Error getting all venues: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/all-countries')
def api_all_countries():
    """Return all countries/cities wrapped in an object."""
    try:
        countries = sorted(data_processor.get_all_countries())
        return jsonify({'countries': countries, 'total': len(countries)})
    except Exception as e:
        logger.error(f"Error getting all countries: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/years')
def api_data_years():
    """Alias that returns available years as an object (used by venues page)."""
    try:
        years = data_processor.get_available_years()
        return jsonify({'years': years, 'total': len(years)})
    except Exception as e:
        logger.error(f"Error getting years: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/venue-overview')
def api_venue_overview():
    """Return a lightweight overview for all venues with optional filters.
    Shape per card needs: venue, country, total_matches, avg_score, bat_first_wins (%).
    """
    try:
        # Parse filters
        filters = {}
        v = request.args.get('venue')
        if v:
            filters['venue'] = v
        fmt = request.args.get('format')
        if fmt:
            filters['format'] = fmt
        country = request.args.get('country')
        if country:
            filters['country'] = country
        years_raw = request.args.get('years')
        if years_raw:
            try:
                if years_raw.strip().startswith('['):
                    import json as _json
                    filters['years'] = _json.loads(years_raw)
                else:
                    filters['years'] = [y.strip() for y in years_raw.split(',') if y.strip()]
            except Exception:
                pass

        matches = data_processor.filter_matches(filters)
        # Aggregate by venue
        agg = {}
        for match in matches:
            try:
                info = match.get('info', {})
                venue = info.get('venue') or 'Unknown'
                city = info.get('city') or ''
                rec = agg.get(venue)
                if not rec:
                    rec = {
                        'venue': venue,
                        'country': city,
                        'total_matches': 0,
                        'runs_total': 0,
                        'innings_count': 0,
                        'bat_first_wins_cnt': 0,
                        'decided_cnt': 0,
                    }
                    agg[venue] = rec
                rec['total_matches'] += 1
                innings = match.get('innings', []) or []
                # total runs across innings
                for inning in innings:
                    try:
                        sc = data_processor._calculate_team_score(inning)
                        rec['runs_total'] += sc.get('runs', 0)
                        rec['innings_count'] += 1
                    except Exception:
                        continue
                # bat-first win percentage
                if len(innings) >= 1:
                    first_team = innings[0].get('team')
                    winner = (info.get('outcome') or {}).get('winner')
                    if first_team and winner:
                        rec['decided_cnt'] += 1
                        if winner == first_team:
                            rec['bat_first_wins_cnt'] += 1
            except Exception:
                continue

        venues = []
        for rec in agg.values():
            innings_count = rec['innings_count'] if rec['innings_count'] else 0
            avg_score = round((rec['runs_total'] / max(innings_count, 1)), 1)
            decided = rec['decided_cnt'] if rec['decided_cnt'] else 0
            bat_first_pct = round((rec['bat_first_wins_cnt'] / max(decided, 1)) * 100, 1) if decided else 0
            venues.append({
                'venue': rec['venue'],
                'country': rec['country'],
                'total_matches': rec['total_matches'],
                'avg_score': avg_score,
                'bat_first_wins': bat_first_pct,
            })

        venues.sort(key=lambda x: x['total_matches'], reverse=True)
        return jsonify({'venues': venues, 'total_venues': len(venues), 'filters_applied': filters})
    except Exception as e:
        logger.error(f"Error building venue overview: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/venue-analysis/<venue_name>')
def api_venue_analysis(venue_name):
    """Detailed venue analysis using VenueAnalyzer with optional filters."""
    try:
        filters = {}
        fmt = request.args.get('format')
        if fmt:
            filters['format'] = fmt
        country = request.args.get('country')
        if country:
            filters['country'] = country
        years_raw = request.args.get('years')
        if years_raw:
            try:
                if years_raw.strip().startswith('['):
                    import json as _json
                    filters['years'] = _json.loads(years_raw)
                else:
                    filters['years'] = [y.strip() for y in years_raw.split(',') if y.strip()]
            except Exception:
                pass
        stats = venue_analyzer.get_venue_stats(venue_name, filters)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting venue analysis for {venue_name}: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)