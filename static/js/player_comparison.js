// Player Comparison JavaScript

let availableYears = [];
let selectedYears = [];
let allPlayers = [];
let allCountries = [];
let currentComparisonData = null;
let currentPhaseRole = 'P1Bat';

document.addEventListener('DOMContentLoaded', function() {
    loadInitialData();
    setupEventListeners();
});

function loadInitialData() {
    // Load available years
    fetch('/api/data/years')
        .then(response => response.json())
        .then(data => {
            if (data.years) {
                availableYears = data.years;
                populateYearFilter();
            }
        })
        .catch(error => console.error('Error loading years:', error));
    
    // Load available players
    fetch('/api/data/players')
        .then(response => response.json())
        .then(data => {
            if (data.players) {
                allPlayers = data.players;
                populatePlayersList();
            }
        })
        .catch(error => console.error('Error loading players:', error));
        
    // Load available venues
    fetch('/api/all-venues')
        .then(response => response.json())
        .then(data => {
            if (data.venues) {
                populateVenueFilter(data.venues);
            }
        })
        .catch(error => console.error('Error loading venues:', error));

    // Load available countries
    fetch('/api/all-countries')
        .then(response => response.json())
        .then(data => {
            if (data.countries) {
                allCountries = data.countries;
                populateCountryFilter(allCountries);
            }
        })
        .catch(error => console.error('Error loading countries:', error));
}

function populateVenueFilter(venues) {
    const venueFilter = document.getElementById('venueFilter');
    venues.sort().forEach(venue => {
        const option = document.createElement('option');
        option.value = venue;
        option.textContent = venue;
        venueFilter.appendChild(option);
    });
}

function populateYearFilter() {
    const yearFilterOptions = document.getElementById('yearFilterOptions');
    yearFilterOptions.innerHTML = '';
    
    // Add "All Years" option
    const allOption = document.createElement('div');
    allOption.className = 'multi-select-option';
    allOption.innerHTML = `
        <input type="checkbox" id="year_all" onchange="handleAllYearsToggle(this)">
        <label for="year_all">All Years</label>
    `;
    yearFilterOptions.appendChild(allOption);
    
    // Add individual year options
    availableYears.forEach(year => {
        const option = document.createElement('div');
        option.className = 'multi-select-option';
        option.innerHTML = `
            <input type="checkbox" id="year_${year}" value="${year}" onchange="handleYearSelection(this)">
            <label for="year_${year}">${year}</label>
        `;
        yearFilterOptions.appendChild(option);
    });
}

function populateCountryFilter(countries) {
    const countryFilter = document.getElementById('countryFilter');
    countries.sort().forEach(country => {
        const option = document.createElement('option');
        option.value = country;
        option.textContent = country;
        countryFilter.appendChild(option);
    });
}
function populatePlayersList() {
    const playersList1 = document.getElementById('playersList1');
    const playersList2 = document.getElementById('playersList2');
    
    playersList1.innerHTML = '';
    playersList2.innerHTML = '';
    
    allPlayers.forEach(player => {
        const option1 = document.createElement('option');
        option1.value = player;
        playersList1.appendChild(option1);
        
        const option2 = document.createElement('option');
        option2.value = player;
        playersList2.appendChild(option2);
    });
}

function setupEventListeners() {
    // Year filter dropdown toggle
    document.getElementById('yearFilterButton').addEventListener('click', function() {
        const options = document.getElementById('yearFilterOptions');
        options.style.display = options.style.display === 'block' ? 'none' : 'block';
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(event) {
        const dropdown = document.querySelector('.multi-select-dropdown');
        if (!dropdown.contains(event.target)) {
            document.getElementById('yearFilterOptions').style.display = 'none';
        }
    });
    
    // Compare button
    document.getElementById('compareButton').addEventListener('click', comparePlayers);

        // Phase role toggle
        const roleP1Bat = document.getElementById('roleP1Bat');
        const roleP2Bat = document.getElementById('roleP2Bat');
        if (roleP1Bat && roleP2Bat) {
            roleP1Bat.addEventListener('change', () => { currentPhaseRole = 'P1Bat'; renderPhaseComparison(); });
            roleP2Bat.addEventListener('change', () => { currentPhaseRole = 'P2Bat'; renderPhaseComparison(); });
        }
    
    // Enter key handling
    document.getElementById('player1Search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            comparePlayers();
        }
    });
    
    document.getElementById('player2Search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            comparePlayers();
        }
    });
}

function handleAllYearsToggle(checkbox) {
    const yearCheckboxes = document.querySelectorAll('input[id^="year_"]:not(#year_all)');
    
    if (checkbox.checked) {
        selectedYears = [];
        yearCheckboxes.forEach(cb => cb.checked = false);
        updateYearFilterText();
    }
}

function handleYearSelection(checkbox) {
    const allYearsCheckbox = document.getElementById('year_all');
    
    if (checkbox.checked) {
        allYearsCheckbox.checked = false;
        if (!selectedYears.includes(checkbox.value)) {
            selectedYears.push(checkbox.value);
        }
    } else {
        selectedYears = selectedYears.filter(year => year !== checkbox.value);
        if (selectedYears.length === 0) {
            allYearsCheckbox.checked = true;
        }
    }
    
    updateYearFilterText();
}

function updateYearFilterText() {
    const yearFilterText = document.getElementById('yearFilterText');
    const allYearsCheckbox = document.getElementById('year_all');
    
    if (allYearsCheckbox.checked || selectedYears.length === 0) {
        yearFilterText.textContent = 'All Years';
    } else if (selectedYears.length === 1) {
        yearFilterText.textContent = selectedYears[0];
    } else if (selectedYears.length <= 3) {
        yearFilterText.textContent = selectedYears.join(', ');
    } else {
        yearFilterText.textContent = `${selectedYears.length} years selected`;
    }
}

function comparePlayers() {
    const player1 = document.getElementById('player1Search').value.trim();
    const player2 = document.getElementById('player2Search').value.trim();
    const format = document.getElementById('formatFilter').value;
    const inningsType = document.getElementById('inningsTypeFilter').value;
    const venue = document.getElementById('venueFilter').value;
    const matchCategory = document.getElementById('matchCategoryFilter').value;
    const battingOrder = document.getElementById('battingOrderFilter').value;
    const country = document.getElementById('countryFilter').value;
    
    if (!player1) {
        showError('Please enter the first player name');
        return;
    }
    
    if (!player2) {
        showError('Please enter the second player name');
        return;
    }
    
    if (player1 === player2) {
        showError('Please select two different players');
        return;
    }
    
    // Build filters
    const filters = {};
    if (format) filters.format = format;
    if (inningsType) filters.innings_type = inningsType;
    if (venue) filters.venue = venue;
        if (matchCategory) filters.match_category = matchCategory;
        if (battingOrder) filters.batting_order = battingOrder;
        if (country) filters.country = country;
    if (selectedYears.length > 0) filters.years = selectedYears;
    
    // Show loading
    showLoading();
    hideError();
    hideResults();
    
    // Make API call
    const params = new URLSearchParams({
        player1: player1,
        player2: player2
    });
    
    if (Object.keys(filters).length > 0) {
        params.append('filters', JSON.stringify(filters));
    }
    
    fetch(`/api/players/compare?${params}`)
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.error) {
                showError(data.error);
            } else {
                    currentComparisonData = data;
                    displayComparisonResults(data);
                    renderPhaseComparison();
                showActiveFilters(filters);
            }
        })
        .catch(error => {
            hideLoading();
            showError('Error comparing players: ' + error.message);
        });
}

function displayComparisonResults(data) {
    // Update player names
    document.getElementById('player1Name').textContent = data.player1.name;
    document.getElementById('player2Name').textContent = data.player2.name;
    document.getElementById('player1StatsTitle').textContent = `${data.player1.name} Statistics`;
    document.getElementById('player2StatsTitle').textContent = `${data.player2.name} Statistics`;
    
    // Display head-to-head summary
    displayHeadToHeadSummary(data.head_to_head);
    
    // Display head-to-head performance
    displayHeadToHeadPerformance(data.head_to_head, data.player1.name, data.player2.name);
    
    // Display overall comparison
    displayOverallComparison(data.comparison_metrics, data.player1.name, data.player2.name);
    
    // Display individual stats
    displayIndividualStats(data.player1.stats, 'player1Stats');
    displayIndividualStats(data.player2.stats, 'player2Stats');
    
    document.getElementById('comparisonResults').style.display = 'block';
}

function displayHeadToHeadSummary(headToHead) {
    const container = document.getElementById('h2hSummary');
    
    if (headToHead.total_encounters === 0) {
        container.innerHTML = `
            <div class="match-result-summary">
                <h5 class="text-warning">No Direct Encounters Found</h5>
                <p>These players have not faced each other in the available match data.</p>
            </div>
        `;
        return;
    }
    
    const matchResults = headToHead.match_results;
    const totalMatches = matchResults.player1_wins + matchResults.player2_wins + matchResults.ties;
    
    container.innerHTML = `
        <div class="match-result-summary">
            <h5>Total Encounters: ${headToHead.total_encounters} matches</h5>
            <div class="mt-3">
                <span class="result-stat">
                    <strong>Player 1 Wins:</strong> ${matchResults.player1_wins}
                </span>
                <span class="result-stat">
                    <strong>Player 2 Wins:</strong> ${matchResults.player2_wins}
                </span>
                ${matchResults.ties > 0 ? `<span class="result-stat"><strong>Ties:</strong> ${matchResults.ties}</span>` : ''}
            </div>
        </div>
    `;
}

function displayHeadToHeadPerformance(headToHead, player1Name, player2Name) {
    displayPlayerVsPerformance(headToHead.player1_vs_player2, 'player1VsPlayer2', player1Name, player2Name);
    displayPlayerVsPerformance(headToHead.player2_vs_player1, 'player2VsPlayer1', player2Name, player1Name);
}

function displayPlayerVsPerformance(performance, containerId, batterName, bowlerName) {
    const container = document.getElementById(containerId);
    
    if (!performance || (performance.as_batsman.balls === 0 && performance.as_bowler.runs_conceded === 0)) {
        container.innerHTML = '<p class="text-muted">No head-to-head data available</p>';
        return;
    }
    
    let html = '';
    
    // Batting performance
    if (performance.as_batsman.balls > 0) {
        html += `
            <div class="h2h-stat-card">
                <h6><i class="fas fa-bat me-2"></i>${batterName} batting vs ${bowlerName}</h6>
                <div class="comparison-stat">
                    <span class="stat-label">Runs</span>
                    <span class="stat-value">${performance.as_batsman.runs}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Balls</span>
                    <span class="stat-value">${performance.as_batsman.balls}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Strike Rate</span>
                    <span class="stat-value">${performance.as_batsman.strike_rate}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Average</span>
                    <span class="stat-value">${performance.as_batsman.average}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Boundaries</span>
                    <span class="stat-value">${performance.as_batsman.boundaries}/${performance.as_batsman.sixes}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Dismissals</span>
                    <span class="stat-value">${performance.as_batsman.dismissals}</span>
                </div>
            </div>
        `;
    }
    
    // Bowling performance
    if (performance.as_bowler.runs_conceded > 0) {
        html += `
            <div class="h2h-stat-card">
                <h6><i class="fas fa-baseball-ball me-2"></i>${batterName.replace(bowlerName, bowlerName)} bowling vs ${bowlerName.replace(batterName, batterName)}</h6>
                <div class="comparison-stat">
                    <span class="stat-label">Overs</span>
                    <span class="stat-value">${performance.as_bowler.overs}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Runs</span>
                    <span class="stat-value">${performance.as_bowler.runs_conceded}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Wickets</span>
                    <span class="stat-value">${performance.as_bowler.wickets}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Economy</span>
                    <span class="stat-value">${performance.as_bowler.economy}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Average</span>
                    <span class="stat-value">${performance.as_bowler.average}</span>
                </div>
            </div>
        `;
    }
    
    if (!html) {
        html = '<p class="text-muted">No head-to-head performance data available</p>';
    }
    
    container.innerHTML = html;
}

function displayOverallComparison(metrics, player1Name, player2Name) {
    const container = document.getElementById('overallComparison');
    
    if (!metrics || (!metrics.batting_comparison && !metrics.bowling_comparison)) {
        container.innerHTML = '<p class="text-muted">No comparison metrics available</p>';
        return;
    }
    
    let html = '';
    
    // Batting comparison
    if (metrics.batting_comparison) {
        html += `
            <div class="h2h-stat-card">
                <h6><i class="fas fa-bat me-2"></i>Batting Comparison</h6>
        `;
        
        Object.entries(metrics.batting_comparison).forEach(([stat, data]) => {
            const player1Value = data.player1;
            const player2Value = data.player2;
            const better = data.better;
            
            html += `
                <div class="comparison-stat">
                    <span class="stat-value ${better === 'player1' ? 'winner' : ''}">${player1Value}</span>
                    <span class="stat-label">${stat.replace('_', ' ').toUpperCase()}</span>
                    <span class="stat-value ${better === 'player2' ? 'winner' : ''}">${player2Value}</span>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    // Bowling comparison
    if (metrics.bowling_comparison) {
        html += `
            <div class="h2h-stat-card">
                <h6><i class="fas fa-baseball-ball me-2"></i>Bowling Comparison</h6>
        `;
        
        Object.entries(metrics.bowling_comparison).forEach(([stat, data]) => {
            const player1Value = data.player1;
            const player2Value = data.player2;
            const better = data.better;
            
            html += `
                <div class="comparison-stat">
                    <span class="stat-value ${better === 'player1' ? 'winner' : ''}">${player1Value}</span>
                    <span class="stat-label">${stat.replace('_', ' ').toUpperCase()}</span>
                    <span class="stat-value ${better === 'player2' ? 'winner' : ''}">${player2Value}</span>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    container.innerHTML = html;
}

function displayIndividualStats(stats, containerId) {
    const container = document.getElementById(containerId);
    
    if (!stats || stats.error) {
        container.innerHTML = `<p class="text-muted">${stats?.error || 'No statistics available'}</p>`;
        return;
    }
    
    let html = '';
    
    // Batting stats
    if (stats.batting && stats.batting.matches > 0) {
        html += `
            <div class="h2h-stat-card">
                <h6><i class="fas fa-bat me-2"></i>Batting</h6>
                <div class="comparison-stat">
                    <span class="stat-label">Matches</span>
                    <span class="stat-value">${stats.batting.matches}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Runs</span>
                    <span class="stat-value">${stats.batting.runs}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Average</span>
                    <span class="stat-value">${stats.batting.average}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Strike Rate</span>
                    <span class="stat-value">${stats.batting.strike_rate}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Hundreds</span>
                    <span class="stat-value">${stats.batting.hundreds}</span>
                </div>
            </div>
        `;
    }
    
    // Bowling stats
    if (stats.bowling && stats.bowling.matches > 0) {
        html += `
            <div class="h2h-stat-card">
                <h6><i class="fas fa-baseball-ball me-2"></i>Bowling</h6>
                <div class="comparison-stat">
                    <span class="stat-label">Matches</span>
                    <span class="stat-value">${stats.bowling.matches}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Wickets</span>
                    <span class="stat-value">${stats.bowling.wickets}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Economy</span>
                    <span class="stat-value">${stats.bowling.economy}</span>
                </div>
                <div class="comparison-stat">
                    <span class="stat-label">Average</span>
                    <span class="stat-value">${stats.bowling.average}</span>
                </div>
            </div>
        `;
    }
    
    if (!html) {
        html = '<p class="text-muted">No statistics available</p>';
    }
    
    container.innerHTML = html;
}

function showActiveFilters(filters) {
    const container = document.getElementById('activeFilters');
    const tagsContainer = document.getElementById('filterTags');
    
    if (Object.keys(filters).length === 0) {
        container.style.display = 'none';
        return;
    }
    
    let tagsHtml = '';
    
    if (filters.format) {
        tagsHtml += `<span class="badge bg-primary me-2 mb-2">Format: ${filters.format}</span>`;
    }
    
    if (filters.years) {
        const yearText = filters.years.length <= 3 ? filters.years.join(', ') : `${filters.years.length} years`;
        tagsHtml += `<span class="badge bg-info me-2 mb-2">Years: ${yearText}</span>`;
    }
    
    tagsContainer.innerHTML = tagsHtml;
    container.style.display = 'block';
}

function showLoading() {
    document.getElementById('loadingSpinner').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loadingSpinner').style.display = 'none';
}

function showError(message) {
    document.getElementById('errorText').textContent = message;
    document.getElementById('errorMessage').style.display = 'block';
}

function hideError() {
    document.getElementById('errorMessage').style.display = 'none';
}

function hideResults() {
    document.getElementById('comparisonResults').style.display = 'none';
}

function renderPhaseComparison() {
    const container = document.getElementById('phaseComparison');
    if (!container) return;
    if (!currentComparisonData) {
        container.innerHTML = '<p class="text-muted">Compare players to see phase-wise breakdown.</p>';
        return;
    }

    // Pick which direction to show based on role selection
    const p1 = currentComparisonData.player1;
    const p2 = currentComparisonData.player2;

    // We'll use each player's phase_analysis to show batting vs bowling context textually.
    // If format filter applied is T20I/ODI, prioritize that, else show both if available.
    const filters = currentComparisonData.filters_applied || {};
    const format = filters.format || '';

    const p1Phases = p1.stats.phase_analysis || {};
    const p2Phases = p2.stats.phase_analysis || {};

    function buildPhaseRows(labelPrefix, batPhases, bowlPhases, isT20) {
        const rows = [];
        const keys = isT20 ? ['phase1','phase2','phase3','phase4'] : ['phase1','phase2','phase3','phase4','phase5'];
        keys.forEach((k, idx) => {
            const bp = (batPhases && batPhases[k]) || { runs: 0, dismissals: 0 };
            const bw = (bowlPhases && bowlPhases[k]) || { wickets: 0, conceded: 0 };
            const phaseName = isT20
                ? ['Powerplay (1-6)','Middle (7-12)','Late Middle (13-16)','Death (17-20)'][idx]
                : ['PP1 (1-10)','Middle1 (11-20)','Middle2 (21-30)','Middle3 (31-40)','Death (41-50)'][idx];
            rows.push(`
                <div class="comparison-stat">
                    <span class="stat-label">${labelPrefix} ${phaseName}</span>
                    <span class="stat-value">Bat: ${bp.runs} r / ${bp.dismissals} out</span>
                    <span class="stat-value">Bowl: ${bw.wickets} w / ${bw.conceded} r</span>
                </div>
            `);
        });
        return rows.join('');
    }

    let html = '';
    if (!format || format === 'T20' || format === 'T20I') {
        // Role selection: if P1Bat, show P1 batting phases and P2 bowling phases aligned
        const p1Bat = p1Phases.t20_phases || {};
        const p2Bowl = p2Phases.t20_phases || {};
        const p2Bat = p2Phases.t20_phases || {};
        const p1Bowl = p1Phases.t20_phases || {};
        html += `<div class="h2h-stat-card">
            <h6><i class="fas fa-stopwatch me-2"></i>T20 Phases</h6>
            ${currentPhaseRole === 'P1Bat' 
                ? buildPhaseRows(`${p1.name} bat vs ${p2.name} bowl -`, p1Bat, p2Bowl, true)
                : buildPhaseRows(`${p2.name} bat vs ${p1.name} bowl -`, p2Bat, p1Bowl, true)}
        </div>`;
    }

    if (!format || format === 'ODI') {
        const p1BatO = p1Phases.odi_phases || {};
        const p2BowlO = p2Phases.odi_phases || {};
        const p2BatO = p2Phases.odi_phases || {};
        const p1BowlO = p1Phases.odi_phases || {};
        html += `<div class="h2h-stat-card">
            <h6><i class="fas fa-hourglass-half me-2"></i>ODI Phases</h6>
            ${currentPhaseRole === 'P1Bat' 
                ? buildPhaseRows(`${p1.name} bat vs ${p2.name} bowl -`, p1BatO, p2BowlO, false)
                : buildPhaseRows(`${p2.name} bat vs ${p1.name} bowl -`, p2BatO, p1BowlO, false)}
        </div>`;
    }

    container.innerHTML = html || '<p class="text-muted">No phase-wise data available for selected filters.</p>';
}