document.addEventListener('DOMContentLoaded', () => {
    const gallery = document.getElementById('galleryScroll');
    const leftBtn = document.querySelector('.scroll-left');
    const rightBtn = document.querySelector('.scroll-right');

    // Сколько пикселей прокручивать за раз (примерно ширина одного изображения + отступ)
    scrollAmount = 300;

    if (leftBtn && rightBtn && gallery) {
        rightBtn.addEventListener('click', () => {
            gallery.scrollBy({ left: scrollAmount, behavior: 'smooth' });
        });

        leftBtn.addEventListener('click', () => {
            gallery.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
        });
    }
});


// Функция копирования текста
function copyLinkText(event) {
    event.preventDefault();

    const link = event.currentTarget;
    const linkText = link.dataset.text || link.textContent.trim();

    navigator.clipboard.writeText(linkText).then(() => {
        showNotification('Номер скопирован', 'success');

        // Визуальная обратная связь
        link.classList.add('copied');
        setTimeout(() => {
            link.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Ошибка копирования:', err);
        showNotification('Ошибка при копировании', 'error');
    });
}

// Показ уведомления
function showNotification(message, type = 'success') {
    // Удаляем старое уведомление
    const oldNotification = document.querySelector('.copy-notification');
    if (oldNotification) {
        oldNotification.remove();
    }

    // Создаем новое
    const notification = document.createElement('div');
    notification.className = `copy-notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Показываем
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // Скрываем через 3 секунды
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 400);
    }, 3000);
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.copy-link, .copy-btn').forEach(element => {
        element.addEventListener('click', copyLinkText);
    });
});

// Простая плавная прокрутка
function scrollToAnchor() {
    const hash = window.location.hash;
    if (hash) {
        const target = document.querySelector(hash);
        if (target) {
            setTimeout(() => {
                const headerHeight = 100; // Высота вашего хедера
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth' // Встроенная плавная прокрутка
                });
            }, 300);
        }
    }
}

// При загрузке страницы
window.addEventListener('load', () => {
    if (window.location.hash) {
        scrollToAnchor();
    }
});

// При изменении хеша
window.addEventListener('hashchange', scrollToAnchor);

