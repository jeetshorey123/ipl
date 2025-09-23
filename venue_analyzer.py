from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

class VenueAnalyzer:
    """Analyze venue statistics and characteristics"""
    
    def __init__(self, data_processor):
        self.data_processor = data_processor
    
    def get_venue_stats(self, venue_name, filters=None):
        """Get comprehensive venue statistics"""
        try:
            venue_matches = self.data_processor.get_venue_matches(venue_name, filters)
            
            if not venue_matches:
                return {'error': f'No data found for venue {venue_name}'}
            
            general_stats = self._calculate_general_stats(venue_matches)
            batting_stats = self._calculate_venue_batting_stats(venue_matches)
            bowling_stats = self._calculate_venue_bowling_stats(venue_matches)
            toss_stats = self._calculate_toss_stats(venue_matches)
            phase_stats = self._calculate_phase_stats(venue_matches)
            team_stats = self._calculate_team_performance(venue_matches)
            
            return {
                'venue_name': venue_name,
                'general': general_stats,
                'batting': batting_stats,
                'bowling': bowling_stats,
                'toss': toss_stats,
                'phases': phase_stats,
                'teams': team_stats,
                'total_matches': len(venue_matches)
            }
            
        except Exception as e:
            logger.error(f"Error calculating venue stats for {venue_name}: {e}")
            return {'error': str(e)}
    
    def _calculate_general_stats(self, venue_matches):
        """Calculate general venue statistics"""
        total_matches = len(venue_matches)
        
        # Match formats
        formats = Counter(match['info'].get('match_type', 'Unknown') for match in venue_matches)
        
        # Teams played
        all_teams = set()
        for match in venue_matches:
            teams = match['info'].get('teams', [])
            all_teams.update(teams)
        
        # Countries/cities
        cities = Counter(match['info'].get('city', 'Unknown') for match in venue_matches)
        
        # Date range
        dates = []
        for match in venue_matches:
            match_dates = match['info'].get('dates', [])
            if match_dates:
                dates.append(match_dates[0])
        
        date_range = {
            'first_match': min(dates) if dates else None,
            'last_match': max(dates) if dates else None
        }
        
        # Win by margin analysis
        wins_by_runs = []
        wins_by_wickets = []
        
        for match in venue_matches:
            outcome = match['info'].get('outcome', {})
            if 'by' in outcome:
                by = outcome['by']
                if 'runs' in by:
                    wins_by_runs.append(int(by['runs']))
                elif 'wickets' in by:
                    wins_by_wickets.append(int(by['wickets']))
        
        return {
            'total_matches': total_matches,
            'formats': dict(formats),
            'teams_played': len(all_teams),
            'cities': dict(cities),
            'date_range': date_range,
            'avg_win_margin_runs': round(sum(wins_by_runs)/len(wins_by_runs), 2) if wins_by_runs else 0,
            'avg_win_margin_wickets': round(sum(wins_by_wickets)/len(wins_by_wickets), 2) if wins_by_wickets else 0
        }
    
    def _calculate_venue_batting_stats(self, venue_matches):
        """Calculate batting statistics at the venue"""
        all_scores = []
        all_run_rates = []
        high_scores = []
        low_scores = []
        
        for match in venue_matches:
            innings = match.get('innings', [])
            
            for inning in innings:
                score = self.data_processor._calculate_team_score(inning)
                total_runs = score['runs']
                total_overs = score['overs']
                
                all_scores.append(total_runs)
                
                if total_overs > 0:
                    run_rate = total_runs / total_overs
                    all_run_rates.append(run_rate)
                
                # Track high and low scores
                if total_runs >= 300:
                    high_scores.append(total_runs)
                elif total_runs <= 150:
                    low_scores.append(total_runs)
        
        # Boundary analysis
        all_boundaries = {'fours': 0, 'sixes': 0}
        total_balls = 0
        
        for match in venue_matches:
            innings = match.get('innings', [])
            
            for inning in innings:
                overs = inning.get('overs', [])
                
                for over in overs:
                    deliveries = over.get('deliveries', [])
                    
                    for delivery in deliveries:
                        total_balls += 1
                        runs = int(delivery.get('runs', {}).get('batter', 0))
                        
                        if runs == 4:
                            all_boundaries['fours'] += 1
                        elif runs == 6:
                            all_boundaries['sixes'] += 1
        
        boundary_percentage = ((all_boundaries['fours'] + all_boundaries['sixes']) / total_balls * 100) if total_balls > 0 else 0
        
        return {
            'average_score': round(sum(all_scores)/len(all_scores), 2) if all_scores else 0,
            'highest_score': max(all_scores) if all_scores else 0,
            'lowest_score': min(all_scores) if all_scores else 0,
            'average_run_rate': round(sum(all_run_rates)/len(all_run_rates), 2) if all_run_rates else 0,
            'high_scores_300_plus': len(high_scores),
            'low_scores_150_minus': len(low_scores),
            'total_boundaries': all_boundaries,
            'boundary_percentage': round(boundary_percentage, 2)
        }
    
    def _calculate_venue_bowling_stats(self, venue_matches):
        """Calculate bowling statistics at the venue"""
        total_wickets = 0
        total_runs = 0
        total_overs = 0
        wicket_types = Counter()
        innings_count = 0
        
        for match in venue_matches:
            innings = match.get('innings', [])
            
            for inning in innings:
                innings_count += 1
                overs = inning.get('overs', [])
                
                for over in overs:
                    total_overs += 1
                    deliveries = over.get('deliveries', [])
                    
                    for delivery in deliveries:
                        total_runs += int(delivery.get('runs', {}).get('total', 0))
                        
                        if 'wickets' in delivery:
                            for wicket in delivery['wickets']:
                                total_wickets += 1
                                wicket_type = wicket.get('kind', 'unknown')
                                wicket_types[wicket_type] += 1
        
        # Calculate bowling averages
        bowling_average = (total_runs / total_wickets) if total_wickets > 0 else 0
        economy_rate = (total_runs / total_overs) if total_overs > 0 else 0
        
        # Wicket type percentages
        wicket_type_percentages = {}
        if total_wickets > 0:
            for wicket_type, count in wicket_types.items():
                wicket_type_percentages[wicket_type] = round(count / total_wickets * 100, 2)
        
        wickets_per_innings = (total_wickets / max(innings_count,1)) if innings_count>0 else 0
        return {
            'total_wickets': total_wickets,
            'bowling_average': round(bowling_average, 2),
            'economy_rate': round(economy_rate, 2),
            'wicket_types': dict(wicket_types),
            'wicket_type_percentages': wicket_type_percentages,
            'wickets_per_match': round(total_wickets / len(venue_matches), 2) if venue_matches else 0,
            'wickets_per_innings': round(wickets_per_innings,2)
        }
    
    def _calculate_toss_stats(self, venue_matches):
        """Calculate toss-related statistics"""
        toss_decisions = Counter()
        toss_win_outcomes = {'won': 0, 'lost': 0}
        bat_first_wins = 0
        bowl_first_wins = 0
        
        for match in venue_matches:
            toss = match['info'].get('toss', {})
            outcome = match['info'].get('outcome', {})
            
            # Toss decision
            decision = toss.get('decision', 'unknown')
            toss_decisions[decision] += 1
            
            # Toss winner vs match winner
            toss_winner = toss.get('winner')
            match_winner = outcome.get('winner')
            
            if toss_winner and match_winner:
                if toss_winner == match_winner:
                    toss_win_outcomes['won'] += 1
                else:
                    toss_win_outcomes['lost'] += 1
            
            # First innings advantage
            if match_winner and len(match.get('innings', [])) >= 2:
                first_innings_team = match['innings'][0].get('team')
                
                if first_innings_team == match_winner:
                    bat_first_wins += 1
                else:
                    bowl_first_wins += 1
        
        total_toss_results = toss_win_outcomes['won'] + toss_win_outcomes['lost']
        toss_advantage = (toss_win_outcomes['won'] / total_toss_results * 100) if total_toss_results > 0 else 50
        
        total_first_innings = bat_first_wins + bowl_first_wins
        bat_first_advantage = (bat_first_wins / total_first_innings * 100) if total_first_innings > 0 else 50
        
        return {
            'toss_decisions': dict(toss_decisions),
            'toss_advantage_percentage': round(toss_advantage, 2),
            'bat_first_win_percentage': round(bat_first_advantage, 2),
            'bowl_first_win_percentage': round(100 - bat_first_advantage, 2)
        }

    def _calculate_phase_stats(self, venue_matches):
        """Compute phase-wise average scores and strike rates for T20 and ODI."""
        phases = {
            'T20': {'1-6': {'runs':0,'balls':0,'innings':0}, '7-15': {'runs':0,'balls':0,'innings':0}, '16-20': {'runs':0,'balls':0,'innings':0}},
            'ODI': {'1-10': {'runs':0,'balls':0,'innings':0}, '11-35': {'runs':0,'balls':0,'innings':0}, '36-50': {'runs':0,'balls':0,'innings':0}}
        }
        for match in venue_matches:
            fmt = match.get('info', {}).get('match_type')
            if fmt not in phases:
                continue
            innings = match.get('innings', [])
            for inning in innings:
                overs = inning.get('overs', [])
                # mark that this innings contributes
                if fmt == 'T20':
                    ranges = [(1,6,'1-6'),(7,15,'7-15'),(16,20,'16-20')]
                else:
                    ranges = [(1,10,'1-10'),(11,35,'11-35'),(36,50,'36-50')]
                for idx, over in enumerate(overs, start=1):
                    total_balls = len(over.get('deliveries', []))
                    total_runs = sum(int(d.get('runs', {}).get('total', 0)) for d in over.get('deliveries', []))
                    for lo, hi, key in ranges:
                        if lo <= idx <= hi:
                            phases[fmt][key]['runs'] += total_runs
                            phases[fmt][key]['balls'] += total_balls
                # count innings once per format bucket
                for _,_,key in ([(1,6,'1-6'),(7,15,'7-15'),(16,20,'16-20')] if fmt=='T20' else [(1,10,'1-10'),(11,35,'11-35'),(36,50,'36-50')]):
                    phases[fmt][key]['innings'] += 1
        # Convert to averages
        result = {}
        for fmt, buckets in phases.items():
            result[fmt] = {}
            for key, rec in buckets.items():
                avg_runs = round((rec['runs']/max(rec['innings'],1)),2) if rec['innings'] else 0
                sr = round((rec['runs']/max(rec['balls'],1))*100,2) if rec['balls'] else 0
                result[fmt][key] = {'avg_runs': avg_runs, 'strike_rate': sr}
        return result
    
    def _calculate_team_performance(self, venue_matches):
        """Calculate team performance at the venue"""
        team_records = defaultdict(lambda: {'matches': 0, 'wins': 0, 'losses': 0})
        
        for match in venue_matches:
            teams = match['info'].get('teams', [])
            winner = match['info'].get('outcome', {}).get('winner')
            
            for team in teams:
                team_records[team]['matches'] += 1
                
                if winner == team:
                    team_records[team]['wins'] += 1
                elif winner and winner != team:
                    team_records[team]['losses'] += 1
        
        # Calculate win percentages
        for team, record in team_records.items():
            total_decided = record['wins'] + record['losses']
            if total_decided > 0:
                record['win_percentage'] = round(record['wins'] / total_decided * 100, 2)
            else:
                record['win_percentage'] = 0
        
        # Sort by matches played
        sorted_teams = sorted(team_records.items(), key=lambda x: x[1]['matches'], reverse=True)
        
        return dict(sorted_teams[:10])  # Return top 10 teams by matches played
    
    def get_all_venues(self):
        """Get list of all venues"""
        return self.data_processor.get_all_venues()
    
    def compare_venues(self, venues, filters=None):
        """Compare multiple venues"""
        comparison = {}
        
        for venue in venues:
            stats = self.get_venue_stats(venue, filters)
            comparison[venue] = stats
        
        return comparison