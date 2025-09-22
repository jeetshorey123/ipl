import logging
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

class VenueAnalytics:
    def __init__(self, data_processor):
        self.data_processor = data_processor
    
    def get_venue_analytics(self, filters=None):
        """Get comprehensive venue analytics with filtering"""
        try:
            # Get all matches
            all_matches = self.data_processor.matches
            filtered_matches = self._apply_filters(all_matches, filters)
            
            if not filtered_matches:
                return {'error': 'No matches found with the applied filters'}
            
            venue_name = filters.get('venue') if filters else None
            
            if venue_name:
                # Detailed analysis for specific venue
                return self._get_detailed_venue_analysis(venue_name, filtered_matches, filters)
            else:
                # Overview of all venues
                return self._get_venues_overview(filtered_matches, filters)
                
        except Exception as e:
            logger.error(f"Error getting venue analytics: {e}")
            return {'error': f'Error processing venue data: {str(e)}'}
    
    def _apply_filters(self, matches, filters):
        """Apply filters to match data"""
        if not filters:
            return matches
        
        filtered_matches = []
        
        for match in matches:
            # Venue filter
            if filters.get('venue') and match.get('venue', '').lower() != filters['venue'].lower():
                continue
            
            # Format filter
            if filters.get('format') and match.get('format', '').lower() != filters['format'].lower():
                continue
            
            # Country filter
            if filters.get('country') and match.get('venue_country', '').lower() != filters['country'].lower():
                continue
            
            # Year filter
            if filters.get('year'):
                match_date = match.get('date')
                if match_date:
                    try:
                        # Parse different date formats
                        if isinstance(match_date, str):
                            if '-' in match_date:
                                year = int(match_date.split('-')[0])
                            elif '/' in match_date:
                                # Assuming DD/MM/YYYY or MM/DD/YYYY
                                parts = match_date.split('/')
                                year = int(parts[2]) if len(parts) == 3 else None
                            else:
                                year = None
                        else:
                            year = match_date.year if hasattr(match_date, 'year') else None
                        
                        if year and str(year) != filters['year']:
                            continue
                    except (ValueError, IndexError, AttributeError):
                        continue
            
            filtered_matches.append(match)
        
        return filtered_matches
    
    def _get_detailed_venue_analysis(self, venue_name, matches, filters):
        """Get detailed analysis for a specific venue"""
        venue_matches = [m for m in matches if m.get('venue', '').lower() == venue_name.lower()]
        
        if not venue_matches:
            return {'error': f'No matches found for venue "{venue_name}" with applied filters'}
        
        # Basic venue information
        basic_info = self._calculate_basic_info(venue_matches, venue_name)
        
        # Batting vs Bowling statistics
        batting_bowling_stats = self._calculate_batting_bowling_stats(venue_matches)
        
        # Toss impact analysis
        toss_impact = self._calculate_toss_impact(venue_matches)
        
        # Win patterns
        win_patterns = self._calculate_win_patterns(venue_matches)
        
        # Format-wise performance
        format_performance = self._calculate_format_performance(venue_matches)
        
        # Year-wise trends (if no year filter applied)
        year_trends = self._calculate_year_trends(venue_matches) if not filters.get('year') else None
        
        # Team performance at venue
        team_performance = self._calculate_team_performance(venue_matches)
        
        # Bowling and batting averages
        performance_stats = self._calculate_performance_stats(venue_matches)
        
        return {
            'venue_name': venue_name,
            'basic_info': basic_info,
            'batting_bowling_stats': batting_bowling_stats,
            'toss_impact': toss_impact,
            'win_patterns': win_patterns,
            'format_performance': format_performance,
            'year_trends': year_trends,
            'team_performance': team_performance,
            'performance_stats': performance_stats,
            'total_matches_analyzed': len(venue_matches),
            'filters_applied': filters or {}
        }
    
    def _get_venues_overview(self, matches, filters):
        """Get overview of all venues matching filters"""
        venue_stats = defaultdict(lambda: {
            'total_matches': 0,
            'total_runs': 0,
            'total_wickets': 0,
            'formats': set(),
            'countries': set(),
            'years': set(),
            'toss_wins': 0,
            'batting_first_wins': 0,
            'bowling_first_wins': 0
        })
        
        for match in matches:
            venue = match.get('venue', 'Unknown')
            stats = venue_stats[venue]
            
            stats['total_matches'] += 1
            stats['formats'].add(match.get('format', 'Unknown'))
            stats['countries'].add(match.get('venue_country', 'Unknown'))
            
            # Extract year
            match_date = match.get('date')
            if match_date:
                try:
                    if isinstance(match_date, str) and '-' in match_date:
                        year = match_date.split('-')[0]
                        stats['years'].add(year)
                except:
                    pass
            
            # Aggregate runs and wickets
            for team_key in ['team1_batting', 'team2_batting']:
                batting_data = match.get(team_key, [])
                for innings in batting_data:
                    stats['total_runs'] += innings.get('runs', 0)
            
            for team_key in ['team1_bowling', 'team2_bowling']:
                bowling_data = match.get(team_key, [])
                for innings in bowling_data:
                    stats['total_wickets'] += innings.get('wickets', 0)
            
            # Toss impact
            toss_winner = match.get('toss_winner', '')
            match_winner = match.get('winner', '')
            if toss_winner and match_winner and toss_winner.lower() == match_winner.lower():
                stats['toss_wins'] += 1
            
            # Batting first vs bowling first wins
            toss_decision = match.get('toss_decision', '').lower()
            if 'bat' in toss_decision and toss_winner.lower() == match_winner.lower():
                stats['batting_first_wins'] += 1
            elif 'bowl' in toss_decision and toss_winner.lower() == match_winner.lower():
                stats['bowling_first_wins'] += 1
        
        # Convert to list format
        venues_list = []
        for venue, stats in venue_stats.items():
            venues_list.append({
                'venue_name': venue,
                'total_matches': stats['total_matches'],
                'avg_runs_per_match': round(stats['total_runs'] / max(stats['total_matches'], 1), 1),
                'avg_wickets_per_match': round(stats['total_wickets'] / max(stats['total_matches'], 1), 1),
                'formats': list(stats['formats']),
                'countries': list(stats['countries']),
                'years': sorted(list(stats['years'])),
                'toss_advantage': round((stats['toss_wins'] / max(stats['total_matches'], 1)) * 100, 1),
                'batting_first_advantage': round((stats['batting_first_wins'] / max(stats['total_matches'], 1)) * 100, 1),
                'bowling_first_advantage': round((stats['bowling_first_wins'] / max(stats['total_matches'], 1)) * 100, 1)
            })
        
        # Sort by total matches
        venues_list.sort(key=lambda x: x['total_matches'], reverse=True)
        
        return {
            'venues': venues_list,
            'total_venues': len(venues_list),
            'total_matches_analyzed': len(matches),
            'filters_applied': filters or {}
        }
    
    def _calculate_basic_info(self, matches, venue_name):
        """Calculate basic venue information"""
        if not matches:
            return {}
        
        countries = set()
        formats = set()
        years = set()
        
        for match in matches:
            countries.add(match.get('venue_country', 'Unknown'))
            formats.add(match.get('format', 'Unknown'))
            
            match_date = match.get('date')
            if match_date:
                try:
                    if isinstance(match_date, str) and '-' in match_date:
                        year = match_date.split('-')[0]
                        years.add(year)
                except:
                    pass
        
        return {
            'total_matches': len(matches),
            'countries': list(countries),
            'formats': list(formats),
            'years_active': sorted(list(years)),
            'first_match': min([m.get('date', '') for m in matches if m.get('date')]),
            'latest_match': max([m.get('date', '') for m in matches if m.get('date')])
        }
    
    def _calculate_batting_bowling_stats(self, matches):
        """Calculate batting vs bowling statistics"""
        total_runs = 0
        total_wickets = 0
        total_balls = 0
        innings_count = 0
        
        run_distribution = defaultdict(int)
        
        for match in matches:
            for team_key in ['team1_batting', 'team2_batting']:
                batting_data = match.get(team_key, [])
                for innings in batting_data:
                    runs = innings.get('runs', 0)
                    balls = innings.get('balls', 0)
                    total_runs += runs
                    total_balls += balls
                    innings_count += 1
                    
                    # Categorize innings scores
                    if runs < 120:
                        run_distribution['low'] += 1
                    elif runs < 160:
                        run_distribution['medium'] += 1
                    elif runs < 200:
                        run_distribution['high'] += 1
                    else:
                        run_distribution['very_high'] += 1
            
            for team_key in ['team1_bowling', 'team2_bowling']:
                bowling_data = match.get(team_key, [])
                for innings in bowling_data:
                    total_wickets += innings.get('wickets', 0)
        
        return {
            'average_score': round(total_runs / max(innings_count, 1), 1),
            'average_wickets': round(total_wickets / max(innings_count, 1), 1),
            'average_strike_rate': round((total_runs / max(total_balls, 1)) * 100, 2),
            'run_distribution': dict(run_distribution),
            'total_innings': innings_count
        }
    
    def _calculate_toss_impact(self, matches):
        """Calculate toss impact analysis"""
        toss_wins = 0
        bat_first_wins = 0
        bowl_first_wins = 0
        total_valid_matches = 0
        
        for match in matches:
            toss_winner = match.get('toss_winner', '')
            match_winner = match.get('winner', '')
            toss_decision = match.get('toss_decision', '').lower()
            
            if toss_winner and match_winner:
                total_valid_matches += 1
                
                if toss_winner.lower() == match_winner.lower():
                    toss_wins += 1
                    
                    if 'bat' in toss_decision:
                        bat_first_wins += 1
                    elif 'bowl' in toss_decision:
                        bowl_first_wins += 1
        
        if total_valid_matches == 0:
            return {'error': 'No valid matches with toss data'}
        
        return {
            'toss_advantage_percentage': round((toss_wins / total_valid_matches) * 100, 1),
            'bat_first_advantage': round((bat_first_wins / total_valid_matches) * 100, 1),
            'bowl_first_advantage': round((bowl_first_wins / total_valid_matches) * 100, 1),
            'toss_impact_level': self._get_toss_impact_level(toss_wins / total_valid_matches),
            'total_matches_with_toss_data': total_valid_matches
        }
    
    def _get_toss_impact_level(self, percentage):
        """Determine toss impact level"""
        if percentage >= 0.65:
            return 'Very High'
        elif percentage >= 0.55:
            return 'High'
        elif percentage >= 0.45:
            return 'Medium'
        else:
            return 'Low'
    
    def _calculate_win_patterns(self, matches):
        """Calculate win margin patterns"""
        convincing_wins = 0  # 100+ runs or 7+ wickets
        comfortable_wins = 0  # 50-99 runs or 4-6 wickets
        close_wins = 0  # <50 runs or <4 wickets
        
        for match in matches:
            margin_type = match.get('win_margin_type', '').lower()
            margin_value = match.get('win_margin_value', 0)
            
            if 'run' in margin_type:
                if margin_value >= 100:
                    convincing_wins += 1
                elif margin_value >= 50:
                    comfortable_wins += 1
                else:
                    close_wins += 1
            elif 'wicket' in margin_type:
                if margin_value >= 7:
                    convincing_wins += 1
                elif margin_value >= 4:
                    comfortable_wins += 1
                else:
                    close_wins += 1
        
        total = convincing_wins + comfortable_wins + close_wins
        
        return {
            'convincing_wins': convincing_wins,
            'comfortable_wins': comfortable_wins,
            'close_wins': close_wins,
            'convincing_percentage': round((convincing_wins / max(total, 1)) * 100, 1),
            'comfortable_percentage': round((comfortable_wins / max(total, 1)) * 100, 1),
            'close_percentage': round((close_wins / max(total, 1)) * 100, 1)
        }
    
    def _calculate_format_performance(self, matches):
        """Calculate format-wise performance"""
        format_stats = defaultdict(lambda: {
            'matches': 0,
            'total_runs': 0,
            'total_wickets': 0,
            'highest_score': 0,
            'lowest_score': float('inf')
        })
        
        for match in matches:
            format_type = match.get('format', 'Unknown')
            stats = format_stats[format_type]
            stats['matches'] += 1
            
            for team_key in ['team1_batting', 'team2_batting']:
                batting_data = match.get(team_key, [])
                for innings in batting_data:
                    runs = innings.get('runs', 0)
                    stats['total_runs'] += runs
                    stats['highest_score'] = max(stats['highest_score'], runs)
                    stats['lowest_score'] = min(stats['lowest_score'], runs)
            
            for team_key in ['team1_bowling', 'team2_bowling']:
                bowling_data = match.get(team_key, [])
                for innings in bowling_data:
                    stats['total_wickets'] += innings.get('wickets', 0)
        
        result = {}
        for format_type, stats in format_stats.items():
            if stats['matches'] > 0:
                result[format_type] = {
                    'matches': stats['matches'],
                    'average_score': round(stats['total_runs'] / (stats['matches'] * 2), 1),
                    'average_wickets': round(stats['total_wickets'] / (stats['matches'] * 2), 1),
                    'highest_score': stats['highest_score'],
                    'lowest_score': stats['lowest_score'] if stats['lowest_score'] != float('inf') else 0
                }
        
        return result
    
    def _calculate_year_trends(self, matches):
        """Calculate year-wise trends"""
        year_stats = defaultdict(lambda: {
            'matches': 0,
            'total_runs': 0,
            'total_wickets': 0
        })
        
        for match in matches:
            match_date = match.get('date')
            if match_date:
                try:
                    if isinstance(match_date, str) and '-' in match_date:
                        year = match_date.split('-')[0]
                    else:
                        continue
                        
                    stats = year_stats[year]
                    stats['matches'] += 1
                    
                    for team_key in ['team1_batting', 'team2_batting']:
                        batting_data = match.get(team_key, [])
                        for innings in batting_data:
                            stats['total_runs'] += innings.get('runs', 0)
                    
                    for team_key in ['team1_bowling', 'team2_bowling']:
                        bowling_data = match.get(team_key, [])
                        for innings in bowling_data:
                            stats['total_wickets'] += innings.get('wickets', 0)
                except:
                    continue
        
        result = []
        for year, stats in sorted(year_stats.items()):
            if stats['matches'] > 0:
                result.append({
                    'year': year,
                    'matches': stats['matches'],
                    'average_score': round(stats['total_runs'] / (stats['matches'] * 2), 1),
                    'average_wickets': round(stats['total_wickets'] / (stats['matches'] * 2), 1)
                })
        
        return result
    
    def _calculate_team_performance(self, matches):
        """Calculate team performance at venue"""
        team_stats = defaultdict(lambda: {
            'matches': 0,
            'wins': 0,
            'total_runs': 0,
            'total_wickets_taken': 0
        })
        
        for match in matches:
            team1 = match.get('team1', '')
            team2 = match.get('team2', '')
            winner = match.get('winner', '')
            
            for team in [team1, team2]:
                if team:
                    stats = team_stats[team]
                    stats['matches'] += 1
                    
                    if team.lower() == winner.lower():
                        stats['wins'] += 1
            
            # Add runs and wickets data
            team1_batting = match.get('team1_batting', [])
            team2_batting = match.get('team2_batting', [])
            team1_bowling = match.get('team1_bowling', [])
            team2_bowling = match.get('team2_bowling', [])
            
            for innings in team1_batting:
                team_stats[team1]['total_runs'] += innings.get('runs', 0)
            
            for innings in team2_batting:
                team_stats[team2]['total_runs'] += innings.get('runs', 0)
            
            for innings in team1_bowling:
                team_stats[team1]['total_wickets_taken'] += innings.get('wickets', 0)
            
            for innings in team2_bowling:
                team_stats[team2]['total_wickets_taken'] += innings.get('wickets', 0)
        
        # Convert to list and calculate percentages
        result = []
        for team, stats in team_stats.items():
            if stats['matches'] >= 3:  # Only include teams with 3+ matches
                result.append({
                    'team': team,
                    'matches': stats['matches'],
                    'wins': stats['wins'],
                    'win_percentage': round((stats['wins'] / stats['matches']) * 100, 1),
                    'average_score': round(stats['total_runs'] / stats['matches'], 1),
                    'average_wickets_taken': round(stats['total_wickets_taken'] / stats['matches'], 1)
                })
        
        # Sort by win percentage
        result.sort(key=lambda x: x['win_percentage'], reverse=True)
        
        return result[:10]  # Top 10 teams
    
    def _calculate_performance_stats(self, matches):
        """Calculate detailed performance statistics"""
        batting_averages = []
        bowling_averages = []
        strike_rates = []
        economy_rates = []
        
        for match in matches:
            for team_key in ['team1_batting', 'team2_batting']:
                batting_data = match.get(team_key, [])
                for innings in batting_data:
                    runs = innings.get('runs', 0)
                    balls = innings.get('balls', 0)
                    dismissal = innings.get('dismissal')
                    
                    if dismissal:
                        batting_averages.append(runs)
                    
                    if balls > 0:
                        strike_rates.append((runs / balls) * 100)
            
            for team_key in ['team1_bowling', 'team2_bowling']:
                bowling_data = match.get(team_key, [])
                for innings in bowling_data:
                    runs_conceded = innings.get('runs_conceded', 0)
                    wickets = innings.get('wickets', 0)
                    overs = innings.get('overs', 0)
                    
                    if wickets > 0:
                        bowling_averages.append(runs_conceded / wickets)
                    
                    if overs > 0:
                        economy_rates.append(runs_conceded / overs)
        
        return {
            'batting_average': round(sum(batting_averages) / max(len(batting_averages), 1), 2),
            'bowling_average': round(sum(bowling_averages) / max(len(bowling_averages), 1), 2),
            'strike_rate': round(sum(strike_rates) / max(len(strike_rates), 1), 2),
            'economy_rate': round(sum(economy_rates) / max(len(economy_rates), 1), 2),
            'total_batting_entries': len(batting_averages),
            'total_bowling_entries': len(bowling_averages)
        }