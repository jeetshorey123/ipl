// Enhanced Players Analysis JavaScript

let availableYears = [];
let selectedYears = [];
let allPlayers = [];
let runDistributionChart = null;

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

function populatePlayersList() {
    const playersList = document.getElementById('playersList');
    playersList.innerHTML = '';
    
    allPlayers.forEach(player => {
        const option = document.createElement('option');
        option.value = player;
        playersList.appendChild(option);
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
    
    // Search button
    document.getElementById('searchButton').addEventListener('click', analyzePlayer);
    
    // Enter key in player search
    document.getElementById('playerSearch').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            analyzePlayer();
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

function analyzePlayer() {
    const playerName = document.getElementById('playerSearch').value.trim();
    const format = document.getElementById('formatFilter').value;
    const inningsType = document.getElementById('inningsTypeFilter').value;
    const venue = document.getElementById('venueFilter').value;
    
    if (!playerName) {
        showError('Please enter a player name');
        return;
    }
    
    // Build filters
    const filters = {};
    if (format) filters.format = format;
    if (inningsType) filters.innings_type = inningsType;
    if (venue) filters.venue = venue;
    if (selectedYears.length > 0) filters.years = selectedYears;
    
    // Show loading
    showLoading();
    hideError();
    hideResults();
    
    // Make API call
    const url = `/api/players/${encodeURIComponent(playerName)}`;
    const params = new URLSearchParams();
    if (Object.keys(filters).length > 0) {
        params.append('filters', JSON.stringify(filters));
    }
    
    fetch(`${url}?${params}`)
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.error) {
                showError(data.error);
            } else {
                displayPlayerStats(data);
                showActiveFilters(filters);
            }
        })
        .catch(error => {
            hideLoading();
            showError('Error fetching player data: ' + error.message);
        });
}

function displayPlayerStats(data) {
    displayBattingStats(data.batting);
    displayBowlingStats(data.bowling);
    displayMatchStats(data.matches);
    displayAdvancedAnalysis(data.advanced_analysis);
    displayRunDistributionChart(data.batting.run_distribution);
    
    document.getElementById('playerResults').style.display = 'block';
}

function displayBattingStats(batting) {
    const container = document.getElementById('battingStats');
    
    if (!batting || batting.matches === 0) {
        container.innerHTML = '<p class="text-muted">No batting data available</p>';
        return;
    }
    
    container.innerHTML = `
        <div class="stat-item">
            <span class="stat-label">Matches</span>
            <span class="stat-value">${batting.matches}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Innings</span>
            <span class="stat-value">${batting.innings}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Runs</span>
            <span class="stat-value">${batting.runs}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Average</span>
            <span class="stat-value">${batting.average}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Strike Rate</span>
            <span class="stat-value">${batting.strike_rate}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">High Score</span>
            <span class="stat-value">${batting.high_score}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Boundaries (4s/6s)</span>
            <span class="stat-value">${batting.fours}/${batting.sixes}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Fifties</span>
            <span class="stat-value">${batting.fifties}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Hundreds</span>
            <span class="stat-value">${batting.hundreds}</span>
        </div>
    `;
}

function displayBowlingStats(bowling) {
    const container = document.getElementById('bowlingStats');
    
    if (!bowling || bowling.matches === 0) {
        container.innerHTML = '<p class="text-muted">No bowling data available</p>';
        return;
    }
    
    container.innerHTML = `
        <div class="stat-item">
            <span class="stat-label">Matches</span>
            <span class="stat-value">${bowling.matches}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Innings</span>
            <span class="stat-value">${bowling.innings}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Overs</span>
            <span class="stat-value">${bowling.overs}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Wickets</span>
            <span class="stat-value">${bowling.wickets}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Average</span>
            <span class="stat-value">${bowling.average}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Economy</span>
            <span class="stat-value">${bowling.economy}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Strike Rate</span>
            <span class="stat-value">${bowling.strike_rate}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Best Bowling</span>
            <span class="stat-value">${bowling.best_bowling}</span>
        </div>
    `;
}

function displayMatchStats(matches) {
    const container = document.getElementById('matchStats');
    
    if (!matches) {
        container.innerHTML = '<p class="text-muted">No match data available</p>';
        return;
    }
    
    container.innerHTML = `
        <h6 class="mb-3">Batting First</h6>
        <div class="stat-item">
            <span class="stat-label">Matches</span>
            <span class="stat-value">${matches.batting_first.matches}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Avg Runs</span>
            <span class="stat-value">${matches.batting_first.batting_stats.average}</span>
        </div>
        
        <h6 class="mb-3 mt-4">Bowling First</h6>
        <div class="stat-item">
            <span class="stat-label">Matches</span>
            <span class="stat-value">${matches.bowling_first.matches}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Avg Runs</span>
            <span class="stat-value">${matches.bowling_first.batting_stats.average}</span>
        </div>
    `;
}

function displayAdvancedAnalysis(analysis) {
    const container = document.getElementById('advancedAnalysis');
    
    if (!analysis) {
        container.innerHTML = '<p class="text-muted">No advanced analysis available</p>';
        return;
    }
    
    let html = '';
    
    // Win Percentage
    if (analysis.win_percentage) {
        html += `
            <div class="analysis-section">
                <h5><i class="fas fa-trophy me-2"></i>Win Percentage</h5>
                <p><strong>${analysis.win_percentage.percentage}%</strong> (${analysis.win_percentage.wins}/${analysis.win_percentage.total_games} matches)</p>
            </div>
        `;
    }
    
    // Batting Positions
    if (analysis.batting_positions && Object.keys(analysis.batting_positions).length > 0) {
        html += `
            <div class="analysis-section">
                <h5><i class="fas fa-sort-numeric-up me-2"></i>Batting Position Analysis</h5>
                <div class="position-stats">
        `;
        
        Object.entries(analysis.batting_positions).forEach(([position, stats]) => {
            html += `
                <div class="position-item">
                    <h6>Position ${position}</h6>
                    <p><strong>Innings:</strong> ${stats.innings}</p>
                    <p><strong>Runs:</strong> ${stats.runs}</p>
                    <p><strong>Average:</strong> ${stats.average}</p>
                    <p><strong>Runs/Innings:</strong> ${stats.runs_per_innings}</p>
                </div>
            `;
        });
        
        html += '</div></div>';
    }
    
    // Dismissal Patterns
    if (analysis.dismissal_patterns && Object.keys(analysis.dismissal_patterns).length > 0) {
        html += `
            <div class="analysis-section">
                <h5><i class="fas fa-times-circle me-2"></i>Dismissal Patterns</h5>
        `;
        
        const totalDismissals = Object.values(analysis.dismissal_patterns).reduce((a, b) => a + b, 0);
        Object.entries(analysis.dismissal_patterns).forEach(([type, count]) => {
            const percentage = ((count / totalDismissals) * 100).toFixed(1);
            html += `
                <div class="dismissal-pattern">
                    <span>${type}</span>
                    <span><strong>${count}</strong> (${percentage}%)</span>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    // Performance by Opposition
    if (analysis.performance_by_opposition && Object.keys(analysis.performance_by_opposition).length > 0) {
        html += `
            <div class="analysis-section">
                <h5><i class="fas fa-users me-2"></i>Performance vs Opposition</h5>
                <div class="opposition-stats">
        `;
        
        Object.entries(analysis.performance_by_opposition).forEach(([team, stats]) => {
            html += `
                <div class="opposition-item">
                    <h6>vs ${team}</h6>
                    <p><strong>Matches:</strong> ${stats.matches}</p>
                    <p><strong>Runs:</strong> ${stats.runs}</p>
                    <p><strong>Average:</strong> ${stats.average}</p>
                    <p><strong>Runs/Innings:</strong> ${stats.runs_per_innings}</p>
                </div>
            `;
        });
        
        html += '</div></div>';
    }
    
    container.innerHTML = html || '<p class="text-muted">No advanced analysis data available</p>';
}

function displayRunDistributionChart(runDistribution) {
    const ctx = document.getElementById('runDistributionChart').getContext('2d');
    
    if (runDistributionChart) {
        runDistributionChart.destroy();
    }
    
    if (!runDistribution) {
        return;
    }
    
    runDistributionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Dots', 'Singles', 'Doubles', 'Fours', 'Sixes'],
            datasets: [{
                data: [
                    runDistribution.dots || 0,
                    runDistribution.ones || 0,
                    runDistribution.twos || 0,
                    runDistribution.fours || 0,
                    runDistribution.sixes || 0
                ],
                backgroundColor: [
                    '#FF6B6B',
                    '#4ECDC4',
                    '#45B7D1',
                    '#96CEB4',
                    '#FECA57'
                ],
                borderWidth: 2,
                borderColor: '#1a1a1a'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#ffffff',
                        padding: 15
                    }
                }
            }
        }
    });
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
    document.getElementById('playerResults').style.display = 'none';
}