function updateRealTime() {
    const now = new Date(); // Получаем текущее время
    const formattedTime = now.toLocaleTimeString(); // Форматируем время в "чч:мм:сс"
    document.getElementById('current-time').textContent = formattedTime; // Записываем в элемент
}

// Запускаем обновление каждые 1000 мс (1 секунда)
setInterval(updateRealTime, 1000);
updateRealTime(); // Отображение времени при загрузке страницы
