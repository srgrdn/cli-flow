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
    // Проверка авторизации и прав администратора
    const token = getCookie('access_token');
    if (token) {
        // Проверка JWT токена, чтобы узнать, является ли пользователь администратором
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const payload = JSON.parse(window.atob(base64));
            
            // Проверяем права администратора
            checkAdminRights(token);
            
            // Обновляем UI для авторизованного пользователя
            updateAuthUI(true);
        } catch (e) {
            console.error('Ошибка при разборе токена:', e);
        }
    } else {
        // Пользователь не авторизован
        updateAuthUI(false);
    }
    
    // Обновление UI в зависимости от статуса авторизации
    function updateAuthUI(isAuthenticated) {
        // Элементы для авторизованных пользователей
        const authUserElements = document.querySelectorAll('.auth-user, .auth-logout');
        // Элементы для неавторизованных пользователей
        const nonAuthElements = document.querySelectorAll('.auth-login, .auth-register');
        
        if (isAuthenticated) {
            // Показываем элементы для авторизованных пользователей
            authUserElements.forEach(el => el.style.display = 'block');
            // Скрываем элементы для неавторизованных пользователей
            nonAuthElements.forEach(el => el.style.display = 'none');
            
            // Если есть токен, декодируем его для получения email пользователя
            const token = getCookie('access_token');
            if (token) {
                try {
                    const base64Url = token.split('.')[1];
                    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                    const payload = JSON.parse(window.atob(base64));
                    
                    // Устанавливаем email пользователя, если элемент существует
                    const userEmailElement = document.getElementById('user-email');
                    if (userEmailElement) {
                        userEmailElement.textContent = payload.sub;
                    }
                    
                    // Настраиваем кнопку выхода
                    const logoutLink = document.getElementById('logout-link');
                    if (logoutLink) {
                        logoutLink.addEventListener('click', function(e) {
                            if (e.currentTarget.getAttribute('href') === '#') {
                                e.preventDefault();
                                // Удаляем токен из куки
                                document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
                                // Перенаправляем на главную
                                window.location.href = '/';
                            }
                        });
                    }
                } catch (e) {
                    console.error('Ошибка при разборе токена:', e);
                }
            }
        } else {
            // Показываем элементы для неавторизованных пользователей
            nonAuthElements.forEach(el => el.style.display = 'block');
            // Скрываем элементы для авторизованных пользователей
            authUserElements.forEach(el => el.style.display = 'none');
        }
    }
    
    // Проверка прав администратора через API
    async function checkAdminRights(token) {
        try {
            const response = await fetch('/auth/check-admin', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                // Если пользователь - администратор, показываем ссылку на админку
                const adminMenuItem = document.getElementById('adminMenuItem');
                if (adminMenuItem) {
                    adminMenuItem.style.display = 'block';
                }
                
                // Настраиваем ссылку для перехода в админку
                const adminLink = document.getElementById('adminLink');
                if (adminLink) {
                    adminLink.addEventListener('click', function(e) {
                        e.preventDefault();
                        window.location.href = '/admin/';
                    });
                }
            }
        } catch (e) {
            console.error('Ошибка при проверке прав администратора:', e);
        }
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
                
                // Проверяем, является ли пользователь администратором
                try {
                    const adminResponse = await fetch('/auth/check-admin', {
                        headers: {
                            'Authorization': `Bearer ${data.access_token}`
                        }
                    });
                    
                    if (adminResponse.ok) {
                        // Если пользователь - администратор, перенаправляем в админку
                        window.location.href = '/admin/';
                    } else {
                        // Иначе на главную страницу
                        window.location.href = '/';
                    }
                } catch (error) {
                    // В случае ошибки просто перенаправляем на главную
                    window.location.href = '/';
                }
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
    document.querySelectorAll('a[href^="/questions/test"], a[href^="/questions/history"]').forEach(link => {
        link.addEventListener('click', function(e) {
            const token = getCookie('access_token');
            
            if (!token) {
                e.preventDefault();
                window.location.href = '/login';
                return;
            }
            
            // Токен уже в куки, не нужно добавлять его в URL
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