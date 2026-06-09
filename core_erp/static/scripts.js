/*! Bootstrap v5.3.3 Custom Light Build */
document.addEventListener('DOMContentLoaded', function () {
    // Находим все кнопки выпадающего меню на сайте
    const dropdownToggles = document.querySelectorAll('[data-bs-toggle="dropdown"]');

    dropdownToggles.forEach(function (toggle) {
        toggle.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            const menu = this.nextElementSibling;
            if (menu && menu.classList.contains('dropdown-menu')) {
                // Закрываем другие открытые меню
                document.querySelectorAll('.dropdown-menu.show').forEach(function (m) {
                    if (m !== menu) m.classList.remove('show');
                });
                menu.classList.toggle('show');
            }
        });
    });

    // Закрываем меню при клике в любое пустое место экрана
    document.addEventListener('click', function () {
        document.querySelectorAll('.dropdown-menu.show').forEach(function (menu) {
            menu.classList.remove('show');
        });
    });
});