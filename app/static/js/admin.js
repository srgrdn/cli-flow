// Функционал для админ-панели

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация тултипов для Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Обработка кликов по сообщениям
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        const closeBtn = alert.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                alert.classList.add('fade');
                setTimeout(() => {
                    alert.remove();
                }, 150);
            });
        }
    });

    // Функция для форматирования дат
    function formatDate(dateString) {
        const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        return new Date(dateString).toLocaleDateString('ru-RU', options);
    }

    // Форматирование дат в таблицах
    const dateCells = document.querySelectorAll('.format-date');
    dateCells.forEach(cell => {
        const originalDate = cell.textContent.trim();
        if (originalDate) {
            try {
                cell.textContent = formatDate(originalDate);
            } catch (e) {
                console.error('Ошибка форматирования даты:', e);
            }
        }
    });

    // Обработка подтверждений удаления
    const deleteButtons = document.querySelectorAll('.delete-confirm');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Вы уверены, что хотите удалить этот элемент?')) {
                e.preventDefault();
            }
        });
    });

    // Активация текущего пункта меню
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath || 
            (link.getAttribute('href') !== '/' && currentPath.startsWith(link.getAttribute('href')))) {
            link.classList.add('active');
        }
    });
    
    // Добавление токена к ссылкам навигации в админ-панели
    function getTokenFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('token');
    }
    
    const token = getTokenFromUrl();
    if (token) {
        // Добавляем токен ко всем ссылкам в админ-панели
        const adminLinks = document.querySelectorAll('a[href^="/admin"]');
        adminLinks.forEach(link => {
            const href = link.getAttribute('href');
            // Проверяем, что у ссылки еще нет параметра token
            if (!href.includes('token=')) {
                link.setAttribute('href', `${href}${href.includes('?') ? '&' : '?'}token=${token}`);
            }
        });
    }
}); 