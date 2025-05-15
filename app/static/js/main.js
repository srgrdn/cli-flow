// Основная клиентская логика

// Функция для установки cookie
function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
}

// Функция для получения cookie
function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

document.addEventListener('DOMContentLoaded', function() {
    // Обработка формы тестирования
    const testForm = document.getElementById('test-form');
    if (testForm) {
        testForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // В будущем здесь будет логика отправки ответов и получения результатов
            alert('Функционал проверки ответов будет реализован в следующей версии!');
            
            // Перенаправление на главную страницу
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        });
    }
    
    // Обработчик формы входа
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new URLSearchParams();
            formData.append('username', document.getElementById('email').value);
            formData.append('password', document.getElementById('password').value);
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: formData
            });
            if (response.ok) {
                const data = await response.json();
                // Сохраняем токен в куки вместо localStorage
                setCookie('access_token', data.access_token, 1); // срок действия 1 день
                window.location.href = '/';
            } else {
                alert('Ошибка авторизации');
            }
        });
    }

    // Обработчик формы регистрации
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: document.getElementById('email').value,
                    password: document.getElementById('password').value
                })
            });

            if (response.ok) {
                window.location.href = '/login';
            } else {
                alert('Ошибка регистрации');
            }
        });
    }
    
    // Перехват всех ссылок на защищенные страницы
    document.querySelectorAll('a[href^="/questions/test"]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const token = getCookie('access_token');
            
            if (!token) {
                window.location.href = '/login';
                return;
            }
            
            // Добавляем токен в URL напрямую
            window.location.href = this.href + '?token=' + encodeURIComponent(token);
        });
    });
    
    // Анимация для карточек на главной странице
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});