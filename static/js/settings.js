document.addEventListener('DOMContentLoaded', function () {
    loadSettings();
});

function loadSettings() {
    fetch('{% url "users:ajax_user_settings" %}')
        .then(response => response.json())
        .then(data => {
            document.getElementById('email-notifications').checked = data.email_notifications;
            document.getElementById('sms-notifications').checked = data.sms_notifications;
            document.getElementById('theme-select').value = data.theme;
            document.getElementById('language-select').value = data.language;
        })
        .catch(error => {
            console.error('Error loading settings:', error);
        });
}

function saveSettings() {
    const settings = {
        email_notifications: document.getElementById('email-notifications').checked,
        sms_notifications: document.getElementById('sms-notifications').checked,
        theme: document.getElementById('theme-select').value,
        language: document.getElementById('language-select').value,
    };

    fetch('{% url "users:ajax_update_settings" %}', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify(settings)
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Настройки сохранены', 'Ваши настройки успешно обновлены', 'success');
                // Применить тему сразу
                document.documentElement.setAttribute('data-theme', settings.theme);
                localStorage.setItem('theme', settings.theme);
            } else {
                showNotification('Ошибка', 'Не удалось сохранить настройки', 'error');
            }
        })
        .catch(error => {
            console.error('Error saving settings:', error);
            showNotification('Ошибка', 'Произошла ошибка при сохранении', 'error');
        });
}

function changePassword() {
    // TODO: Реализовать изменение пароля
    showNotification('В разработке', 'Функция изменения пароля скоро будет доступна', 'info');
}

function manageTokens() {
    window.location.href = '{% url "users:token_list" %}';
}

function showNotification(title, message, level = 'info') {
    // Create toast notification using DaisyUI
    const toast = document.createElement('div');
    toast.className = `toast toast-top toast-end`;

    const alert = document.createElement('div');
    alert.className = `alert alert-${level}`;

    alert.innerHTML = `
        <div>
            <h3 class="font-bold">${title}</h3>
            <div class="text-xs">${message}</div>
        </div>
        <div class="flex-none">
            <button class="btn btn-sm btn-circle btn-ghost" onclick="this.parentElement.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    toast.appendChild(alert);
    document.body.appendChild(toast);

    // Auto-hide after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}
