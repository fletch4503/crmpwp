    // HTMX Configuration -->
    // Configure HTMX
    htmx.config.globalViewTransitions = true;
    htmx.config.useTemplateFragments = true;

    // Add loading indicators
    document.body.addEventListener('htmx:beforeRequest', function (evt) {
        const btn = evt.target.closest('button, [role="button"]');
        if (btn) {
            btn.disabled = true;
            const originalText = btn.innerHTML;
            btn.setAttribute('data-original-text', originalText);
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Загрузка...';
        }
    });

    document.body.addEventListener('htmx:afterRequest', function (evt) {
        const btn = evt.target.closest('button, [role="button"]');
        if (btn) {
            btn.disabled = false;
            const originalText = btn.getAttribute('data-original-text');
            if (originalText) {
                btn.innerHTML = originalText;
            }
        }
    });

    // Handle HTMX errors
    document.body.addEventListener('htmx:responseError', function (evt) {
        showNotification('Ошибка', 'Произошла ошибка при загрузке данных', 'error');
    });
