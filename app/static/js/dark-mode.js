// Dark Mode Functionality
document.addEventListener('DOMContentLoaded', function() {
    // Create the theme toggle button
    const toggleButton = document.createElement('button');
    toggleButton.className = 'theme-toggle';
    toggleButton.setAttribute('aria-label', 'Переключить тему');
    toggleButton.innerHTML = '<i class="fas fa-sun"></i>';
    document.body.appendChild(toggleButton);
    
    // Check for saved theme preference or respect OS preference
    const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('theme');
    
    // Apply the right theme based on saved preference or OS preference
    if (savedTheme === 'dark' || (!savedTheme && prefersDarkMode)) {
        document.body.classList.add('dark-mode');
        toggleButton.innerHTML = '<i class="fas fa-moon"></i>';
        
        // Ensure bg-light elements get proper dark mode class
        document.querySelectorAll('.bg-light').forEach(el => {
            el.classList.remove('bg-light');
            el.classList.add('bg-dark');
        });
    }
    
    // Toggle theme function
    function toggleTheme() {
        if (document.body.classList.contains('dark-mode')) {
            document.body.classList.remove('dark-mode');
            localStorage.setItem('theme', 'light');
            toggleButton.innerHTML = '<i class="fas fa-sun"></i>';
            
            // Restore bg-light for elements that had bg-dark added
            document.querySelectorAll('.bg-dark:not(.navbar)').forEach(el => {
                el.classList.remove('bg-dark');
                el.classList.add('bg-light');
            });
        } else {
            document.body.classList.add('dark-mode');
            localStorage.setItem('theme', 'dark');
            toggleButton.innerHTML = '<i class="fas fa-moon"></i>';
            
            // Convert bg-light elements to bg-dark
            document.querySelectorAll('.bg-light').forEach(el => {
                el.classList.remove('bg-light');
                el.classList.add('bg-dark');
            });
        }
        
        // Add animation to the toggle icon
        const icon = toggleButton.querySelector('i');
        icon.style.animation = 'rotate 0.5s ease';
        setTimeout(() => {
            icon.style.animation = '';
        }, 500);
    }
    
    // Add click event to toggle theme
    toggleButton.addEventListener('click', toggleTheme);
    
    // Toggle based on OS theme change
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
        if (!localStorage.getItem('theme')) { // Only if user hasn't manually set a preference
            if (event.matches) {
                document.body.classList.add('dark-mode');
                toggleButton.innerHTML = '<i class="fas fa-moon"></i>';
                
                // Convert bg-light elements to bg-dark
                document.querySelectorAll('.bg-light').forEach(el => {
                    el.classList.remove('bg-light');
                    el.classList.add('bg-dark');
                });
            } else {
                document.body.classList.remove('dark-mode');
                toggleButton.innerHTML = '<i class="fas fa-sun"></i>';
                
                // Restore bg-light for elements that had bg-dark added
                document.querySelectorAll('.bg-dark:not(.navbar)').forEach(el => {
                    el.classList.remove('bg-dark');
                    el.classList.add('bg-light');
                });
            }
        }
    });
    
    // Add keydown event to toggle theme with 'D' key
    document.addEventListener('keydown', function(e) {
        // Toggle theme with Ctrl+D (or Cmd+D on Mac)
        if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
            e.preventDefault();
            toggleTheme();
        }
    });
}); 