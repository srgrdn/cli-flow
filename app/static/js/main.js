// Основная клиентская логика

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