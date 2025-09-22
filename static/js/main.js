// Main JavaScript for Cricket Analytics Hub

// Global variables
let chartInstances = {};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupGlobalSearch();
    setupCommonEventListeners();
    setupChartDefaults();
}

// Global Search
function setupGlobalSearch() {
    const globalSearch = document.getElementById('globalSearch');
    if (globalSearch) {
        globalSearch.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performGlobalSearch(this.value);
            }
        });
        
        globalSearch.addEventListener('input', debounce(function(e) {
            if (e.target.value.length > 2) {
                showSearchSuggestions(e.target.value);
            } else {
                hideSearchSuggestions();
            }
        }, 300));
    }
}

function performGlobalSearch(query) {
    if (!query.trim()) return;
    
    // Redirect to appropriate page based on search
    // This is a simple implementation - you could make it more sophisticated
    window.location.href = `/players?search=${encodeURIComponent(query)}`;
}

function showSearchSuggestions(query) {
    // Implementation for search suggestions
    console.log('Showing suggestions for:', query);
}

function hideSearchSuggestions() {
    // Hide search suggestions dropdown
}

// Common Event Listeners
function setupCommonEventListeners() {
    // Close any open dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            hideSearchSuggestions();
        }
    });
    
    // Handle form submissions
    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (form.classList.contains('ajax-form')) {
            e.preventDefault();
            handleAjaxForm(form);
        }
    });
}

// Chart Configuration
function setupChartDefaults() {
    // Ensure Chart.js is loaded before configuring
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded yet, skipping setup');
        return;
    }
    
    try {
        Chart.defaults.font.family = 'Inter, sans-serif';
        Chart.defaults.font.size = 12;
        Chart.defaults.color = '#6b7280';
        Chart.defaults.plugins.legend.position = 'bottom';
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.padding = 20;
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
    } catch (error) {
        console.error('Error setting up Chart defaults:', error);
    }
}

// Utility Functions

// Loading States
function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('d-none');
        overlay.classList.add('fade-in');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('d-none');
        overlay.classList.remove('fade-in');
    }
}

// Alerts
function showAlert(message, type = 'info', duration = 5000) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const container = document.querySelector('.container') || document.body;
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = alertHtml;
    
    container.insertBefore(alertDiv.firstElementChild, container.firstChild);
    
    if (duration > 0) {
        setTimeout(() => {
            const alert = container.querySelector('.alert');
            if (alert) {
                alert.remove();
            }
        }, duration);
    }
}

function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle',
        'primary': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Chart Utilities
function createPieChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    // Destroy existing chart if it exists
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }
    
    const defaultOptions = {
        type: 'pie',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    };
    
    const config = { ...defaultOptions, ...options };
    chartInstances[canvasId] = new Chart(ctx, config);
    return chartInstances[canvasId];
}

function createBarChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    // Destroy existing chart if it exists
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }
    
    const defaultOptions = {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: data.datasets.length > 1
                }
            }
        }
    };
    
    const config = { ...defaultOptions, ...options };
    chartInstances[canvasId] = new Chart(ctx, config);
    return chartInstances[canvasId];
}

function createLineChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    // Destroy existing chart if it exists
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }
    
    const defaultOptions = {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                }
            },
            elements: {
                line: {
                    tension: 0.4
                },
                point: {
                    radius: 4,
                    hoverRadius: 6
                }
            }
        }
    };
    
    const config = { ...defaultOptions, ...options };
    chartInstances[canvasId] = new Chart(ctx, config);
    return chartInstances[canvasId];
}

// Data Formatting Utilities
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function formatPercentage(value, total) {
    if (total === 0) return '0%';
    return ((value / total) * 100).toFixed(1) + '%';
}

function formatDecimal(num, places = 2) {
    return parseFloat(num).toFixed(places);
}

// Color palettes for charts
const chartColors = {
    primary: ['#1e40af', '#3b82f6', '#60a5fa', '#93c5fd', '#dbeafe'],
    success: ['#059669', '#10b981', '#34d399', '#6ee7b7', '#a7f3d0'],
    warning: ['#d97706', '#f59e0b', '#fbbf24', '#fcd34d', '#fef3c7'],
    info: ['#0891b2', '#06b6d4', '#22d3ee', '#67e8f9', '#a5f3fc'],
    mixed: ['#1e40af', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2']
};

function getChartColors(type = 'mixed', count = 5) {
    const colors = chartColors[type] || chartColors.mixed;
    return colors.slice(0, count);
}

// AJAX Form Handler
async function handleAjaxForm(form) {
    try {
        showLoading();
        
        const formData = new FormData(form);
        const method = form.method || 'POST';
        const action = form.action || window.location.href;
        
        const response = await fetch(action, {
            method: method,
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(result.message || 'Operation completed successfully!', 'success');
            if (result.redirect) {
                setTimeout(() => {
                    window.location.href = result.redirect;
                }, 1500);
            }
        } else {
            showAlert(result.message || 'An error occurred. Please try again.', 'danger');
        }
        
        hideLoading();
    } catch (error) {
        console.error('Form submission error:', error);
        showAlert('An error occurred. Please try again.', 'danger');
        hideLoading();
    }
}

// Export functions for use in other scripts
window.CricketAnalytics = {
    showLoading,
    hideLoading,
    showAlert,
    createPieChart,
    createBarChart,
    createLineChart,
    formatNumber,
    formatPercentage,
    formatDecimal,
    getChartColors,
    debounce
};