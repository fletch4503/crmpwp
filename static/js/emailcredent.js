function syncNow() {
    fetch('/emails/ajax/sync-now/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Синхронизация запущена', 'Это может занять несколько минут', 'info');
                // Refresh the page after 5 seconds to show updated status
                setTimeout(() => location.reload(), 5000);
            } else {
                showNotification('Ошибка', data.error, 'error');
            }
        })
        .catch(error => {
            showNotification('Ошибка', 'Не удалось запустить синхронизацию', 'error');
        });
}

function deleteRule(ruleId) {
    if (confirm('Вы уверены, что хотите удалить это правило?')) {
        fetch(`/emails/rules/${ruleId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            },
        })
            .then(response => {
                if (response.ok) {
                    showNotification('Правило удалено', '', 'success');
                    location.reload();
                } else {
                    showNotification('Ошибка', 'Не удалось удалить правило', 'error');
                }
            });
    }
}

// Auto-refresh sync status every 30 seconds
setInterval(() => {
    // Only refresh if we're on the credentials page
    if (window.location.pathname.includes('credentials')) {
        location.reload();
    }
}, 30000);
