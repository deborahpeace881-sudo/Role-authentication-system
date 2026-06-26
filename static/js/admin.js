// Sidebar toggle
document.getElementById('menu-toggle').addEventListener('click', function() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('active');
});

// Theme toggle
document.getElementById('theme-toggle').addEventListener('click', function() {
    const body = document.body;
    const icon = this.querySelector('i');

    body.classList.toggle('dark-theme');

    if (body.classList.contains('dark-theme')) {
        localStorage.setItem('theme', 'dark');
        icon.className = 'ti ti-sun';
    } else {
        localStorage.setItem('theme', 'light');
        icon.className = 'ti ti-moon';
    }
});

// Load saved theme
window.addEventListener('load', function() {
    const savedTheme = localStorage.getItem('theme');
    const icon = document.getElementById('theme-toggle').querySelector('i');

    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        icon.className = 'ti ti-sun';
    } else {
        icon.className = 'ti ti-moon';
    }
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', function(event) {
    const sidebar = document.getElementById('sidebar');
    const menuBtn = document.getElementById('menu-toggle');

    if (window.innerWidth <= 768) {
        if (!sidebar.contains(event.target) && !menuBtn.contains(event.target)) {
            sidebar.classList.remove('active');
        }
    }
}); 