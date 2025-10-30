// Обновление предпросмотра в реальном времени
function updatePreview() {
    // Получаем исходный шаблон из скрытого элемента или из data-атрибута
    const previewEl = document.getElementById('preview');
    if (!previewEl) return;

    let text = previewEl.dataset.original || previewEl.textContent;

    // Находим все переменные на странице (по name)
    const inputs = document.querySelectorAll('input[name], textarea[name]');
    inputs.forEach(input => {
        const varName = input.name;
        const value = input.value || "(пусто)";
        // Экранируем для регулярки
        const escapedVar = varName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`{{\\s*${escapedVar}\\s*}}`, 'g');
        text = text.replace(regex, value);
    });

    previewEl.textContent = text;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function () {
    // Сохраняем оригинальный текст шаблона
    const previewEl = document.getElementById('preview');
    if (previewEl) {
        previewEl.dataset.original = previewEl.textContent;
        // Сразу обновляем, если есть данные
        updatePreview();
    }

    // Вешаем обработчики на все поля ввода на странице генерации
    const inputs = document.querySelectorAll('input[name], textarea[name]');
    inputs.forEach(input => {
        input.addEventListener('input', updatePreview);
    });
});