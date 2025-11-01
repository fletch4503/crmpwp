// Load dashboard data
document.addEventListener('DOMContentLoaded', function () {
    loadDashboardStats();
    loadRecentActivity();

    // Check system status
    checkSystemStatus();
});

function loadDashboardStats() {
    fetch('/api/dashboard/stats/')
        .then(response => response.json())
        .then(data => {
            // Update stats cards
            updateStatsCards(data);
        })
        .catch(error => console.error('Error loading stats:', error));
}

function loadRecentActivity() {
    fetch('/api/dashboard/recent-activity/')
        .then(response => response.json())
        .then(data => {
            updateRecentActivity(data);
        })
        .catch(error => console.error('Error loading activity:', error));
}

function checkSystemStatus() {
    fetch('/api/system/health/')
        .then(response => response.json())
        .then(data => {
            updateSystemStatus(data);
        })
        .catch(error => console.error('Error checking system status:', error));
}

function updateStatsCards(data) {
    // Update the stats display
    const statsElements = document.querySelectorAll('[data-stat]');
    statsElements.forEach(element => {
        const statName = element.getAttribute('data-stat');
        if (data[statName] !== undefined) {
            element.textContent = data[statName];
        }
    });
}

function updateRecentActivity(data) {
    const activityContainer = document.getElementById('recent-activity');
    if (data.activities && data.activities.length > 0) {
        activityContainer.innerHTML = data.activities.map(activity => `
        <div class="flex items-center space-x-2 text-sm">
            <i class="fas fa-${activity.icon} text-${activity.color}-500"></i>
            <span>${activity.description}</span>
            <span class="text-xs text-base-content/50">${activity.time}</span>
        </div>
    `).join('');
    }
}

function updateSystemStatus(data) {
    // Update status indicators
    const statusMap = {
        'database': 'db-status',
        'redis': 'redis-status',
        'email_sync': 'email-status'
    };

    Object.keys(statusMap).forEach(key => {
        const status = data[key];
        const indicator = document.getElementById(statusMap[key]);
        const text = document.getElementById(statusMap[key] + '-text');

        if (status) {
            indicator.className = 'w-3 h-3 rounded-full bg-success';
            text.textContent = 'OK';
        } else {
            indicator.className = 'w-3 h-3 rounded-full bg-error';
            text.textContent = 'Ошибка';
        }
    });
}

// Auto-refresh dashboard data every 600 seconds
setInterval(() => {
    loadDashboardStats();
    checkSystemStatus();
}, 600000);
