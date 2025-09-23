import logging
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class PlayerComparisonCalculator:
    def __init__(self, data_processor):
        self.data_processor = data_processor
    
    def compare_players(self, player1, player2, filters=None):
        """Compare two players with comprehensive statistics and head-to-head analysis"""
        try:
            # Get individual player stats
            player1_stats = self.data_processor.player_stats_calculator.get_player_stats(player1, filters)
            player2_stats = self.data_processor.player_stats_calculator.get_player_stats(player2, filters)
            
            # Get head-to-head analysis
            head_to_head = self._calculate_head_to_head(player1, player2, filters)
            
            # Calculate comparison metrics
            comparison_metrics = self._calculate_comparison_metrics(player1_stats, player2_stats)
            
            return {
                'player1': {
                    'name': player1,
                    'stats': player1_stats
                },
                'player2': {
                    'name': player2,
                    'stats': player2_stats
                },
                'head_to_head': head_to_head,
                'comparison_metrics': comparison_metrics,
                'filters_applied': filters or {}
            }
            
        except Exception as e:
            logger.error(f"Error comparing players {player1} vs {player2}: {e}")
            return {'error': f'Error comparing players: {str(e)}'}
    
    def _calculate_head_to_head(self, player1, player2, filters=None):
        """Calculate head-to-head performance when players face each other"""
        try:
            # Get all matches where both players participated
            player1_matches = self.data_processor.get_player_match_data(player1, filters)
            player2_matches = self.data_processor.get_player_match_data(player2, filters)
            
            # Find common matches
            common_matches = []
            for match1 in player1_matches:
                match_id1 = match1.get('match_data', {}).get('info', {}).get('match_id', '')
                for match2 in player2_matches:
                    match_id2 = match2.get('match_data', {}).get('info', {}).get('match_id', '')
                    if match_id1 and match_id1 == match_id2:
                        common_matches.append(match1)
                        break
            
            if not common_matches:
                return {
                    'total_encounters': 0,
                    'player1_vs_player2': {'as_batsman': {}, 'as_bowler': {}},
                    'player2_vs_player1': {'as_batsman': {}, 'as_bowler': {}},
                    'match_results': {}
                }
            
            # Analyze head-to-head performance
            player1_vs_player2 = {
                'as_batsman': {
                    'runs': 0, 'balls': 0, 'dismissals': 0, 'strike_rate': 0,
                    'boundaries': 0, 'sixes': 0, 'average': 0, 'dot_balls': 0
                },
                'as_bowler': {
                    'overs': 0, 'runs_conceded': 0, 'wickets': 0, 'economy': 0,
                    'maidens': 0, 'dot_balls': 0, 'boundaries_conceded': 0, 'average': 0
                }
            }
            
            player2_vs_player1 = {
                'as_batsman': {
                    'runs': 0, 'balls': 0, 'dismissals': 0, 'strike_rate': 0,
                    'boundaries': 0, 'sixes': 0, 'average': 0, 'dot_balls': 0
                },
                'as_bowler': {
                    'overs': 0, 'runs_conceded': 0, 'wickets': 0, 'economy': 0,
                    'maidens': 0, 'dot_balls': 0, 'boundaries_conceded': 0, 'average': 0
                }
            }
            
            match_results = {'player1_wins': 0, 'player2_wins': 0, 'ties': 0}
            
            for match in common_matches:
                match_data = match.get('match_data', {})
                innings_list = match_data.get('innings', [])
                
                # Determine match result
                result = match_data.get('info', {}).get('outcome', {}).get('winner', '')
                team1 = match_data.get('info', {}).get('teams', [])[0] if match_data.get('info', {}).get('teams', []) else ''
                team2 = match_data.get('info', {}).get('teams', [])[1] if len(match_data.get('info', {}).get('teams', [])) > 1 else ''
                
                player1_team = ''
                player2_team = ''
                
                # Find which team each player belongs to
                for innings in innings_list:
                    for over in innings.get('overs', []):
                        for delivery in over.get('deliveries', []):
                            batsman = delivery.get('batsman', '')
                            bowler = delivery.get('bowler', '')
                            team = innings.get('team', '')
                            
                            if player1 in [batsman, bowler] and not player1_team:
                                player1_team = team
                            if player2 in [batsman, bowler] and not player2_team:
                                player2_team = team
                
                # Count match results
                if result == player1_team:
                    match_results['player1_wins'] += 1
                elif result == player2_team:
                    match_results['player2_wins'] += 1
                else:
                    match_results['ties'] += 1
                
                # Analyze ball-by-ball data
                for innings in innings_list:
                    for over in innings.get('overs', []):
                        for delivery in over.get('deliveries', []):
                            batsman = delivery.get('batsman', '')
                            bowler = delivery.get('bowler', '')
                            runs = delivery.get('runs', {})
                            batsman_runs = int(runs.get('batsman', 0)) if str(runs.get('batsman', 0)).isdigit() else 0
                            total_runs = int(runs.get('total', 0)) if str(runs.get('total', 0)).isdigit() else 0
                            
                            # Player1 batting vs Player2 bowling
                            if batsman == player1 and bowler == player2:
                                player1_vs_player2['as_batsman']['runs'] += batsman_runs
                                player1_vs_player2['as_batsman']['balls'] += 1
                                player2_vs_player1['as_bowler']['runs_conceded'] += total_runs
                                
                                if batsman_runs == 0:
                                    player1_vs_player2['as_batsman']['dot_balls'] += 1
                                    player2_vs_player1['as_bowler']['dot_balls'] += 1
                                elif batsman_runs == 4:
                                    player1_vs_player2['as_batsman']['boundaries'] += 1
                                    player2_vs_player1['as_bowler']['boundaries_conceded'] += 1
                                elif batsman_runs == 6:
                                    player1_vs_player2['as_batsman']['sixes'] += 1
                                    player2_vs_player1['as_bowler']['boundaries_conceded'] += 1
                                
                                # Check for dismissal
                                wicket = delivery.get('wicket', {})
                                if wicket and wicket.get('player_out') == player1:
                                    player1_vs_player2['as_batsman']['dismissals'] += 1
                                    player2_vs_player1['as_bowler']['wickets'] += 1
                            
                            # Player2 batting vs Player1 bowling
                            elif batsman == player2 and bowler == player1:
                                player2_vs_player1['as_batsman']['runs'] += batsman_runs
                                player2_vs_player1['as_batsman']['balls'] += 1
                                player1_vs_player2['as_bowler']['runs_conceded'] += total_runs
                                
                                if batsman_runs == 0:
                                    player2_vs_player1['as_batsman']['dot_balls'] += 1
                                    player1_vs_player2['as_bowler']['dot_balls'] += 1
                                elif batsman_runs == 4:
                                    player2_vs_player1['as_batsman']['boundaries'] += 1
                                    player1_vs_player2['as_bowler']['boundaries_conceded'] += 1
                                elif batsman_runs == 6:
                                    player2_vs_player1['as_batsman']['sixes'] += 1
                                    player1_vs_player2['as_bowler']['boundaries_conceded'] += 1
                                
                                # Check for dismissal
                                wicket = delivery.get('wicket', {})
                                if wicket and wicket.get('player_out') == player2:
                                    player2_vs_player1['as_batsman']['dismissals'] += 1
                                    player1_vs_player2['as_bowler']['wickets'] += 1
            
            # Calculate derived statistics
            self._calculate_derived_head_to_head_stats(player1_vs_player2)
            self._calculate_derived_head_to_head_stats(player2_vs_player1)
            
            return {
                'total_encounters': len(common_matches),
                'player1_vs_player2': player1_vs_player2,
                'player2_vs_player1': player2_vs_player1,
                'match_results': match_results
            }
            
        except Exception as e:
            logger.error(f"Error calculating head-to-head: {e}")
            return {}
    
    def _calculate_derived_head_to_head_stats(self, player_stats):
        """Calculate derived statistics like strike rate, average, economy"""
        # Batting stats
        batting = player_stats['as_batsman']
        if batting['balls'] > 0:
            batting['strike_rate'] = round((batting['runs'] / batting['balls']) * 100, 2)
        if batting['dismissals'] > 0:
            batting['average'] = round(batting['runs'] / batting['dismissals'], 2)
        else:
            batting['average'] = 'Not Out' if batting['runs'] > 0 else 0
        
        # Bowling stats
        bowling = player_stats['as_bowler']
        total_balls = batting['balls']  # Using opponent's balls faced as balls bowled
        if total_balls > 0:
            overs = total_balls // 6
            remaining_balls = total_balls % 6
            bowling['overs'] = f"{overs}.{remaining_balls}"
            bowling['economy'] = round((bowling['runs_conceded'] / total_balls) * 6, 2)
        
        if bowling['wickets'] > 0:
            bowling['average'] = round(bowling['runs_conceded'] / bowling['wickets'], 2)
        else:
            bowling['average'] = 0
    
    def _calculate_comparison_metrics(self, player1_stats, player2_stats):
        """Calculate comparison metrics between two players"""
        try:
            metrics = {
                'batting_comparison': {},
                'bowling_comparison': {},
                'overall_comparison': {}
            }
            
            # Batting comparison
            if 'batting' in player1_stats and 'batting' in player2_stats:
                p1_bat = player1_stats['batting']
                p2_bat = player2_stats['batting']
                
                metrics['batting_comparison'] = {
                    'runs': {
                        'player1': p1_bat.get('runs', 0),
                        'player2': p2_bat.get('runs', 0),
                        'better': 'player1' if p1_bat.get('runs', 0) > p2_bat.get('runs', 0) else 'player2'
                    },
                    'average': {
                        'player1': p1_bat.get('average', 0),
                        'player2': p2_bat.get('average', 0),
                        'better': 'player1' if self._safe_compare(p1_bat.get('average', 0), p2_bat.get('average', 0)) > 0 else 'player2'
                    },
                    'strike_rate': {
                        'player1': p1_bat.get('strike_rate', 0),
                        'player2': p2_bat.get('strike_rate', 0),
                        'better': 'player1' if p1_bat.get('strike_rate', 0) > p2_bat.get('strike_rate', 0) else 'player2'
                    },
                    'hundreds': {
                        'player1': p1_bat.get('hundreds', 0),
                        'player2': p2_bat.get('hundreds', 0),
                        'better': 'player1' if p1_bat.get('hundreds', 0) > p2_bat.get('hundreds', 0) else 'player2'
                    }
                }
            
            # Bowling comparison
            if 'bowling' in player1_stats and 'bowling' in player2_stats:
                p1_bowl = player1_stats['bowling']
                p2_bowl = player2_stats['bowling']
                
                metrics['bowling_comparison'] = {
                    'wickets': {
                        'player1': p1_bowl.get('wickets', 0),
                        'player2': p2_bowl.get('wickets', 0),
                        'better': 'player1' if p1_bowl.get('wickets', 0) > p2_bowl.get('wickets', 0) else 'player2'
                    },
                    'economy': {
                        'player1': p1_bowl.get('economy', 0),
                        'player2': p2_bowl.get('economy', 0),
                        'better': 'player1' if p1_bowl.get('economy', 0) < p2_bowl.get('economy', 0) and p1_bowl.get('economy', 0) > 0 else 'player2'
                    },
                    'average': {
                        'player1': p1_bowl.get('average', 0),
                        'player2': p2_bowl.get('average', 0),
                        'better': 'player1' if self._safe_compare(p1_bowl.get('average', 0), p2_bowl.get('average', 0), lower_better=True) > 0 else 'player2'
                    }
                }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating comparison metrics: {e}")
            return {}
    
    def _safe_compare(self, val1, val2, lower_better=False):
        """Safely compare two values that might be strings or numbers"""
        try:
            # Handle 'Not Out' and similar string values
            if isinstance(val1, str) and not val1.replace('.', '').isdigit():
                val1 = float('inf') if not lower_better else 0
            if isinstance(val2, str) and not val2.replace('.', '').isdigit():
                val2 = float('inf') if not lower_better else 0
            
            val1 = float(val1) if val1 != 0 else 0
            val2 = float(val2) if val2 != 0 else 0
            
            if lower_better:
                return 1 if val1 < val2 and val1 > 0 else -1
            else:
                return 1 if val1 > val2 else -1
                
        except:
            return 0