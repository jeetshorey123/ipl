import numpy as np
from collections import defaultdict
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import logging
import os
from datetime import datetime
try:
    import joblib
except Exception:  # joblib is in sklearn deps but guard anyway
    joblib = None

logger = logging.getLogger(__name__)

class WinPredictor:
    """Predict match outcomes using machine learning"""
    
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.model = None
        self.label_encoders = {}
        self.is_trained = False
        # Phase-wise models
        self.phase_runs_model = None
        self.phase_wkts_model = None
        self.phase_encoders = {}
        # Try loading models from disk first, else train
        loaded = False
        try:
            loaded = self.load_models()
        except Exception:
            loaded = False
        if not loaded:
            self._train_model()
    
    def _train_model(self):
        """Train the win prediction model"""
        try:
            logger.info("Training win prediction model...")
            
            # Prepare training data
            training_data = self._prepare_training_data()
            
            # Train with very small datasets too; fall back gracefully if still too small
            if len(training_data) < 3:
                logger.warning("Insufficient data to train model")
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(training_data)
            
            # Encode categorical variables
            categorical_features = ['team1', 'team2', 'venue', 'format', 'toss_winner', 'toss_decision']
            
            for feature in categorical_features:
                if feature in df.columns:
                    le = LabelEncoder()
                    df[feature] = le.fit_transform(df[feature].astype(str))
                    self.label_encoders[feature] = le
            
            # Prepare features and target
            feature_columns = categorical_features + ['team1_recent_form', 'team2_recent_form', 
                                                    'venue_team1_performance', 'venue_team2_performance']
            
            X = df[feature_columns]
            y = df['winner_team1']  # 1 if team1 wins, 0 if team2 wins
            
            # Train the model
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.model.fit(X, y)
            
            self.is_trained = True
            logger.info(f"Model trained successfully with {len(training_data)} matches")
            # Train phasewise expected score and wickets models
            self._train_phase_models()
            # Persist models if possible
            try:
                self.save_models()
            except Exception:
                logger.debug("Skipping save_models after training")
            
        except Exception as e:
            logger.error(f"Error training model: {e}")

    def retrain(self):
        """Public method to (re)train models after data changes."""
        # Reset training flags and models
        self.model = None
        self.label_encoders = {}
        self.is_trained = False
        self.phase_runs_model = None
        self.phase_wkts_model = None
        self.phase_encoders = {}
        self._train_model()

    def save_models(self, model_dir: str = 'models'):
        """Save classifier, encoders, and phase models to disk."""
        if joblib is None:
            raise RuntimeError("joblib not available for saving models")
        os.makedirs(model_dir, exist_ok=True)
        meta = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'matches': len(getattr(self.data_processor, 'matches_data', []) or []),
            'is_trained': bool(self.is_trained)
        }
        # Save classifier-related parts
        joblib.dump(self.model, os.path.join(model_dir, 'classifier.joblib'))
        joblib.dump(self.label_encoders, os.path.join(model_dir, 'label_encoders.joblib'))
        # Phase models
        joblib.dump(self.phase_runs_model, os.path.join(model_dir, 'phase_runs.joblib'))
        joblib.dump(self.phase_wkts_model, os.path.join(model_dir, 'phase_wkts.joblib'))
        joblib.dump(self.phase_encoders, os.path.join(model_dir, 'phase_encoders.joblib'))
        joblib.dump(meta, os.path.join(model_dir, 'meta.joblib'))
        return meta

    def load_models(self, model_dir: str = 'models') -> bool:
        """Load saved models if available. Returns True if loaded."""
        if joblib is None:
            return False
        try:
            clf_path = os.path.join(model_dir, 'classifier.joblib')
            enc_path = os.path.join(model_dir, 'label_encoders.joblib')
            if not (os.path.exists(clf_path) and os.path.exists(enc_path)):
                return False
            self.model = joblib.load(clf_path)
            self.label_encoders = joblib.load(enc_path)
            self.phase_runs_model = joblib.load(os.path.join(model_dir, 'phase_runs.joblib')) if os.path.exists(os.path.join(model_dir, 'phase_runs.joblib')) else None
            self.phase_wkts_model = joblib.load(os.path.join(model_dir, 'phase_wkts.joblib')) if os.path.exists(os.path.join(model_dir, 'phase_wkts.joblib')) else None
            self.phase_encoders = joblib.load(os.path.join(model_dir, 'phase_encoders.joblib')) if os.path.exists(os.path.join(model_dir, 'phase_encoders.joblib')) else {}
            self.is_trained = True if self.model is not None else False
            return True
        except Exception as e:
            logger.warning(f"Failed to load models: {e}")
            return False
    
    def _prepare_training_data(self):
        """Prepare training data from historical matches"""
        training_data = []
        
        for match in self.data_processor.matches_data:
            info = match.get('info', {})
            
            # Get basic match information
            teams = info.get('teams', [])
            if len(teams) != 2:
                continue
            
            team1, team2 = teams[0], teams[1]
            venue = info.get('venue', 'Unknown')
            match_type = info.get('match_type', 'Unknown')
            
            # Toss information
            toss = info.get('toss', {})
            toss_winner = toss.get('winner', team1)
            toss_decision = toss.get('decision', 'bat')
            
            # Match outcome
            outcome = info.get('outcome', {})
            winner = outcome.get('winner')
            
            if not winner or winner not in teams:
                continue
            
            # Calculate team form and venue performance
            team1_form = self._calculate_recent_form(team1, match)
            team2_form = self._calculate_recent_form(team2, match)
            
            team1_venue_perf = self._calculate_venue_performance(team1, venue, match)
            team2_venue_perf = self._calculate_venue_performance(team2, venue, match)
            
            training_data.append({
                'team1': team1,
                'team2': team2,
                'venue': venue,
                'format': match_type,
                'toss_winner': toss_winner,
                'toss_decision': toss_decision,
                'team1_recent_form': team1_form,
                'team2_recent_form': team2_form,
                'venue_team1_performance': team1_venue_perf,
                'venue_team2_performance': team2_venue_perf,
                'winner_team1': 1 if winner == team1 else 0
            })
        
        return training_data

    def _train_phase_models(self):
        """Train simple ML models to estimate per-over runs and wickets."""
        try:
            rows = []
            for match in self.data_processor.matches_data:
                info = match.get('info', {})
                fmt = info.get('match_type', 'Unknown')
                venue = info.get('venue', 'Unknown')
                teams = info.get('teams', [])
                innings_list = match.get('innings', [])
                for innings in innings_list:
                    team_bat = innings.get('team')
                    # infer bowling team
                    team_bowl = None
                    if len(teams) == 2:
                        team_bowl = teams[1] if team_bat == teams[0] else teams[0]
                    overs = innings.get('overs', [])
                    for idx, over in enumerate(overs, start=1):
                        deliveries = over.get('deliveries', [])
                        runs_sum = 0
                        wkts_sum = 0
                        for d in deliveries:
                            runs_sum += int(d.get('runs', {}).get('total', 0))
                            for w in d.get('wickets', []) or []:
                                k = w.get('kind', '')
                                if k not in ['run out', 'retired hurt', 'retired out']:
                                    wkts_sum += 1
                        phase = self._map_over_to_phase(fmt, idx)
                        rows.append({
                            'venue': venue,
                            'format': fmt,
                            'phase': phase,
                            'over': idx,
                            'runs': runs_sum,
                            'wkts': wkts_sum
                        })
            if len(rows) < 50:
                logger.warning("Insufficient over-level data to train phase models")
                return
            df = pd.DataFrame(rows)
            cat_cols = ['venue', 'format', 'phase']
            X_parts = []
            for c in cat_cols:
                le = LabelEncoder()
                df[c] = le.fit_transform(df[c].astype(str))
                self.phase_encoders[c] = le
            X = df[['venue','format','phase','over']]
            y_runs = df['runs']
            y_wkts = df['wkts']
            self.phase_runs_model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.phase_runs_model.fit(X, y_runs)
            self.phase_wkts_model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.phase_wkts_model.fit(X, y_wkts)
            logger.info("Phase models trained successfully")
        except Exception as e:
            logger.error(f"Error training phase models: {e}")

    def _map_over_to_phase(self, fmt, over):
        if fmt == 'T20':
            if 1 <= over <= 6:
                return '1-6'
            if 7 <= over <= 12:
                return '7-12'
            if 13 <= over <= 16:
                return '13-16'
            return '17-20'
        # ODI/ODM
        if 1 <= over <= 10:
            return '1-10'
        if 11 <= over <= 20:
            return '11-20'
        if 21 <= over <= 30:
            return '21-30'
        if 31 <= over <= 40:
            return '31-40'
        return '41-50'

    def predict_phasewise_expected(self, match_details):
        """Predict expected runs and wickets per phase and totals for both teams."""
        venue = match_details.get('venue')
        fmt = match_details.get('format', 'ODI')
        phases = (['1-6','7-12','13-16','17-20'] if fmt == 'T20'
                  else ['1-10','11-20','21-30','31-40','41-50'])
        def enc_val(col, val):
            le = self.phase_encoders.get(col)
            if not le:
                return 0
            try:
                return le.transform([str(val)])[0]
            except Exception:
                return 0
        results = {}
        for team_key in ['team1','team2']:
            phase_map = {p: {'runs': 0.0, 'wkts': 0.0} for p in phases}
            runs_total = 0.0
            wkts_total = 0.0
            max_over = 20 if fmt == 'T20' else 50
            for over in range(1, max_over+1):
                p = self._map_over_to_phase(fmt, over)
                if self.phase_runs_model and self.phase_wkts_model:
                    x = [
                        enc_val('venue', venue),
                        enc_val('format', fmt),
                        enc_val('phase', p),
                        over
                    ]
                    try:
                        r = float(self.phase_runs_model.predict([x])[0])
                        w = float(self.phase_wkts_model.predict([x])[0])
                    except Exception:
                        r, w = 0.0, 0.0
                else:
                    # Fallback: distribute baseline evenly over overs
                    avg_score, wkts_per_inning = self._get_venue_baselines(venue, fmt)
                    r = avg_score / (20 if fmt == 'T20' else 50)
                    w = wkts_per_inning / (20 if fmt == 'T20' else 50)
                phase_map[p]['runs'] += r
                phase_map[p]['wkts'] += w
                runs_total += r
                wkts_total += w
            # Round values
            for p in phases:
                phase_map[p]['runs'] = round(phase_map[p]['runs'], 1)
                phase_map[p]['wkts'] = round(phase_map[p]['wkts'], 2)
            results[team_key] = {
                'phases': phase_map,
                'total_runs': int(round(runs_total)),
                'total_wkts': int(round(wkts_total))
            }
        return results
    
    def _calculate_recent_form(self, team, current_match, num_matches=10):
        """Calculate recent form for a team (before current match)"""
        current_date = current_match.get('info', {}).get('dates', [''])[0]
        
        team_matches = []
        for match in self.data_processor.matches_data:
            match_info = match.get('info', {})
            match_date = match_info.get('dates', [''])[0]
            teams = match_info.get('teams', [])
            
            # Skip current match and future matches
            if match_date >= current_date or team not in teams:
                continue
            
            team_matches.append(match)
        
        # Sort by date and take recent matches
        team_matches.sort(key=lambda x: x.get('info', {}).get('dates', [''])[0], reverse=True)
        recent_matches = team_matches[:num_matches]
        
        if not recent_matches:
            return 0.5
        
        wins = 0
        for match in recent_matches:
            winner = match.get('info', {}).get('outcome', {}).get('winner')
            if winner == team:
                wins += 1
        
        return wins / len(recent_matches)
    
    def _calculate_venue_performance(self, team, venue, current_match):
        """Calculate team's performance at a specific venue (before current match)"""
        current_date = current_match.get('info', {}).get('dates', [''])[0]
        
        venue_matches = []
        for match in self.data_processor.matches_data:
            match_info = match.get('info', {})
            match_date = match_info.get('dates', [''])[0]
            match_venue = match_info.get('venue', '')
            teams = match_info.get('teams', [])
            
            # Skip current match and future matches
            if match_date >= current_date or match_venue != venue or team not in teams:
                continue
            
            venue_matches.append(match)
        
        if not venue_matches:
            return 0.5
        
        wins = 0
        for match in venue_matches:
            winner = match.get('info', {}).get('outcome', {}).get('winner')
            if winner == team:
                wins += 1
        
        return wins / len(venue_matches)
    
    def predict_match_outcome(self, match_details):
        """Predict the outcome of a match"""
        if not self.is_trained:
            # Build a consistent, rich heuristic response instead of returning an error
            return self._heuristic_full_response(match_details)
        
        try:
            # Prepare input data
            input_data = self._prepare_prediction_input(match_details)
            
            # Make prediction
            probability = self.model.predict_proba([input_data])[0]
            team1_win_prob = probability[1] * 100
            team2_win_prob = probability[0] * 100
            
            # Get feature importance for explanation
            feature_importance = self._get_prediction_explanation(input_data)
            
            # Additional analysis
            historical_h2h = self._get_historical_head_to_head(
                match_details['team1'], match_details['team2']
            )

            # Expected average score and wickets (phasewise and totals)
            phase_expected = self.predict_phasewise_expected(match_details)
            exp_scores = self._estimate_expected_scores(match_details)

            # Player-level H2H key battles (if players provided)
            key_battles, player_h2h = self._compute_key_battles(
                match_details.get('team1_players') or [],
                match_details.get('team2_players') or []
            )

            # Player importance for MoM
            mom_importance = self._compute_mom_importance(
                (match_details.get('team1_players') or []) + (match_details.get('team2_players') or [])
            )
            
            # Build top 5 reasons as human-readable strings
            reasons = self._format_top_reasons(feature_importance, match_details)

            return {
                'team1': match_details['team1'],
                'team2': match_details['team2'],
                'predictions': {
                    'team1_win_probability': round(team1_win_prob, 2),
                    'team2_win_probability': round(team2_win_prob, 2),
                    'predicted_winner': match_details['team1'] if team1_win_prob > team2_win_prob else match_details['team2'],
                    'confidence': round(max(team1_win_prob, team2_win_prob), 2)
                },
                'factors': feature_importance,
                'reasons': reasons,
                'historical_h2h': historical_h2h,
                'venue_analysis': self._get_venue_analysis(match_details['venue']),
                'toss_impact': self._get_toss_impact_analysis(match_details['venue']),
                'expected': exp_scores,
                'phase_expected': phase_expected,
                'key_battles': key_battles,
                'mom_importance': mom_importance,
                'player_h2h': player_h2h
            }
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return {
                'error': str(e),
                'fallback_prediction': self._fallback_prediction(match_details)
            }

    def _heuristic_full_response(self, match_details):
        """Return a fully shaped prediction using heuristics when ML model is unavailable."""
        try:
            team1 = match_details.get('team1') or 'Team 1'
            team2 = match_details.get('team2') or 'Team 2'
            venue = match_details.get('venue') or ''
            fmt = match_details.get('format') or 'ODI'
            t1_players = match_details.get('team1_players') or []
            t2_players = match_details.get('team2_players') or []

            # Overall expected via venue + form
            exp_scores = self._estimate_expected_scores({
                'venue': venue,
                'format': fmt,
                'team1': team1,
                'team2': team2
            })

            # Phasewise expected (falls back to venue baselines if phase models not trained)
            phase_expected = self.predict_phasewise_expected({
                'venue': venue,
                'format': fmt,
                'team1': team1,
                'team2': team2
            })

            # Heuristic probabilities from expected totals/wickets and toss
            fb = self._fallback_prediction({
                'team1': team1,
                'team2': team2,
                'toss_winner': match_details.get('toss_winner'),
                'toss_decision': match_details.get('toss_decision')
            })
            team1_win = fb.get('team1_win_probability', 50.0)
            team2_win = fb.get('team2_win_probability', 50.0)
            predicted_winner = fb.get('predicted_winner', team1 if team1_win >= team2_win else team2)
            confidence = fb.get('confidence', max(team1_win, team2_win))

            # Key battles and MoM importance
            key_battles, player_h2h = self._compute_key_battles(t1_players, t2_players)
            mom_importance = self._compute_mom_importance(t1_players + t2_players) if (t1_players or t2_players) else {}

            # Reasons (5 concise)
            reasons = []
            t1s, t2s = exp_scores.get('team1_expected_score'), exp_scores.get('team2_expected_score')
            if t1s and t2s:
                diff = int(abs(t1s - t2s))
                lead = team1 if t1s > t2s else team2
                reasons.append(f"{lead} higher expected total by {diff} runs")
            t1w, t2w = exp_scores.get('team1_expected_wickets'), exp_scores.get('team2_expected_wickets')
            if t1w and t2w:
                diffw = int(abs(t1w - t2w))
                leadw = team1 if t2w > t1w else team2  # fewer wickets expected lost = advantage
                if diffw:
                    reasons.append(f"{leadw} stronger batting stability (wickets)")
            va = self._get_venue_analysis(venue)
            if va:
                bf = va.get('bat_first_advantage')
                if bf is not None:
                    reasons.append("Venue batting-first advantage impacts outcome")
            if match_details.get('toss_winner'):
                reasons.append("Toss outcome provides a small edge")
            if not reasons:
                reasons.append("Recent form and venue trends drive the prediction")
            while len(reasons) < 5:
                reasons.append("Combined historical patterns and heuristics")

            return {
                'team1': team1,
                'team2': team2,
                'predictions': {
                    'team1_win_probability': round(float(team1_win), 2),
                    'team2_win_probability': round(float(team2_win), 2),
                    'predicted_winner': predicted_winner,
                    'confidence': round(float(confidence), 2)
                },
                'factors': {},
                'reasons': reasons[:5],
                'historical_h2h': self._get_historical_head_to_head(team1, team2),
                'venue_analysis': va,
                'toss_impact': self._get_toss_impact_analysis(venue),
                'expected': exp_scores,
                'phase_expected': phase_expected,
                'key_battles': key_battles,
                'mom_importance': mom_importance,
                'player_h2h': player_h2h,
                'model_trained': False
            }
        except Exception as e:
            logger.error(f"Heuristic prediction failed: {e}")
            # Final minimal fallback
            fb = self._fallback_prediction(match_details)
            return {
                'team1': match_details.get('team1'),
                'team2': match_details.get('team2'),
                'predictions': {
                    'team1_win_probability': fb.get('team1_win_probability', 50.0),
                    'team2_win_probability': fb.get('team2_win_probability', 50.0),
                    'predicted_winner': fb.get('predicted_winner'),
                    'confidence': fb.get('confidence')
                },
                'factors': {},
                'reasons': ["Heuristic fallback used due to limited data"],
                'historical_h2h': self._get_historical_head_to_head(match_details.get('team1'), match_details.get('team2')),
                'venue_analysis': self._get_venue_analysis(match_details.get('venue')),
                'toss_impact': self._get_toss_impact_analysis(match_details.get('venue')),
                'expected': self._estimate_expected_scores(match_details),
                'phase_expected': self.predict_phasewise_expected(match_details),
                'key_battles': [],
                'mom_importance': {},
                'player_h2h': {},
                'model_trained': False
            }

    def _format_top_reasons(self, feature_importance, match_details):
        # Map feature keys to readable reasons
        mapping = {
            'team1': f"Team strength and historical performance favor {match_details.get('team1')}",
            'team2': f"Team strength and historical performance favor {match_details.get('team2')}",
            'venue': f"Venue conditions impact outcome",
            'format': f"Format-specific trends influence probabilities",
            'toss_winner': f"Toss outcome historically affects match result",
            'toss_decision': f"Toss decision (bat/field) shifts advantage",
            'team1_recent_form': f"{match_details.get('team1')} recent form is strong",
            'team2_recent_form': f"{match_details.get('team2')} recent form is strong",
            'venue_team1_performance': f"{match_details.get('team1')} record at venue",
            'venue_team2_performance': f"{match_details.get('team2')} record at venue",
        }
        items = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        out = []
        for k, _ in items:
            out.append(mapping.get(k, f"Factor '{k}' contributed significantly"))
        # ensure 5 reasons
        while len(out) < 5:
            out.append("Model confidence based on combined historical patterns")
        return out[:5]
    
    def _prepare_prediction_input(self, match_details):
        """Prepare input data for prediction"""
        team1 = match_details['team1']
        team2 = match_details['team2']
        venue = match_details['venue']
        format_type = match_details.get('format', 'ODI')
        toss_winner = match_details.get('toss_winner', team1)
        toss_decision = match_details.get('toss_decision', 'bat')
        
        # Calculate current form and venue performance
        team1_form = self._get_current_team_form(team1)
        team2_form = self._get_current_team_form(team2)
        
        team1_venue_perf = self._get_current_venue_performance(team1, venue)
        team2_venue_perf = self._get_current_venue_performance(team2, venue)
        
        # Encode categorical variables
        input_data = []
        
        categorical_features = ['team1', 'team2', 'venue', 'format', 'toss_winner', 'toss_decision']
        values = [team1, team2, venue, format_type, toss_winner, toss_decision]
        
        for i, feature in enumerate(categorical_features):
            if feature in self.label_encoders:
                try:
                    encoded_value = self.label_encoders[feature].transform([str(values[i])])[0]
                except ValueError:
                    # Handle unseen values
                    encoded_value = 0
                input_data.append(encoded_value)
            else:
                input_data.append(0)
        
        # Add numerical features
        input_data.extend([team1_form, team2_form, team1_venue_perf, team2_venue_perf])
        
        return input_data

    def _estimate_expected_scores(self, match_details):
        """Estimate expected average score and wickets for both teams using venue stats and form.
        Returns a dict with expected scores and wickets.
        """
        venue = match_details.get('venue')
        fmt = match_details.get('format', 'ODI')
        team1 = match_details['team1']
        team2 = match_details['team2']

        # Compute venue averages for the format
        avg_score, wkts_per_match = self._get_venue_baselines(venue, fmt)

        # Recent form scaling between 0.8 and 1.2
        form1 = self._get_current_team_form(team1)
        form2 = self._get_current_team_form(team2)
        scale = lambda f: 0.9 + 0.2 * f  # 0.9 to 1.1

        exp_team1_score = round(avg_score * scale(form1))
        exp_team2_score = round(avg_score * scale(form2))
        exp_team1_wkts = min(10, max(3, round(wkts_per_match * (1.0 + (1 - form1) * 0.2))))
        exp_team2_wkts = min(10, max(3, round(wkts_per_match * (1.0 + (1 - form2) * 0.2))))

        return {
            'team1_expected_score': exp_team1_score,
            'team2_expected_score': exp_team2_score,
            'team1_expected_wickets': exp_team1_wkts,
            'team2_expected_wickets': exp_team2_wkts
        }

    def _get_venue_baselines(self, venue, fmt):
        # Compute average score and wickets per match at venue filtered by format
        matches = [m for m in self.data_processor.matches_data
                   if m.get('info', {}).get('venue') == venue and
                   (fmt == '' or m.get('info', {}).get('match_type') == fmt)]
        if not matches:
            return (160 if fmt == 'T20' else 260 if fmt == 'ODI' else 300, 6)
        scores = []
        wickets = 0
        for match in matches:
            for inning in match.get('innings', []):
                score = self.data_processor._calculate_team_score(inning)
                scores.append(score['runs'])
                wickets += score['wickets']
        avg_score = round(np.mean(scores), 1) if scores else (160 if fmt == 'T20' else 260)
        innings_count = sum(len(m.get('innings', [])) for m in matches)
        wkts_per_match = round((wickets / max(innings_count, 1)) , 1)
        return (avg_score, wkts_per_match)

    def _compute_key_battles(self, team1_players, team2_players, min_balls=12):
        """Compute batter vs bowler H2H for provided squads. Returns (top_list, per_player_map)."""
        battles = []
        per_player = {}
        if not team1_players or not team2_players:
            return battles, per_player
        # Build quick lookup
        for match in self.data_processor.matches_data:
            for inning in match.get('innings', []):
                for over in inning.get('overs', []):
                    for d in over.get('deliveries', []):
                        batter = d.get('batter')
                        bowler = d.get('bowler')
                        if batter in team1_players and bowler in team2_players:
                            runs = int(d.get('runs', {}).get('batter', 0))
                            out = 0
                            if 'wickets' in d:
                                for w in d['wickets']:
                                    if w.get('player_out') == batter and w.get('kind') not in ['run out','retired hurt','retired out']:
                                        out = 1
                                        break
                            key = (batter, bowler, 't1bat')
                            rec = per_player.setdefault(batter, {'batting_vs': {}})['batting_vs'].setdefault(bowler, {'runs':0,'balls':0,'outs':0})
                            rec['runs'] += runs
                            rec['balls'] += 1
                            rec['outs'] += out
                        if batter in team2_players and bowler in team1_players:
                            runs = int(d.get('runs', {}).get('batter', 0))
                            out = 0
                            if 'wickets' in d:
                                for w in d['wickets']:
                                    if w.get('player_out') == batter and w.get('kind') not in ['run out','retired hurt','retired out']:
                                        out = 1
                                        break
                            rec = per_player.setdefault(bowler, {'bowling_vs': {}})['bowling_vs'].setdefault(batter, {'runs':0,'balls':0,'outs':0})
                            rec['runs'] += runs
                            rec['balls'] += 1
                            rec['outs'] += out
        # Create flattened key battles list
        for batter, data in per_player.items():
            for opp, rec in data.get('batting_vs', {}).items():
                if rec['balls'] >= min_balls:
                    sr = (rec['runs']/rec['balls']*100) if rec['balls']>0 else 0
                    avg = (rec['runs']/rec['outs']) if rec['outs']>0 else rec['runs']
                    score = rec['runs'] + 25*rec['outs'] + 0.1*sr - 0.02*rec['balls']
                    battles.append({'batter': batter, 'bowler': opp, 'runs': rec['runs'], 'balls': rec['balls'], 'outs': rec['outs'], 'sr': round(sr,1), 'avg': round(avg,1), 'score': round(score,2)})
        # sort by improved composite score emphasizing dismissals and productivity
        battles.sort(key=lambda x: x['score'], reverse=True)
        return battles[:10], per_player

    def _compute_mom_importance(self, players):
        """Compute a simple importance percentage per player based on batting runs and bowling wickets aggregates."""
        if not players:
            return {}
        scores = {}
        for p in players:
            try:
                stats = self.data_processor.player_stats_calculator.get_player_stats(p)
                bat = stats.get('batting', {})
                bowl = stats.get('bowling', {})
                val = (bat.get('average',0) * 0.5 + bat.get('strike_rate',0) * 0.2 + bowl.get('wickets',0) * 2 + (50 - bowl.get('average',50)) * 0.1)
                scores[p] = max(val, 0)
            except Exception:
                continue
        total = sum(scores.values()) or 1
        return {p: round(v/total*100,1) for p,v in sorted(scores.items(), key=lambda x: x[1], reverse=True)}
    
    def _get_current_team_form(self, team):
        """Get current form for a team"""
        team_matches = self.data_processor.get_team_match_data(team)
        recent_matches = team_matches[-10:] if len(team_matches) >= 10 else team_matches
        
        if not recent_matches:
            return 0.5
        
        wins = len([m for m in recent_matches if m['result'] == 'win'])
        return wins / len(recent_matches)
    
    def _get_current_venue_performance(self, team, venue):
        """Get current venue performance for a team"""
        venue_matches = self.data_processor.get_venue_matches(venue)
        team_venue_matches = []
        
        for match in venue_matches:
            teams = match.get('info', {}).get('teams', [])
            if team in teams:
                winner = match.get('info', {}).get('outcome', {}).get('winner')
                team_venue_matches.append(winner == team)
        
        if not team_venue_matches:
            return 0.5
        
        return sum(team_venue_matches) / len(team_venue_matches)
    
    def _get_prediction_explanation(self, input_data):
        """Get explanation for the prediction"""
        if not self.model:
            return {}
        
        feature_names = ['team1', 'team2', 'venue', 'format', 'toss_winner', 'toss_decision',
                        'team1_recent_form', 'team2_recent_form', 
                        'venue_team1_performance', 'venue_team2_performance']
        
        feature_importance = dict(zip(feature_names, self.model.feature_importances_))
        
        # Sort by importance
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        
        return dict(sorted_features[:5])  # Return top 5 factors
    
    def _get_historical_head_to_head(self, team1, team2):
        """Get historical head-to-head record"""
        team1_matches = self.data_processor.get_team_match_data(team1)
        h2h_matches = [m for m in team1_matches if m['opponent'] == team2]
        
        if not h2h_matches:
            return {'total_matches': 0, 'team1_wins': 0, 'team2_wins': 0}
        
        team1_wins = len([m for m in h2h_matches if m['result'] == 'win'])
        team2_wins = len([m for m in h2h_matches if m['result'] == 'loss'])
        
        return {
            'total_matches': len(h2h_matches),
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'team1_win_percentage': round(team1_wins / len(h2h_matches) * 100, 2) if h2h_matches else 0
        }
    
    def _get_venue_analysis(self, venue):
        """Get venue-specific analysis"""
        venue_matches = self.data_processor.get_venue_matches(venue)
        
        if not venue_matches:
            return {'bat_first_advantage': 50, 'total_matches': 0}
        
        bat_first_wins = 0
        total_decided = 0
        
        for match in venue_matches:
            winner = match.get('info', {}).get('outcome', {}).get('winner')
            if not winner:
                continue
            
            innings = match.get('innings', [])
            if len(innings) >= 2:
                first_innings_team = innings[0].get('team')
                if first_innings_team == winner:
                    bat_first_wins += 1
                total_decided += 1
        
        bat_first_advantage = (bat_first_wins / total_decided * 100) if total_decided > 0 else 50
        
        return {
            'bat_first_advantage': round(bat_first_advantage, 2),
            'bowl_first_advantage': round(100 - bat_first_advantage, 2),
            'total_matches': len(venue_matches)
        }
    
    def _get_toss_impact_analysis(self, venue):
        """Get toss impact analysis for venue"""
        venue_matches = self.data_processor.get_venue_matches(venue)
        
        toss_win_match_win = 0
        total_matches = 0
        
        for match in venue_matches:
            toss_winner = match.get('info', {}).get('toss', {}).get('winner')
            match_winner = match.get('info', {}).get('outcome', {}).get('winner')
            
            if toss_winner and match_winner:
                if toss_winner == match_winner:
                    toss_win_match_win += 1
                total_matches += 1
        
        toss_advantage = (toss_win_match_win / total_matches * 100) if total_matches > 0 else 50
        
        return {
            'toss_advantage_percentage': round(toss_advantage, 2),
            'toss_impact': 'High' if toss_advantage > 60 else 'Medium' if toss_advantage > 55 else 'Low'
        }
    
    def _fallback_prediction(self, match_details):
        """Provide fallback prediction when ML model is not available"""
        team1 = match_details['team1']
        team2 = match_details['team2']
        
        # Simple heuristic based on recent form
        team1_form = self._get_current_team_form(team1)
        team2_form = self._get_current_team_form(team2)
        
        # Adjust for toss
        toss_adjustment = 5 if match_details.get('toss_winner') == team1 else -5
        
        team1_score = team1_form * 100 + toss_adjustment
        team2_score = team2_form * 100 - toss_adjustment
        
        total_score = team1_score + team2_score
        team1_prob = (team1_score / total_score * 100) if total_score > 0 else 50
        team2_prob = 100 - team1_prob
        
        return {
            'team1_win_probability': round(team1_prob, 2),
            'team2_win_probability': round(team2_prob, 2),
            'predicted_winner': team1 if team1_prob > team2_prob else team2,
            'confidence': round(max(team1_prob, team2_prob), 2),
            'note': 'Prediction based on recent form analysis (ML model unavailable)'
        }