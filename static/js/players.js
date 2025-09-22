// Players page JavaScript

let currentPlayerData = null;
let playersData = [];
let venuesData = [];

document.addEventListener('DOMContentLoaded', function() {
    initializePlayersPage();
});

async function initializePlayersPage() {
    try {
        await loadPlayersData();
        await loadVenuesData();
        await loadCountriesData();
        initPhaseFilter();
        setupEventListeners();
    } catch (error) {
        console.error('Error initializing players page:', error);
        CricketAnalytics.showAlert('Error loading data. Please refresh the page.', 'danger');
    }
}

async function loadPlayersData() {
    try {
        const response = await axios.get('/api/data/players');
        playersData = (response.data.players || []).sort();
        
        const playerSelect = document.getElementById('playerSelect');
        const comparePlayer1 = document.getElementById('comparePlayer1');
        const comparePlayer2 = document.getElementById('comparePlayer2');
        
        [playerSelect, comparePlayer1, comparePlayer2].forEach(select => {
            if (select) {
                playersData.forEach(player => {
                    const option = document.createElement('option');
                    option.value = player;
                    option.textContent = player;
                    select.appendChild(option);
                });
            }
        });
    } catch (error) {
        console.error('Error loading players:', error);
        throw error;
    }
}

async function loadVenuesData() {
    try {
        const response = await axios.get('/api/all-venues');
        venuesData = response.data.venues.sort();
        
        const venueSelect = document.getElementById('venueFilter');
        if (venueSelect) {
            venuesData.forEach(venue => {
                const option = document.createElement('option');
                option.value = venue;
                option.textContent = venue;
                venueSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading venues:', error);
        throw error;
    }
}

async function loadCountriesData() {
    try {
        const response = await axios.get('/api/all-countries');
        const countriesData = response.data.countries.sort();
        
        const countryFilter = document.getElementById('countryFilter');
        if (countryFilter) {
            countriesData.forEach(country => {
                const option = document.createElement('option');
                option.value = country;
                option.textContent = country;
                countryFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading countries:', error);
        throw error;
    }
}

function setupEventListeners() {
    // Analyze player button
    document.getElementById('analyzePlayerBtn').addEventListener('click', analyzePlayer);
    // Change phase options when format changes
    const formatEl = document.getElementById('formatFilter');
    if (formatEl) {
        formatEl.addEventListener('change', updatePhaseOptions);
    }
    
    // Compare players button
    document.getElementById('comparePlayerBtn').addEventListener('click', function() {
        const modal = new bootstrap.Modal(document.getElementById('comparePlayersModal'));
        modal.show();
    });
    
    // Start comparison button
    document.getElementById('startComparisonBtn').addEventListener('click', compareSelectedPlayers);
    
    // Export stats button
    document.getElementById('exportStatsBtn').addEventListener('click', exportPlayerStats);
    // No advanced analysis tab anymore
}

function initPhaseFilter() {
    updatePhaseOptions();
}

function updatePhaseOptions() {
    const format = document.getElementById('formatFilter')?.value || '';
    const phaseSelect = document.getElementById('phaseFilter');
    if (!phaseSelect) return;

    // Reset
    phaseSelect.innerHTML = '';
    const add = (val, text) => {
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = text;
        phaseSelect.appendChild(opt);
    };

    // Always include overall
    add('', 'All Overs');

    if (format === 'T20') {
        phaseSelect.disabled = false;
        add('t20_1_6', 'Powerplay (1-6)');
        add('t20_7_12', 'Middle (7-12)');
        add('t20_13_16', 'Late Middle (13-16)');
        add('t20_17_20', 'Death (17-20)');
    } else if (format === 'ODI') {
        phaseSelect.disabled = false;
        add('odi_1_10', 'PP1 (1-10)');
        add('odi_11_20', 'Middle1 (11-20)');
        add('odi_21_30', 'Middle2 (21-30)');
        add('odi_31_40', 'Middle3 (31-40)');
        add('odi_41_50', 'Death (41-50)');
    } else {
        // Test or all formats: disable specific phase selection
        phaseSelect.disabled = true;
    }
}

async function analyzePlayer() {
    const player = document.getElementById('playerSelect').value;
    
    if (!player) {
        CricketAnalytics.showAlert('Please select a player to analyze.', 'warning');
        return;
    }
    
    try {
        CricketAnalytics.showLoading();
        
        // Build query parameters
        const params = new URLSearchParams();
        const matchCategory = document.getElementById('matchCategoryFilter').value;
        const format = document.getElementById('formatFilter').value;
    const phase = document.getElementById('phaseFilter')?.value || '';
    const phaseRole = document.getElementById('phaseRoleFilter')?.value || '';
        const venue = document.getElementById('venueFilter').value;
        const country = document.getElementById('countryFilter').value;
    const inningsType = document.getElementById('inningsTypeFilter').value;
        
        if (matchCategory) params.append('match_category', matchCategory);
        if (format) params.append('format', format);
    if (phase) params.append('phase', phase);
    if (phaseRole) params.append('phase_role', phaseRole);
        if (venue) params.append('venue', venue);
        if (country) params.append('country', country);
    if (inningsType) params.append('innings_type', inningsType);
        
        // Fetch player stats
        const [statsResponse] = await Promise.all([
            axios.get(`/api/player-stats/${encodeURIComponent(player)}?${params}`)
        ]);
        
        // Check for errors in responses
        if (statsResponse.data.error) {
            CricketAnalytics.showAlert(statsResponse.data.error, 'warning');
            CricketAnalytics.hideLoading();
            return;
        }
        
        currentPlayerData = {
            stats: statsResponse.data
        };
        
        displayPlayerStats();
        CricketAnalytics.hideLoading();
        
    } catch (error) {
        console.error('Error analyzing player:', error);
        CricketAnalytics.showAlert('Error analyzing player data. Please try again.', 'danger');
        CricketAnalytics.hideLoading();
    }
}

function displayPlayerStats() {
    if (!currentPlayerData || !currentPlayerData.stats) return;
    
    const stats = currentPlayerData.stats;
    
    // Show the stats container
    document.getElementById('playerStatsContainer').style.display = 'block';
    
    // Update player header
    document.getElementById('playerName').textContent = stats.player_name;
    document.getElementById('playerSummary').textContent = 
        `${stats.total_matches} matches analyzed with current filters`;
    
    // Update overall stats cards
    const batting = stats.batting || {};
    const bowling = stats.bowling || {};
    
    document.getElementById('totalMatches').textContent = stats.total_matches || 0;
    document.getElementById('totalRuns').textContent = CricketAnalytics.formatNumber(batting.runs || 0);
    document.getElementById('battingAverage').textContent = batting.average || '0.00';
    document.getElementById('strikeRate').textContent = batting.strike_rate || '0.00';
    document.getElementById('totalWickets').textContent = bowling.wickets || 0;
    document.getElementById('economyRate').textContent = bowling.economy || '0.00';
    
    // Update detailed batting stats
    updateBattingStatsTable(batting);
    
    // Update detailed bowling stats
    updateBowlingStatsTable(bowling);
    
    // Update phase analysis in dedicated tab
    updatePhaseAnalysis(stats.phase_analysis, stats.matches);
    
    // Update rivalry analysis
    updateRivalryAnalysis(stats.rivalry_analysis);
    
    // Update milestones
    document.getElementById('fifties').textContent = batting.fifties || 0;
    document.getElementById('hundreds').textContent = batting.hundreds || 0;
    document.getElementById('doubleHundreds').textContent = batting.double_hundreds || 0;
    document.getElementById('threeWickets').textContent = bowling.three_wickets || 0;
    document.getElementById('fiveWickets').textContent = bowling.five_wickets || 0;
    
    // Scroll to stats
    document.getElementById('playerStatsContainer').scrollIntoView({ behavior: 'smooth' });
}

function updateBattingStatsTable(batting) {
    const tableBody = document.getElementById('battingStatsTable');
    
    const stats = [
        { label: 'Innings', value: batting.innings || 0 },
        { label: 'Runs', value: batting.runs || 0 },
        { label: 'Balls Faced', value: batting.balls || 0 },
        { label: 'Average', value: batting.average || '0.00' },
        { label: 'Strike Rate', value: batting.strike_rate || '0.00' },
        { label: 'High Score', value: batting.high_score || '0' },
        { label: 'Not Outs', value: batting.not_outs || 0 },
        { label: 'Fours', value: batting.fours || 0 },
        { label: 'Sixes', value: batting.sixes || 0 },
        { label: 'Boundary %', value: `${batting.boundary_percentage || 0}%` }
    ];
    
    tableBody.innerHTML = stats.map(stat => `
        <tr>
            <td class="fw-medium">${stat.label}</td>
            <td class="text-end">${stat.value}</td>
        </tr>
    `).join('');
}

function updateBowlingStatsTable(bowling) {
    const tableBody = document.getElementById('bowlingStatsTable');
    
    const stats = [
        { label: 'Innings', value: bowling.innings || 0 },
        { label: 'Overs', value: bowling.overs || '0.0' },
        { label: 'Runs Conceded', value: bowling.runs || 0 },
        { label: 'Wickets', value: bowling.wickets || 0 },
        { label: 'Average', value: bowling.average || '0.00' },
        { label: 'Economy Rate', value: bowling.economy || '0.00' },
        { label: 'Strike Rate', value: bowling.strike_rate || '0.0' },
        { label: 'Best Bowling', value: bowling.best_bowling || '0/0' },
        { label: 'Maidens', value: bowling.maidens || 0 },
        { label: 'Dot Ball %', value: `${bowling.dot_ball_percentage || 0}%` }
    ];
    
    tableBody.innerHTML = stats.map(stat => `
        <tr>
            <td class="fw-medium">${stat.label}</td>
            <td class="text-end">${stat.value}</td>
        </tr>
    `).join('');
}


async function compareSelectedPlayers() {
    const player1 = document.getElementById('comparePlayer1').value;
    const player2 = document.getElementById('comparePlayer2').value;
    
    if (!player1 || !player2) {
        CricketAnalytics.showAlert('Please select both players for comparison.', 'warning');
        return;
    }
    
    if (player1 === player2) {
        CricketAnalytics.showAlert('Please select different players for comparison.', 'warning');
        return;
    }
    
    try {
        CricketAnalytics.showLoading();
        
        const params = new URLSearchParams();
        params.append('players', player1);
        params.append('players', player2);
        
        const response = await axios.get(`/api/player-comparison?${params}`);
        
        displayPlayerComparison(response.data, player1, player2);
        CricketAnalytics.hideLoading();
        
    } catch (error) {
        console.error('Error comparing players:', error);
        CricketAnalytics.showAlert('Error comparing players. Please try again.', 'danger');
        CricketAnalytics.hideLoading();
    }
}

function displayPlayerComparison(comparisonData, player1, player2) {
    const resultsDiv = document.getElementById('comparisonResults');
    
    const stats1 = comparisonData[player1];
    const stats2 = comparisonData[player2];
    
    if (stats1.error || stats2.error) {
        resultsDiv.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Error loading comparison data. Please try different players.
            </div>
        `;
        return;
    }
    
    const batting1 = stats1.batting || {};
    const batting2 = stats2.batting || {};
    const bowling1 = stats1.bowling || {};
    const bowling2 = stats2.bowling || {};
    
    resultsDiv.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <div class="card bg-primary text-white">
                    <div class="card-header">
                        <h6 class="mb-0">${player1}</h6>
                    </div>
                    <div class="card-body">
                        <h6>Batting</h6>
                        <p class="mb-1">Runs: <strong>${batting1.runs || 0}</strong></p>
                        <p class="mb-1">Average: <strong>${batting1.average || '0.00'}</strong></p>
                        <p class="mb-1">Strike Rate: <strong>${batting1.strike_rate || '0.00'}</strong></p>
                        <p class="mb-3">100s: <strong>${batting1.hundreds || 0}</strong></p>
                        
                        <h6>Bowling</h6>
                        <p class="mb-1">Wickets: <strong>${bowling1.wickets || 0}</strong></p>
                        <p class="mb-1">Average: <strong>${bowling1.average || '0.00'}</strong></p>
                        <p class="mb-0">Economy: <strong>${bowling1.economy || '0.00'}</strong></p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card bg-success text-white">
                    <div class="card-header">
                        <h6 class="mb-0">${player2}</h6>
                    </div>
                    <div class="card-body">
                        <h6>Batting</h6>
                        <p class="mb-1">Runs: <strong>${batting2.runs || 0}</strong></p>
                        <p class="mb-1">Average: <strong>${batting2.average || '0.00'}</strong></p>
                        <p class="mb-1">Strike Rate: <strong>${batting2.strike_rate || '0.00'}</strong></p>
                        <p class="mb-3">100s: <strong>${batting2.hundreds || 0}</strong></p>
                        
                        <h6>Bowling</h6>
                        <p class="mb-1">Wickets: <strong>${bowling2.wickets || 0}</strong></p>
                        <p class="mb-1">Average: <strong>${bowling2.average || '0.00'}</strong></p>
                        <p class="mb-0">Economy: <strong>${bowling2.economy || '0.00'}</strong></p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function exportPlayerStats() {
    if (!currentPlayerData || !currentPlayerData.stats) {
        CricketAnalytics.showAlert('No player data to export. Please analyze a player first.', 'warning');
        return;
    }
    
    const stats = currentPlayerData.stats;
    const csvData = convertToCSV(stats);
    const blob = new Blob([csvData], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `${stats.player_name}_cricket_stats.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    CricketAnalytics.showAlert('Player stats exported successfully!', 'success');
}

function convertToCSV(stats) {
    const batting = stats.batting || {};
    const bowling = stats.bowling || {};
    
    const data = [
        ['Player', stats.player_name],
        ['Total Matches', stats.total_matches],
        [''],
        ['BATTING STATISTICS'],
        ['Innings', batting.innings || 0],
        ['Runs', batting.runs || 0],
        ['Average', batting.average || 0],
        ['Strike Rate', batting.strike_rate || 0],
        ['High Score', batting.high_score || 0],
        ['Fifties', batting.fifties || 0],
        ['Hundreds', batting.hundreds || 0],
        ['Double Hundreds', batting.double_hundreds || 0],
        ['Fours', batting.fours || 0],
        ['Sixes', batting.sixes || 0],
        [''],
        ['BOWLING STATISTICS'],
        ['Innings', bowling.innings || 0],
        ['Overs', bowling.overs || 0],
        ['Wickets', bowling.wickets || 0],
        ['Average', bowling.average || 0],
        ['Economy', bowling.economy || 0],
        ['Strike Rate', bowling.strike_rate || 0],
        ['Best Bowling', bowling.best_bowling || 0],
        ['5 Wickets', bowling.five_wickets || 0]
    ];
    
    return data.map(row => row.join(',')).join('\n');
}

function updatePhaseAnalysis(phaseData, matchesData) {
    if (!phaseData) return;
    
    // Determine which format to show based on available data
    const hasT20Data = phaseData.t20_phases && Object.values(phaseData.t20_phases).some(phase => 
        phase.runs > 0 || phase.wickets > 0 || phase.dismissals > 0 || phase.conceded > 0
    );
    
    const hasOdiData = phaseData.odi_phases && Object.values(phaseData.odi_phases).some(phase => 
        phase.runs > 0 || phase.wickets > 0 || phase.dismissals > 0 || phase.conceded > 0
    );
    
    // Show/hide appropriate phase sections
    const t20Section = document.getElementById('t20PhaseAnalysis');
    const odiSection = document.getElementById('odiPhaseAnalysis');
    
    if (hasT20Data) {
        t20Section.style.display = 'block';
        updateT20Phases(phaseData.t20_phases);
    } else {
        t20Section.style.display = 'none';
    }
    
    if (hasOdiData) {
        odiSection.style.display = 'block';
        updateOdiPhases(phaseData.odi_phases);
    } else {
        odiSection.style.display = 'none';
    }
}

function updateT20Phases(t20Phases) {
    const phases = ['phase1', 'phase2', 'phase3', 'phase4'];
    
    phases.forEach((phase, index) => {
        const phaseNum = index + 1;
        const phaseData = t20Phases[phase] || { runs: 0, wickets: 0, dismissals: 0, conceded: 0, batting_innings: 0, balls: 0 };
        const avgRuns = phaseData.batting_innings > 0 ? (phaseData.runs / phaseData.batting_innings) : 0;
        const sr = phaseData.balls > 0 ? ((phaseData.runs / phaseData.balls) * 100) : 0;
    document.getElementById(`t20Phase${phaseNum}Runs`).textContent = `${Math.round(avgRuns)} avg`;
        document.getElementById(`t20Phase${phaseNum}Wickets`).textContent = phaseData.wickets || 0;
        document.getElementById(`t20Phase${phaseNum}Dismissals`).textContent = phaseData.dismissals || 0;
        document.getElementById(`t20Phase${phaseNum}Conceded`).textContent = phaseData.conceded || 0;
    document.getElementById(`t20Phase${phaseNum}SR`).textContent = (phaseData.strike_rate ?? 0).toFixed ? (phaseData.strike_rate).toFixed(1) : (phaseData.strike_rate || 0);
        // Optionally append SR next to runs label if UI supports
    });
}

function updateOdiPhases(odiPhases) {
    const phases = ['phase1', 'phase2', 'phase3', 'phase4', 'phase5'];
    
    phases.forEach((phase, index) => {
        const phaseNum = index + 1;
        const phaseData = odiPhases[phase] || { runs: 0, wickets: 0, dismissals: 0, conceded: 0, batting_innings: 0, balls: 0 };
        const avgRuns = phaseData.batting_innings > 0 ? (phaseData.runs / phaseData.batting_innings) : 0;
        const sr = phaseData.balls > 0 ? ((phaseData.runs / phaseData.balls) * 100) : 0;
    document.getElementById(`odiPhase${phaseNum}Runs`).textContent = `${Math.round(avgRuns)} avg`;
        document.getElementById(`odiPhase${phaseNum}Wickets`).textContent = phaseData.wickets || 0;
        document.getElementById(`odiPhase${phaseNum}Dismissals`).textContent = phaseData.dismissals || 0;
        document.getElementById(`odiPhase${phaseNum}Conceded`).textContent = phaseData.conceded || 0;
    document.getElementById(`odiPhase${phaseNum}SR`).textContent = (phaseData.strike_rate ?? 0).toFixed ? (phaseData.strike_rate).toFixed(1) : (phaseData.strike_rate || 0);
    });
}

// Rivalry Analysis Function
function updateRivalryAnalysis(rivalryData) {
    if (!rivalryData) {
        // Clear all rivalry sections
        document.getElementById('mostRunsAgainst').innerHTML = '<p class="text-muted">No rivalry data available</p>';
        document.getElementById('mostWicketsAgainst').innerHTML = '<p class="text-muted">No rivalry data available</p>';
        document.getElementById('mostRunsConcededTo').innerHTML = '<p class="text-muted">No rivalry data available</p>';
        document.getElementById('mostDismissalsBy').innerHTML = '<p class="text-muted">No rivalry data available</p>';
        return;
    }
    
    // Most runs scored against opponents
    if (rivalryData.most_runs_against && rivalryData.most_runs_against.length > 0) {
        const runsAgainstHtml = rivalryData.most_runs_against.map(item => `
            <div class="rivalry-item">
                <span class="rivalry-opponent">${item.opponent}</span>
                <span class="rivalry-stats">${item.runs} runs in ${item.matches} matches</span>
            </div>
        `).join('');
        document.getElementById('mostRunsAgainst').innerHTML = runsAgainstHtml;
    } else {
        document.getElementById('mostRunsAgainst').innerHTML = '<p class="text-muted">No batting rivalry data</p>';
    }
    
    // Most wickets taken against opponents
    if (rivalryData.most_wickets_against && rivalryData.most_wickets_against.length > 0) {
        const wicketsAgainstHtml = rivalryData.most_wickets_against.map(item => `
            <div class="rivalry-item">
                <span class="rivalry-opponent">${item.opponent}</span>
                <span class="rivalry-stats">${item.wickets} wickets in ${item.matches} matches</span>
            </div>
        `).join('');
        document.getElementById('mostWicketsAgainst').innerHTML = wicketsAgainstHtml;
    } else {
        document.getElementById('mostWicketsAgainst').innerHTML = '<p class="text-muted">No bowling rivalry data</p>';
    }
    
    // Most runs conceded to opponents
    if (rivalryData.most_runs_conceded_to && rivalryData.most_runs_conceded_to.length > 0) {
        const runsConcededHtml = rivalryData.most_runs_conceded_to.map(item => `
            <div class="rivalry-item">
                <span class="rivalry-opponent">${item.opponent}</span>
                <span class="rivalry-stats">${item.runs} runs conceded in ${item.matches} matches</span>
            </div>
        `).join('');
        document.getElementById('mostRunsConcededTo').innerHTML = runsConcededHtml;
    } else {
        document.getElementById('mostRunsConcededTo').innerHTML = '<p class="text-muted">No bowling struggle data</p>';
    }
    
    // Most dismissals by opponents
    if (rivalryData.most_dismissals_by && rivalryData.most_dismissals_by.length > 0) {
        const dismissalsHtml = rivalryData.most_dismissals_by.map(item => `
            <div class="rivalry-item">
                <span class="rivalry-opponent">${item.opponent}</span>
                <span class="rivalry-stats">Dismissed ${item.dismissals} times in ${item.matches} matches</span>
            </div>
        `).join('');
        document.getElementById('mostDismissalsBy').innerHTML = dismissalsHtml;
    } else {
        document.getElementById('mostDismissalsBy').innerHTML = '<p class="text-muted">No batting struggle data</p>';
    }
}