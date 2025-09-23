from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

class PlayerStatsCalculator:
    """Calculate comprehensive player statistics"""
    
    def __init__(self, data_processor):
        self.data_processor = data_processor
        
    def _to_int(self, value, default: int = 0) -> int:
        """Safely convert assorted numeric-like values to int.
        Mirrors CricketDataProcessor._to_int to avoid type errors.
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
                return int(float(s))
            return default
        except Exception:
            return default
    
    def get_player_stats(self, player_name, filters=None):
        """Get comprehensive player statistics"""
        try:
            if not player_name or player_name.strip() == '':
                return {'error': 'Player name cannot be empty'}
            
            player_matches = self.data_processor.get_player_match_data(player_name, filters)
            
            if not player_matches:
                # Check if player exists at all
                all_players = self.data_processor.get_all_players()
                if player_name not in all_players:
                    return {'error': f'Player "{player_name}" not found in the database'}
                else:
                    return {'error': f'No matches found for player "{player_name}" with the applied filters'}
            
            batting_stats = self._calculate_batting_stats(player_matches)
            bowling_stats = self._calculate_bowling_stats(player_matches)
            match_stats = self._calculate_match_stats(player_matches)
            advanced_analysis = self._calculate_advanced_analysis(player_matches, player_name)
            phase_analysis = self._calculate_phase_analysis(player_matches, player_name, filters)
            rivalry_analysis = self._calculate_rivalry_analysis(player_matches, player_name, filters)
            
            return {
                'player_name': player_name,
                'batting': batting_stats,
                'bowling': bowling_stats,
                'matches': match_stats,
                'advanced_analysis': advanced_analysis,
                'phase_analysis': phase_analysis,
                'rivalry_analysis': rivalry_analysis,
                'total_matches': len(player_matches),
                'filters_applied': filters or {}
            }
            
        except Exception as e:
            logger.error(f"Error calculating player stats for {player_name}: {e}")
            return {'error': f'Error processing player data: {str(e)}'}
    
    def _calculate_batting_stats(self, player_matches):
        """Calculate batting statistics"""
        all_batting = []
        
        for match in player_matches:
            all_batting.extend(match.get('batting_data', []))
        
        if not all_batting:
            return self._empty_batting_stats()
        
        # Basic stats
        total_runs = sum(innings['runs'] for innings in all_batting)
        total_balls = sum(innings['balls'] for innings in all_batting)
        total_fours = sum(innings['fours'] for innings in all_batting)
        total_sixes = sum(innings['sixes'] for innings in all_batting)
        total_ones = sum(innings['ones'] for innings in all_batting)
        total_twos = sum(innings['twos'] for innings in all_batting)
        total_dots = sum(innings['dots'] for innings in all_batting)
        
        # Dismissals
        dismissals = [innings for innings in all_batting if innings.get('dismissal')]
        not_outs = len(all_batting) - len(dismissals)
        
        # Calculate averages and rates
        strike_rate = (total_runs / total_balls * 100) if total_balls > 0 else 0
        average = total_runs / len(dismissals) if dismissals else total_runs
        
        # Milestones
        fifties = len([innings for innings in all_batting if 50 <= innings['runs'] < 100])
        hundreds = len([innings for innings in all_batting if 100 <= innings['runs'] < 200])
        double_hundreds = len([innings for innings in all_batting if innings['runs'] >= 200])
        
        # High score
        high_score = max(innings['runs'] for innings in all_batting) if all_batting else 0
        high_score_not_out = any(
            innings['runs'] == high_score and not innings.get('dismissal')
            for innings in all_batting
        )
        
        # Run distribution
        run_distribution = {
            'dots': total_dots,
            'ones': total_ones,
            'twos': total_twos,
            'fours': total_fours,
            'sixes': total_sixes
        }
        
        # Calculate percentages
        total_scoring_balls = total_balls
        if total_scoring_balls > 0:
            run_distribution_percentage = {
                'dots': round(total_dots / total_scoring_balls * 100, 2),
                'ones': round(total_ones / total_scoring_balls * 100, 2),
                'twos': round(total_twos / total_scoring_balls * 100, 2),
                'fours': round(total_fours / total_scoring_balls * 100, 2),
                'sixes': round(total_sixes / total_scoring_balls * 100, 2)
            }
        else:
            run_distribution_percentage = {k: 0 for k in run_distribution.keys()}
        
        # Boundary percentage
        boundary_runs = total_fours * 4 + total_sixes * 6
        boundary_percentage = (boundary_runs / total_runs * 100) if total_runs > 0 else 0
        
        return {
            'matches': len(all_batting),
            'innings': len(all_batting),
            'runs': total_runs,
            'balls': total_balls,
            'average': round(average, 2),
            'strike_rate': round(strike_rate, 2),
            'high_score': f"{high_score}{'*' if high_score_not_out else ''}",
            'not_outs': not_outs,
            'fours': total_fours,
            'sixes': total_sixes,
            'fifties': fifties,
            'hundreds': hundreds,
            'double_hundreds': double_hundreds,
            'run_distribution': run_distribution,
            'run_distribution_percentage': run_distribution_percentage,
            'boundary_percentage': round(boundary_percentage, 2)
        }
    
    def _calculate_bowling_stats(self, player_matches):
        """Calculate bowling statistics"""
        all_bowling = []
        
        for match in player_matches:
            all_bowling.extend(match.get('bowling_data', []))
        
        if not all_bowling:
            return self._empty_bowling_stats()
        
        # Basic stats
        total_overs = sum(spell['overs'] for spell in all_bowling)
        total_runs = sum(spell['runs_conceded'] for spell in all_bowling)
        total_wickets = sum(spell['wickets'] for spell in all_bowling)
        total_balls = sum(spell['balls'] for spell in all_bowling)
        total_maidens = sum(spell['maidens'] for spell in all_bowling)
        total_dots = sum(spell['dots'] for spell in all_bowling)
        
        # Calculate rates
        economy = (total_runs / total_overs) if total_overs > 0 else 0
        average = (total_runs / total_wickets) if total_wickets > 0 else 0
        strike_rate = (total_balls / total_wickets) if total_wickets > 0 else 0
        
        # Wicket hauls
        three_wickets = len([spell for spell in all_bowling if spell['wickets'] >= 3])
        five_wickets = len([spell for spell in all_bowling if spell['wickets'] >= 5])
        
        # Best bowling figures
        best_figures = max(all_bowling, key=lambda x: (x['wickets'], -x['runs_conceded']), default=None)
        best_bowling = f"{best_figures['wickets']}/{best_figures['runs_conceded']}" if best_figures else "0/0"
        
        # Wicket types analysis
        all_wicket_types = []
        for spell in all_bowling:
            all_wicket_types.extend(spell.get('wicket_types', []))
        
        wicket_types_count = Counter(all_wicket_types)
        total_wicket_types = len(all_wicket_types)
        
        wicket_types_percentage = {}
        if total_wicket_types > 0:
            for wicket_type, count in wicket_types_count.items():
                wicket_types_percentage[wicket_type] = round(count / total_wicket_types * 100, 2)
        
        # Dot ball percentage
        dot_ball_percentage = (total_dots / total_balls * 100) if total_balls > 0 else 0
        
        return {
            'matches': len(all_bowling),
            'innings': len(all_bowling),
            'overs': round(total_overs, 1),
            'runs': total_runs,
            'wickets': total_wickets,
            'average': round(average, 2),
            'economy': round(economy, 2),
            'strike_rate': round(strike_rate, 1),
            'best_bowling': best_bowling,
            'maidens': total_maidens,
            'three_wickets': three_wickets,
            'five_wickets': five_wickets,
            'wicket_types': dict(wicket_types_count),
            'wicket_types_percentage': wicket_types_percentage,
            'dot_ball_percentage': round(dot_ball_percentage, 2)
        }
    
    def _calculate_match_stats(self, player_matches):
        """Calculate match-level statistics"""
        batting_first_matches = []
        bowling_first_matches = []
        
        # Milestone win percentages
        matches_with_50_plus = []
        matches_with_3_plus_wickets = []
        
        for match in player_matches:
            match_info = match.get('match_info', {})
            
            # Determine if team batted first (use full innings list)
            innings = match.get('innings_full', []) or []
            if len(innings) >= 2:
                first_inning_team = innings[0].get('team')
                if first_inning_team == match['player_team']:
                    batting_first_matches.append(match)
                else:
                    bowling_first_matches.append(match)
            
            # Check for milestone achievements
            # Check if player scored 50+ in this match
            player_scored_50_plus = False
            for innings in match.get('batting_data', []):
                if innings['runs'] >= 50:
                    player_scored_50_plus = True
                    break
            
            if player_scored_50_plus:
                matches_with_50_plus.append(match)
            
            # Check if player took 3+ wickets in this match
            player_took_3_plus = False
            total_wickets_in_match = 0
            for innings in match.get('bowling_data', []):
                total_wickets_in_match += innings.get('wickets', 0)
            
            if total_wickets_in_match >= 3:
                player_took_3_plus = True
                matches_with_3_plus_wickets.append(match)
        
        # Calculate win percentages for milestones
        win_pct_50_plus = self._calculate_win_percentage(matches_with_50_plus)
        win_pct_3_plus_wickets = self._calculate_win_percentage(matches_with_3_plus_wickets)
        
        return {
            'batting_first': {
                'matches': len(batting_first_matches),
                'batting_stats': self._calculate_batting_stats(batting_first_matches) if batting_first_matches else self._empty_batting_stats(),
                'bowling_stats': self._calculate_bowling_stats(batting_first_matches) if batting_first_matches else self._empty_bowling_stats(),
                'win_percentage': self._calculate_win_percentage(batting_first_matches)
            },
            'bowling_first': {
                'matches': len(bowling_first_matches),
                'batting_stats': self._calculate_batting_stats(bowling_first_matches) if bowling_first_matches else self._empty_batting_stats(),
                'bowling_stats': self._calculate_bowling_stats(bowling_first_matches) if bowling_first_matches else self._empty_bowling_stats(),
                'win_percentage': self._calculate_win_percentage(bowling_first_matches)
            },
            'milestone_win_percentages': {
                'fifty_plus_runs': {
                    'matches': len(matches_with_50_plus),
                    'win_percentage': win_pct_50_plus
                },
                'three_plus_wickets': {
                    'matches': len(matches_with_3_plus_wickets), 
                    'win_percentage': win_pct_3_plus_wickets
                }
            }
        }
    
    def _empty_batting_stats(self):
        """Return empty batting stats structure"""
        return {
            'matches': 0,
            'innings': 0,
            'runs': 0,
            'balls': 0,
            'average': 0,
            'strike_rate': 0,
            'high_score': '0',
            'not_outs': 0,
            'fours': 0,
            'sixes': 0,
            'fifties': 0,
            'hundreds': 0,
            'double_hundreds': 0,
            'run_distribution': {'dots': 0, 'ones': 0, 'twos': 0, 'fours': 0, 'sixes': 0},
            'run_distribution_percentage': {'dots': 0, 'ones': 0, 'twos': 0, 'fours': 0, 'sixes': 0},
            'boundary_percentage': 0
        }
    
    def _empty_bowling_stats(self):
        """Return empty bowling stats structure"""
        return {
            'matches': 0,
            'innings': 0,
            'overs': 0,
            'runs': 0,
            'wickets': 0,
            'average': 0,
            'economy': 0,
            'strike_rate': 0,
            'best_bowling': '0/0',
            'maidens': 0,
            'three_wickets': 0,
            'five_wickets': 0,
            'wicket_types': {},
            'wicket_types_percentage': {},
            'dot_ball_percentage': 0
        }
    
    def compare_players(self, players, filters=None):
        """Compare multiple players"""
        comparison = {}
        
        for player in players:
            stats = self.get_player_stats(player, filters)
            comparison[player] = stats
        
        return comparison
    
    def get_dismissal_analysis(self, player_name, filters=None):
        """Get detailed dismissal analysis for a player"""
        player_matches = self.data_processor.get_player_match_data(player_name, filters)
        
        all_batting = []
        for match in player_matches:
            all_batting.extend(match.get('batting_data', []))
        
        dismissals = [innings for innings in all_batting if innings.get('dismissal')]
        
        if not dismissals:
            return {'error': 'No dismissal data found'}
        
        dismissal_types = Counter(innings['dismissal_type'] for innings in dismissals)
        total_dismissals = len(dismissals)
        
        dismissal_analysis = {}
        for dismissal_type, count in dismissal_types.items():
            percentage = round(count / total_dismissals * 100, 2)
            dismissal_analysis[dismissal_type] = {
                'count': count,
                'percentage': percentage
            }
        
        return {
            'total_dismissals': total_dismissals,
            'dismissal_types': dismissal_analysis,
            'dismissal_types_chart': dict(dismissal_types)
        }
    
    def get_run_distribution(self, player_name, filters=None):
        """Get detailed run distribution for a player"""
        stats = self.get_player_stats(player_name, filters)
        
        if 'error' in stats:
            return stats
        
        batting_stats = stats.get('batting', {})
        run_dist = batting_stats.get('run_distribution', {})
        run_dist_pct = batting_stats.get('run_distribution_percentage', {})
        
        return {
            'run_distribution': run_dist,
            'run_distribution_percentage': run_dist_pct,
            'total_balls': batting_stats.get('balls', 0),
            'boundary_percentage': batting_stats.get('boundary_percentage', 0)
        }
    
    def _calculate_advanced_analysis(self, player_matches, player_name):
        """Calculate advanced player analysis including batting positions, dismissal patterns, and performance metrics"""
        try:
            analysis = {
                'batting_positions': {},
                'dismissal_patterns': {},
                'performance_by_opposition': {},
                'venue_performance': {},
                'win_percentage': {},
                'scoring_pattern': {},
                'partnership_stats': {}
            }
            
            total_batting_innings = 0
            total_wins = 0
            total_games = 0
            
            for match in player_matches:
                info = match.get('match_info', {})
                innings_list = match.get('innings_full', []) or []
                
                # Track if player's team won
                result = info.get('outcome', {}).get('winner', '')
                teams_arr = info.get('teams', []) or []
                team1 = teams_arr[0] if len(teams_arr) > 0 else ''
                team2 = teams_arr[1] if len(teams_arr) > 1 else ''
                opposition = ''
                player_team = ''
                
                total_games += 1
                
                for innings in innings_list:
                    team = innings.get('team', '')
                    deliveries = innings.get('overs', [])
                    
                    # Determine if player is in this team
                    player_in_team = False
                    for over in deliveries:
                        for delivery in over.get('deliveries', []):
                            batsman = delivery.get('batter', '') or delivery.get('batsman', '')
                            non_striker = delivery.get('non_striker', '')
                            bowler = delivery.get('bowler', '')
                            
                            if player_name in [batsman, non_striker, bowler]:
                                player_in_team = True
                                player_team = team
                                opposition = team2 if team == team1 else team1
                                break
                        if player_in_team:
                            break
                    
                    if player_in_team:
                        if result == player_team:
                            total_wins += 1
                        break
                
                # Analyze batting performance
                for innings in innings_list:
                    deliveries = innings.get('overs', [])
                    
                    # Track batting position and runs
                    batsmen_order = []
                    for over in deliveries:
                        for delivery in over.get('deliveries', []):
                            batsman = delivery.get('batter', '') or delivery.get('batsman', '')
                            if batsman not in batsmen_order:
                                batsmen_order.append(batsman)
                    
                    if player_name in batsmen_order:
                        position = batsmen_order.index(player_name) + 1
                        total_batting_innings += 1
                        
                        # Batting position analysis
                        if position not in analysis['batting_positions']:
                            analysis['batting_positions'][position] = {
                                'innings': 0, 'runs': 0, 'dismissals': 0, 'not_outs': 0
                            }
                        
                        analysis['batting_positions'][position]['innings'] += 1
                        
                        # Calculate runs and dismissals for this innings
                        runs_scored = 0
                        was_dismissed = False
                        dismissal_type = None
                        
                        for over in deliveries:
                            for delivery in over.get('deliveries', []):
                                if (delivery.get('batter') or delivery.get('batsman', '')) == player_name:
                                    runs = delivery.get('runs', {}).get('batter', delivery.get('runs', {}).get('batsman', 0))
                                    runs = self._to_int(runs, 0)
                                    runs_scored += runs
                                    
                                    # Check for dismissal
                                    wickets = delivery.get('wickets', []) or []
                                    if isinstance(wickets, list):
                                        for w in wickets:
                                            if w.get('player_out') == player_name:
                                                was_dismissed = True
                                                dismissal_type = w.get('kind', 'unknown')
                                                break
                        
                        analysis['batting_positions'][position]['runs'] += runs_scored
                        
                        if was_dismissed:
                            analysis['batting_positions'][position]['dismissals'] += 1
                            
                            # Dismissal patterns
                            if dismissal_type not in analysis['dismissal_patterns']:
                                analysis['dismissal_patterns'][dismissal_type] = 0
                            analysis['dismissal_patterns'][dismissal_type] += 1
                        else:
                            analysis['batting_positions'][position]['not_outs'] += 1
                        
                        # Performance by opposition
                        if opposition:
                            if opposition not in analysis['performance_by_opposition']:
                                analysis['performance_by_opposition'][opposition] = {
                                    'matches': 0, 'runs': 0, 'innings': 0, 'dismissals': 0
                                }
                            
                            analysis['performance_by_opposition'][opposition]['matches'] += 1
                            analysis['performance_by_opposition'][opposition]['runs'] += runs_scored
                            analysis['performance_by_opposition'][opposition]['innings'] += 1
                            if was_dismissed:
                                analysis['performance_by_opposition'][opposition]['dismissals'] += 1
                        
                        # Venue performance
                        venue = info.get('venue', 'Unknown')
                        if venue not in analysis['venue_performance']:
                            analysis['venue_performance'][venue] = {
                                'matches': 0, 'runs': 0, 'innings': 0
                            }
                        
                        analysis['venue_performance'][venue]['matches'] += 1
                        analysis['venue_performance'][venue]['runs'] += runs_scored
                        analysis['venue_performance'][venue]['innings'] += 1
            
            # Calculate win percentage
            if total_games > 0:
                analysis['win_percentage'] = {
                    'wins': total_wins,
                    'total_games': total_games,
                    'percentage': round((total_wins / total_games) * 100, 2)
                }
            
            # Calculate averages for batting positions
            for pos, stats in analysis['batting_positions'].items():
                if stats['dismissals'] > 0:
                    stats['average'] = round(stats['runs'] / stats['dismissals'], 2)
                else:
                    stats['average'] = 'Not Out' if stats['innings'] > 0 else 0
                
                if stats['innings'] > 0:
                    stats['runs_per_innings'] = round(stats['runs'] / stats['innings'], 2)
            
            # Calculate averages for opposition performance
            for team, stats in analysis['performance_by_opposition'].items():
                if stats['dismissals'] > 0:
                    stats['average'] = round(stats['runs'] / stats['dismissals'], 2)
                else:
                    stats['average'] = 'Not Out' if stats['innings'] > 0 else 0
                
                if stats['innings'] > 0:
                    stats['runs_per_innings'] = round(stats['runs'] / stats['innings'], 2)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error calculating advanced analysis: {e}")
            return {}
    
    def _calculate_win_percentage(self, matches):
        """Calculate win percentage for a list of matches"""
        if not matches:
            return 0.0
        
        wins = 0
        total_matches = len(matches)
        
        for match in matches:
            match_info = match.get('match_info', {})
            outcome = match_info.get('outcome', {})
            
            # Check if the player's team won
            winner = outcome.get('winner')
            player_team = match.get('player_team')
            
            if winner and player_team and winner == player_team:
                wins += 1
        
        return round((wins / total_matches) * 100, 1) if total_matches > 0 else 0.0
    
    def _calculate_phase_analysis(self, player_matches, player_name: str, filters=None):
        """Calculate phase-wise performance for T20 and ODI matches, including per-innings averages."""
        phase_analysis = {
            't20_phases': {
                'phase1': {'runs': 0, 'wickets': 0, 'dismissals': 0, 'conceded': 0, 'batting_innings': 0, 'bowling_innings': 0},
                'phase2': {'runs': 0, 'wickets': 0, 'dismissals': 0, 'conceded': 0, 'batting_innings': 0, 'bowling_innings': 0},
                'phase3': {'runs': 0, 'wickets': 0, 'dismissals': 0, 'conceded': 0, 'batting_innings': 0, 'bowling_innings': 0},
                'phase4': {'runs': 0, 'wickets': 0, 'dismissals': 0, 'conceded': 0, 'batting_innings': 0, 'bowling_innings': 0}
            },
            'odi_phases': {
                'phase1': {'runs': 0, 'wickets': 0, 'dismissals': 0, 'conceded': 0, 'batting_innings': 0, 'bowling_innings': 0},
                'phase2': {'runs': 0, 'wickets': 0, 'dismissals': 0, 'conceded': 0, 'batting_innings': 0, 'bowling_innings': 0},
                'phase3': {'runs': 0, 'wickets': 0, 'dismissals': 0, 'conceded': 0, 'batting_innings': 0, 'bowling_innings': 0},
                'phase4': {'runs': 0, 'wickets': 0, 'dismissals': 0, 'conceded': 0, 'batting_innings': 0, 'bowling_innings': 0},
                'phase5': {'runs': 0, 'wickets': 0, 'dismissals': 0, 'conceded': 0, 'batting_innings': 0, 'bowling_innings': 0}
            }
        }

        phase_role = (filters or {}).get('phase_role')  # 'batter' | 'bowler' | None

        for match in player_matches:
            match_info = match.get('match_info', {})
            match_format = match_info.get('match_type', '')

            for innings in match.get('innings_full', []) or []:
                overs = innings.get('overs', [])
                batted_phases = set()
                bowled_phases = set()

                for over_idx, over in enumerate(overs):
                    over_number = over_idx + 1
                    deliveries = over.get('deliveries', [])

                    phase_key = None
                    if match_format == 'T20':
                        if 1 <= over_number <= 6:
                            phase_key = 'phase1'
                        elif 7 <= over_number <= 12:
                            phase_key = 'phase2'
                        elif 13 <= over_number <= 16:
                            phase_key = 'phase3'
                        elif 17 <= over_number <= 20:
                            phase_key = 'phase4'
                    elif match_format in ['ODI', 'ODM']:
                        if 1 <= over_number <= 10:
                            phase_key = 'phase1'
                        elif 11 <= over_number <= 20:
                            phase_key = 'phase2'
                        elif 21 <= over_number <= 30:
                            phase_key = 'phase3'
                        elif 31 <= over_number <= 40:
                            phase_key = 'phase4'
                        elif 41 <= over_number <= 50:
                            phase_key = 'phase5'
                    if not phase_key:
                        continue

                    # Track whether player batted/bowled in this phase at least once to count innings for averages
                    batted_in_phase = False
                    bowled_in_phase = False
                    balls_faced_in_phase = 0
                    for delivery in deliveries:
                        batter = delivery.get('batter', '')
                        bowler = delivery.get('bowler', '')
                        runs = delivery.get('runs', {})
                        batter_runs = self._to_int(runs.get('batter', 0), 0)
                        total_runs = self._to_int(runs.get('total', 0), 0)
                        wickets = delivery.get('wickets', []) or []

                        if batter == player_name and phase_role in [None, '', 'batter']:
                            # Batting contributions
                            target = phase_analysis['t20_phases' if match_format == 'T20' else 'odi_phases'][phase_key]
                            target['runs'] += batter_runs
                            balls_faced_in_phase += 1
                            batted_in_phase = True
                            # Dismissal
                            for w in wickets:
                                if w.get('player_out') == player_name:
                                    target['dismissals'] += 1
                                    break
                        if bowler == player_name and phase_role in [None, '', 'bowler']:
                            # Bowling contributions
                            target = phase_analysis['t20_phases' if match_format == 'T20' else 'odi_phases'][phase_key]
                            target['conceded'] += total_runs
                            bowled_in_phase = True
                            for w in wickets:
                                kind = w.get('kind', '')
                                if kind not in ['run out', 'retired hurt', 'retired out']:
                                    target['wickets'] += 1
                    # After deliveries loop for this over/phase, update innings counters and balls
                    if batted_in_phase and phase_role in [None, '', 'batter']:
                        target = phase_analysis['t20_phases' if match_format == 'T20' else 'odi_phases'][phase_key]
                        # Count batting innings once per phase per match
                        if phase_key not in batted_phases:
                            target['batting_innings'] += 1
                            batted_phases.add(phase_key)
                        target['balls'] = target.get('balls', 0) + balls_faced_in_phase
                    if bowled_in_phase and phase_role in [None, '', 'bowler']:
                        if phase_key not in bowled_phases:
                            target = phase_analysis['t20_phases' if match_format == 'T20' else 'odi_phases'][phase_key]
                            target['bowling_innings'] += 1
                            bowled_phases.add(phase_key)
        
        # Compute strike rates per phase where balls > 0
        def compute_sr(phases_dict):
            for pk, ph in phases_dict.items():
                balls = ph.get('balls', 0) or 0
                runs = ph.get('runs', 0) or 0
                ph['strike_rate'] = round((runs / balls) * 100, 1) if balls > 0 else 0.0

        compute_sr(phase_analysis['t20_phases'])
        compute_sr(phase_analysis['odi_phases'])

        return phase_analysis
    
    def _calculate_rivalry_analysis(self, player_matches, player_name, filters=None):
        """Calculate player's performance against individual opponents (player vs player).

        Batting side: aggregate runs scored off each bowler and dismissals by bowlers.
        Bowling side: aggregate runs conceded to each batter and wickets taken of batters.
        """
        try:
            rivalry_stats = {
                # Batting perspective -> vs bowlers
                'runs_against': defaultdict(lambda: {'runs': 0, 'matches': 0, 'innings': 0}),  # key: bowler
                'dismissals_by': defaultdict(lambda: {'dismissals': 0, 'matches': 0, 'innings': 0}),  # key: bowler
                # Bowling perspective -> vs batters
                'runs_conceded_to': defaultdict(lambda: {'runs': 0, 'matches': 0, 'overs': 0}),  # key: batter
                'wickets_against': defaultdict(lambda: {'wickets': 0, 'matches': 0, 'overs': 0})  # key: batter
            }
            
            for match in player_matches:
                innings_list = match.get('innings_full', []) or []
                # Use sets to ensure we count match once per opponent player for 'matches'
                batting_opponents_in_match = set()
                bowling_opponents_in_match = set()
                
                for innings in innings_list:
                    overs = innings.get('overs', [])
                    
                    for over in overs:
                        deliveries = over.get('deliveries', [])
                        
                        for delivery in deliveries:
                            batter = delivery.get('batter', '') or delivery.get('batsman', '')
                            bowler = delivery.get('bowler', '')
                            runs = delivery.get('runs', {})
                            wickets = delivery.get('wickets', []) or []
                            
                            # Batting perspective: player as batter vs bowler
                            if batter == player_name and bowler:
                                batter_runs = self._to_int(runs.get('batter', 0), 0)
                                rivalry_stats['runs_against'][bowler]['runs'] += batter_runs
                                batting_opponents_in_match.add(bowler)
                                # Dismissal by specific bowler
                                for w in wickets:
                                    if w.get('player_out') == player_name:
                                        # Credit dismissal to the bowler if dismissal kind is credited to bowler
                                        kind = w.get('kind', '')
                                        if kind not in ['run out', 'retired hurt', 'retired out']:
                                            rivalry_stats['dismissals_by'][bowler]['dismissals'] += 1
                                            batting_opponents_in_match.add(bowler)

                            # Bowling perspective: player as bowler vs batter
                            if bowler == player_name and batter:
                                total_runs = self._to_int(runs.get('total', 0), 0)
                                rivalry_stats['runs_conceded_to'][batter]['runs'] += total_runs
                                bowling_opponents_in_match.add(batter)
                                # Wicket taken of specific batter
                                for w in wickets:
                                    kind = w.get('kind', '')
                                    player_out = w.get('player_out', '')
                                    if kind not in ['run out', 'retired hurt', 'retired out'] and player_out:
                                        if player_out == batter:
                                            rivalry_stats['wickets_against'][batter]['wickets'] += 1
                                            bowling_opponents_in_match.add(batter)

                # Increment match counters once per opponent player encountered in this match
                for opp in batting_opponents_in_match:
                    rivalry_stats['runs_against'][opp]['matches'] += 1
                    rivalry_stats['dismissals_by'][opp]['matches'] += 1
                for opp in bowling_opponents_in_match:
                    rivalry_stats['runs_conceded_to'][opp]['matches'] += 1
                    rivalry_stats['wickets_against'][opp]['matches'] += 1
            
            # Convert to top 5 lists
            def get_top_5(stats_dict, sort_key):
                return sorted(
                    [(opponent, stats) for opponent, stats in stats_dict.items() if stats['matches'] > 0],
                    key=lambda x: x[1][sort_key],
                    reverse=True
                )[:5]
            
            rivalry_analysis = {
                'most_runs_against': [
                    {
                        'opponent': opponent,
                        'runs': stats['runs'],
                        'matches': stats['matches']
                    }
                    for opponent, stats in get_top_5(rivalry_stats['runs_against'], 'runs')
                ],
                'most_wickets_against': [
                    {
                        'opponent': opponent,
                        'wickets': stats['wickets'],
                        'matches': stats['matches']
                    }
                    for opponent, stats in get_top_5(rivalry_stats['wickets_against'], 'wickets')
                ],
                'most_runs_conceded_to': [
                    {
                        'opponent': opponent,
                        'runs': stats['runs'],
                        'matches': stats['matches']
                    }
                    for opponent, stats in get_top_5(rivalry_stats['runs_conceded_to'], 'runs')
                ],
                'most_dismissals_by': [
                    {
                        'opponent': opponent,
                        'dismissals': stats['dismissals'],
                        'matches': stats['matches']
                    }
                    for opponent, stats in get_top_5(rivalry_stats['dismissals_by'], 'dismissals')
                ]
            }
            
            return rivalry_analysis
            
        except Exception as e:
            logger.error(f"Error calculating rivalry analysis for {player_name}: {e}")
            return {
                    'most_runs_against': [],
                    'most_wickets_against': [],
                    'most_runs_conceded_to': [],
                    'most_dismissals_by': []
                }