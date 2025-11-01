// WebSocket connection for notifications
const notificationSocket = new WebSocket(
    'ws://' + window.location.host + '/ws/notifications/'
);

notificationSocket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    handleRealtimeMessage(data);
};

notificationSocket.onclose = function (e) {
    console.log('Notification socket closed');
    // Reconnect after 120 seconds
    setTimeout(() => {
        location.reload();
    }, 120000);
};

function handleRealtimeMessage(data) {
    if (data.type === 'connection_established') {
        console.log('WebSocket connected:', data.message);
    } else if (data.type === 'email_received') {
        showNotification('Новый email', `От: ${data.sender}`, 'info');
        updateNotificationCount();
    } else if (data.type === 'project_created') {
        showNotification('Проект создан', data.title, 'success');
    } else if (data.type === 'contact_created') {
        showNotification('Контакт создан', data.name, 'success');
    } else if (data.type === 'system_notification') {
        showNotification(data.title, data.message, data.level);
    }
}

function showNotification(title, message, level = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${level} mb-2 notification-enter`;
    notification.innerHTML = `
        <div>
            <h3 class="font-bold">${title}</h3>
            <div class="text-xs">${message}</div>
        </div>
        <div class="flex-none">
            <button class="btn btn-sm btn-circle btn-ghost" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    const messagesDiv = document.getElementById('messages');
    messagesDiv.appendChild(notification);

    // Animate in
    setTimeout(() => {
        notification.classList.add('notification-enter-active');
    }, 10);

    // Auto remove after 2 seconds
    setTimeout(() => {
        notification.classList.remove('notification-enter-active');
        notification.classList.add('notification-exit-active');
        setTimeout(() => notification.remove(), 300);
    }, 2000);
}

function updateNotificationCount() {
    const countElement = document.getElementById('notification-count');
    const currentCount = parseInt(countElement.textContent || '0');
    countElement.textContent = currentCount + 1;
    countElement.classList.remove('hidden');
}
