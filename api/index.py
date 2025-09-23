from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
from collections import defaultdict
from datetime import datetime
import logging

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
        stats = venue_analyzer.get_venue_stats(venue_name)
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
        total_matches = len(data_processor.matches)
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

# Vercel handler
def handler(request):
    return app(request.environ, lambda status, headers: None)

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)