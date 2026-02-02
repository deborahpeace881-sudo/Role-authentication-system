// Close alert messages
document.querySelectorAll('.close-alert').forEach(button => {
    button.addEventListener('click', function() {
        this.closest('.alert').style.display = 'none';
    });
});

// Load theme preference
window.addEventListener('load', function() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }
});

// Listen for theme changes from admin panel
window.addEventListener('storage', function(e) {
    if (e.key === 'theme') {
        document.body.classList.toggle('dark-theme', e.newValue === 'dark');
    }
});
