// Theme toggle functionality
function initThemeToggle() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;

    // Check if theme toggle button exists on this page
    if (!themeToggleBtn) return;

    const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
    const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');

    // Check for saved theme preference or default to 'light'
    const currentTheme = localStorage.getItem('theme') || 'light';

    function applyTheme(theme) {
        if (theme === 'dark') {
            htmlElement.classList.add('dark');
            htmlElement.setAttribute('data-theme', 'dark');
            if (document.body) document.body.setAttribute('data-theme', 'dark');
            if (themeToggleLightIcon) {
                themeToggleLightIcon.classList.remove('hidden');
                if (themeToggleDarkIcon) themeToggleDarkIcon.classList.add('hidden');
            }
        } else {
            htmlElement.classList.remove('dark');
            htmlElement.setAttribute('data-theme', 'light');
            if (document.body) document.body.setAttribute('data-theme', 'light');
            if (themeToggleDarkIcon) {
                themeToggleDarkIcon.classList.remove('hidden');
                if (themeToggleLightIcon) themeToggleLightIcon.classList.add('hidden');
            }
        }
    }

    // Ensure both icons start hidden before applying
    if (themeToggleDarkIcon) themeToggleDarkIcon.classList.add('hidden');
    if (themeToggleLightIcon) themeToggleLightIcon.classList.add('hidden');

    applyTheme(currentTheme);

    // Toggle theme on button click
    themeToggleBtn.addEventListener('click', function() {
        const isDark = htmlElement.classList.contains('dark');
        const newTheme = isDark ? 'light' : 'dark';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    });
}

// Initialize theme toggle when DOM is ready
document.addEventListener('DOMContentLoaded', initThemeToggle);
