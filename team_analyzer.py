import numpy as np
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

class TeamAnalyzer:
    """Analyze team statistics and performance"""
    
    def __init__(self, data_processor):
        self.data_processor = data_processor
    
    def get_team_stats(self, team_name, filters=None):
        """Get comprehensive team statistics"""
        try:
            team_matches = self.data_processor.get_team_match_data(team_name, filters)
            
            if not team_matches:
                return {'error': f'No data found for team {team_name}'}
            
            general_stats = self._calculate_general_team_stats(team_matches)
            batting_stats = self._calculate_team_batting_stats(team_matches)
            bowling_stats = self._calculate_team_bowling_stats(team_matches)
            performance_stats = self._calculate_performance_stats(team_matches)
            opponent_analysis = self._calculate_opponent_analysis(team_matches)
            phase_averages = self._calculate_phase_averages(team_matches, team_name)
            
            return {
                'team_name': team_name,
                'general': general_stats,
                'batting': batting_stats,
                'bowling': bowling_stats,
                'performance': performance_stats,
                'opponents': opponent_analysis,
                'phase_averages': phase_averages,
                'total_matches': len(team_matches)
            }
            
        except Exception as e:
            logger.error(f"Error calculating team stats for {team_name}: {e}")
            return {'error': str(e)}
    
    def _calculate_general_team_stats(self, team_matches):
        """Calculate general team statistics"""
        total_matches = len(team_matches)
        wins = len([m for m in team_matches if m['result'] == 'win'])
        losses = len([m for m in team_matches if m['result'] == 'loss'])
        draws = len([m for m in team_matches if m['result'] == 'draw'])
        
        win_percentage = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        # Toss statistics
        toss_wins = len([m for m in team_matches if m['won_toss']])
        toss_win_percentage = (toss_wins / total_matches * 100) if total_matches > 0 else 0
        
        # Batting first vs bowling first
        batting_first_matches = [m for m in team_matches if m['batting_first'] == True]
        bowling_first_matches = [m for m in team_matches if m['batting_first'] == False]
        
        batting_first_wins = len([m for m in batting_first_matches if m['result'] == 'win'])
        bowling_first_wins = len([m for m in bowling_first_matches if m['result'] == 'win'])
        
        batting_first_win_pct = (batting_first_wins / len(batting_first_matches) * 100) if batting_first_matches else 0
        bowling_first_win_pct = (bowling_first_wins / len(bowling_first_matches) * 100) if bowling_first_matches else 0
        
        # Format analysis
        format_stats = defaultdict(lambda: {'matches': 0, 'wins': 0})
        for match in team_matches:
            match_type = match['match_info'].get('match_type', 'Unknown')
            format_stats[match_type]['matches'] += 1
            if match['result'] == 'win':
                format_stats[match_type]['wins'] += 1
        
        # Calculate win percentages for each format
        for format_type, stats in format_stats.items():
            if stats['matches'] > 0:
                stats['win_percentage'] = round(stats['wins'] / stats['matches'] * 100, 2)
            else:
                stats['win_percentage'] = 0
        
        return {
            'total_matches': total_matches,
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'win_percentage': round(win_percentage, 2),
            'toss_wins': toss_wins,
            'toss_win_percentage': round(toss_win_percentage, 2),
            'batting_first': {
                'matches': len(batting_first_matches),
                'wins': batting_first_wins,
                'win_percentage': round(batting_first_win_pct, 2)
            },
            'bowling_first': {
                'matches': len(bowling_first_matches),
                'wins': bowling_first_wins,
                'win_percentage': round(bowling_first_win_pct, 2)
            },
            'format_performance': dict(format_stats)
        }
    
    def _calculate_team_batting_stats(self, team_matches):
        """Calculate team batting statistics"""
        all_scores = []
        high_scores = []
        low_scores = []
        
        for match in team_matches:
            if match['team_score']:
                runs = match['team_score']['runs']
                all_scores.append(runs)
                
                if runs >= 300:
                    high_scores.append(runs)
                elif runs <= 150:
                    low_scores.append(runs)
        
        if not all_scores:
            return self._empty_batting_stats()
        
        # Calculate detailed statistics from match data
        total_boundaries = {'fours': 0, 'sixes': 0}
        total_balls = 0
        
        # This would require deeper analysis of individual innings
        # For now, providing aggregate statistics
        
        return {
            'matches': len(all_scores),
            'total_runs': sum(all_scores),
            'average_score': round(np.mean(all_scores), 2),
            'highest_score': max(all_scores),
            'lowest_score': min(all_scores),
            'scores_300_plus': len(high_scores),
            'scores_150_minus': len(low_scores),
            'total_boundaries': total_boundaries
        }
    
    def _calculate_team_bowling_stats(self, team_matches):
        """Calculate team bowling statistics"""
        opponent_scores = []
        
        for match in team_matches:
            if match['opponent_score']:
                runs = match['opponent_score']['runs']
                opponent_scores.append(runs)
        
        if not opponent_scores:
            return self._empty_bowling_stats()
        
        return {
            'matches': len(opponent_scores),
            'runs_conceded': sum(opponent_scores),
            'average_runs_conceded': round(np.mean(opponent_scores), 2),
            'best_bowling_performance': min(opponent_scores),
            'worst_bowling_performance': max(opponent_scores),
            'restricted_under_200': len([s for s in opponent_scores if s < 200]),
            'conceded_300_plus': len([s for s in opponent_scores if s >= 300])
        }
    
    def _calculate_performance_stats(self, team_matches):
        """Calculate performance-based statistics"""
        home_matches = []
        away_matches = []
        neutral_matches = []
        
        # This would require venue classification as home/away
        # For now, we'll analyze by venue frequency
        
        venue_performance = defaultdict(lambda: {'matches': 0, 'wins': 0})
        
        for match in team_matches:
            venue = match['match_info'].get('venue', 'Unknown')
            venue_performance[venue]['matches'] += 1
            if match['result'] == 'win':
                venue_performance[venue]['wins'] += 1
        
        # Calculate win percentages for venues
        for venue, stats in venue_performance.items():
            if stats['matches'] > 0:
                stats['win_percentage'] = round(stats['wins'] / stats['matches'] * 100, 2)
            else:
                stats['win_percentage'] = 0
        
        # Recent form (last 10 matches)
        recent_matches = team_matches[-10:] if len(team_matches) >= 10 else team_matches
        recent_wins = len([m for m in recent_matches if m['result'] == 'win'])
        recent_form = round(recent_wins / len(recent_matches) * 100, 2) if recent_matches else 0
        
        # Win margins analysis
        win_margins_runs = []
        win_margins_wickets = []
        
        for match in team_matches:
            if match['result'] == 'win':
                outcome = match['match_info'].get('outcome', {})
                if 'by' in outcome:
                    by = outcome['by']
                    if 'runs' in by:
                        win_margins_runs.append(int(by['runs']))
                    elif 'wickets' in by:
                        win_margins_wickets.append(int(by['wickets']))
        
        return {
            'venue_performance': dict(venue_performance),
            'recent_form': {
                'matches': len(recent_matches),
                'wins': recent_wins,
                'win_percentage': recent_form
            },
            'win_margins': {
                'by_runs': {
                    'count': len(win_margins_runs),
                    'average': round(np.mean(win_margins_runs), 2) if win_margins_runs else 0,
                    'highest': max(win_margins_runs) if win_margins_runs else 0
                },
                'by_wickets': {
                    'count': len(win_margins_wickets),
                    'average': round(np.mean(win_margins_wickets), 2) if win_margins_wickets else 0,
                    'highest': max(win_margins_wickets) if win_margins_wickets else 0
                }
            }
        }
    
    def _calculate_opponent_analysis(self, team_matches):
        """Analyze performance against different opponents"""
        opponent_records = defaultdict(lambda: {'matches': 0, 'wins': 0, 'losses': 0})
        
        for match in team_matches:
            opponent = match['opponent']
            if opponent:
                opponent_records[opponent]['matches'] += 1
                if match['result'] == 'win':
                    opponent_records[opponent]['wins'] += 1
                elif match['result'] == 'loss':
                    opponent_records[opponent]['losses'] += 1
        
        # Calculate win percentages against each opponent
        for opponent, record in opponent_records.items():
            total_decided = record['wins'] + record['losses']
            if total_decided > 0:
                record['win_percentage'] = round(record['wins'] / total_decided * 100, 2)
            else:
                record['win_percentage'] = 0
        
        # Sort by number of matches played
        sorted_opponents = sorted(opponent_records.items(), key=lambda x: x[1]['matches'], reverse=True)
        
        return dict(sorted_opponents)

    def _calculate_phase_averages(self, team_matches, team_name):
        """Compute phase-wise averages for T20/T20I and ODI using ball-by-ball innings_full.
        Metrics per phase per innings:
          - avg_score: team's runs scored in that phase
          - avg_wkts_taken: wickets taken by team while bowling in that phase
          - avg_wkts_given: wickets lost by team while batting in that phase
        """
        def accum_bat(stats, phase_key, runs, wkts_given):
            s = stats.setdefault(phase_key, {
                'bat_inns': 0, 'bat_runs': 0, 'bat_wkts_given': 0,
                'bowl_inns': 0, 'bowl_wkts_taken': 0
            })
            s['bat_inns'] += 1
            s['bat_runs'] += runs
            s['bat_wkts_given'] += wkts_given

        def accum_bowl(stats, phase_key, wkts_taken):
            s = stats.setdefault(phase_key, {
                'bat_inns': 0, 'bat_runs': 0, 'bat_wkts_given': 0,
                'bowl_inns': 0, 'bowl_wkts_taken': 0
            })
            s['bowl_inns'] += 1
            s['bowl_wkts_taken'] += wkts_taken

        def finalize(stats):
            out = {}
            for k, s in stats.items():
                bat_inns = max(1, s['bat_inns'])
                bowl_inns = max(1, s['bowl_inns'])
                out[k] = {
                    'avg_score': round(s['bat_runs'] / bat_inns, 2) if s['bat_inns'] else 0,
                    'avg_wkts_taken': round(s['bowl_wkts_taken'] / bowl_inns, 2) if s['bowl_inns'] else 0,
                    'avg_wkts_given': round(s['bat_wkts_given'] / bat_inns, 2) if s['bat_inns'] else 0
                }
            return out

        t20_stats = {}
        odi_stats = {}

        for match in team_matches:
            info = match['match_info']
            match_type = info.get('match_type', '')
            innings_full = match.get('innings_full', [])
            # Compute phases
            if match_type in ('T20', 'T20I'):
                phase_bounds = [(1,6,'Powerplay (1-6)'), (7,15,'Middle (7-15)'), (16,20,'Death (16-20)')]
                target_stats = t20_stats
            elif match_type == 'ODI':
                phase_bounds = [(1,10,'Phase 1 (1-10)'), (11,35,'Phase 2 (11-35)'), (36,50,'Phase 3 (36-50)')]
                target_stats = odi_stats
            else:
                continue

            for inning in innings_full:
                is_team_batting = inning.get('team') == team_name
                overs = inning.get('overs', [])
                # Precompute wickets per delivery to know phase wickets
                # We'll assume over number increments by 1 per entry; deliveries are sequential
                # Aggregate by over number
                for start, end, label in phase_bounds:
                    runs_phase = 0
                    wkts_phase = 0
                    for ov_idx, over in enumerate(overs, start=1):
                        if ov_idx < start or ov_idx > end:
                            continue
                        for delivery in over.get('deliveries', []):
                            runs_phase += int(delivery.get('runs', {}).get('total', 0))
                            if 'wickets' in delivery:
                                wkts_phase += len(delivery['wickets'])
                    if is_team_batting:
                        accum_bat(target_stats, label, runs_phase, wkts_phase)
                    else:
                        accum_bowl(target_stats, label, wkts_phase)

        return {
            't20': finalize(t20_stats),
            'odi': finalize(odi_stats)
        }
    
    def _empty_batting_stats(self):
        """Return empty batting stats structure"""
        return {
            'matches': 0,
            'total_runs': 0,
            'average_score': 0,
            'highest_score': 0,
            'lowest_score': 0,
            'scores_300_plus': 0,
            'scores_150_minus': 0,
            'total_boundaries': {'fours': 0, 'sixes': 0}
        }
    
    def _empty_bowling_stats(self):
        """Return empty bowling stats structure"""
        return {
            'matches': 0,
            'runs_conceded': 0,
            'average_runs_conceded': 0,
            'best_bowling_performance': 0,
            'worst_bowling_performance': 0,
            'restricted_under_200': 0,
            'conceded_300_plus': 0
        }
    
    def compare_teams(self, teams, filters=None):
        """Compare multiple teams"""
        comparison = {}
        
        for team in teams:
            stats = self.get_team_stats(team, filters)
            comparison[team] = stats
        
        # Add head-to-head comparison if exactly 2 teams
        if len(teams) == 2:
            h2h_stats = self._get_head_to_head_stats(teams[0], teams[1], filters)
            comparison['head_to_head'] = h2h_stats
        
        return comparison
    
    def _get_head_to_head_stats(self, team1, team2, filters=None):
        """Get head-to-head statistics between two teams"""
        team1_matches = self.data_processor.get_team_match_data(team1, filters)
        
        # Filter for matches between these two teams
        h2h_matches = [
            match for match in team1_matches 
            if match['opponent'] == team2
        ]
        
        if not h2h_matches:
            return {'error': f'No head-to-head matches found between {team1} and {team2}'}
        
        team1_wins = len([m for m in h2h_matches if m['result'] == 'win'])
        team2_wins = len([m for m in h2h_matches if m['result'] == 'loss'])
        draws = len([m for m in h2h_matches if m['result'] == 'draw'])
        
        total_decided = team1_wins + team2_wins
        team1_win_pct = (team1_wins / total_decided * 100) if total_decided > 0 else 0
        
        return {
            'total_matches': len(h2h_matches),
            team1: {
                'wins': team1_wins,
                'win_percentage': round(team1_win_pct, 2)
            },
            team2: {
                'wins': team2_wins,
                'win_percentage': round(100 - team1_win_pct, 2)
            },
            'draws': draws,
            'recent_form': self._get_recent_h2h_form(h2h_matches)
        }
    
    def _get_recent_h2h_form(self, h2h_matches):
        """Get recent head-to-head form (last 5 matches)"""
        recent_matches = h2h_matches[-5:] if len(h2h_matches) >= 5 else h2h_matches
        
        form = []
        for match in recent_matches:
            if match['result'] == 'win':
                form.append('W')
            elif match['result'] == 'loss':
                form.append('L')
            else:
                form.append('D')
        
        return form