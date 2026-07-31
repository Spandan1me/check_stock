(function () {
    document.addEventListener('DOMContentLoaded', function () {
        var toggle = document.querySelector('.menu-toggle');
        var sidebar = document.querySelector('.sidebar');
        var shell = document.querySelector('.shell');
        if (!toggle || !sidebar || !shell) return;
        function openNav() {
            sidebar.classList.add('open');
            shell.classList.add('dimmed');
        }
        function closeNav() {
            sidebar.classList.remove('open');
            shell.classList.remove('dimmed');
        }
        toggle.addEventListener('click', function (e) {
            e.stopPropagation();
            if (sidebar.classList.contains('open')) closeNav(); else openNav();
        });
        // close when clicking outside
        shell.addEventListener('click', function (e) {
            if (!sidebar.classList.contains('open')) return;
            var inside = e.target.closest('.sidebar');
            var isToggle = e.target.closest('.menu-toggle');
            if (!inside && !isToggle) closeNav();
        });
        // close on escape
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeNav(); });
    });
})();
