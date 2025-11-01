// WebSocket connection for real-time email updates
const emailSocket = new WebSocket(
    'ws://' + window.location.host + '/ws/emails/'
);

emailSocket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    handleEmailRealtimeUpdate(data);
};

function handleEmailRealtimeUpdate(data) {
    if (data.type === 'email_received') {
        // Refresh the email list
        location.reload();
    } else if (data.type === 'email_updated') {
        // Update specific email in the list
        updateEmailInList(data.email_id, data.action, data);
    }
}

function updateEmailInList(emailId, action, data) {
    const emailCard = document.querySelector(`[data-email-id="${emailId}"]`);
    if (emailCard) {
        if (action === 'marked_read') {
            emailCard.closest('.card').classList.add('opacity-50');
        } else if (action === 'toggled_important') {
            const starIcon = emailCard.querySelector('.fa-star');
            if (data.is_important) {
                starIcon.classList.remove('text-base-content/30');
                starIcon.classList.add('text-warning');
            } else {
                starIcon.classList.remove('text-warning');
                starIcon.classList.add('text-base-content/30');
            }
        }
    }
}

function markAsRead(emailId) {
    fetch(`/emails/ajax/${emailId}/mark-read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateEmailInList(emailId, 'marked_read', {});
                showNotification('Email помечен как прочитанный', '', 'success');
            }
        });
}

function toggleImportant(emailId) {
    fetch(`/emails/ajax/${emailId}/toggle-important/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateEmailInList(emailId, 'toggled_important', data);
                showNotification(
                    data.is_important ? 'Email помечен как важный' : 'Снята пометка важности',
                    '', 'success'
                );
            }
        });
}

function markSelectedAsRead() {
    const selectedEmails = document.querySelectorAll('.email-checkbox:checked');
    selectedEmails.forEach(checkbox => {
        markAsRead(checkbox.dataset.emailId);
    });
}

function markSelectedAsImportant() {
    const selectedEmails = document.querySelectorAll('.email-checkbox:checked');
    selectedEmails.forEach(checkbox => {
        toggleImportant(checkbox.dataset.emailId);
    });
}

function syncEmails() {
    fetch('/emails/ajax/sync-now/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Синхронизация запущена', 'Проверьте статус через несколько минут', 'info');
            } else {
                showNotification('Ошибка синхронизации', data.error, 'error');
            }
        });
}

// Auto-refresh every 5 minutes
setInterval(() => {
    // Only refresh if no filters are applied
    if (!window.location.search) {
        location.reload();
    }
}, 300000);
