// API Info Management Module
(function(){
  window.App = window.App || {};
  
  let apiInfoTimer = null;
  const API_INFO_INTERVAL_KEY = "api-info-interval-seconds";
  
  // Загрузка информации о текущем API
  async function loadApiInfo() {
    try {
      const response = await App.util.withProgress(fetch("/api/current_api"));
      const apiInfo = await response.json();
      
      updateApiIndicator(apiInfo);
    } catch (e) {
      console.warn('Ошибка при загрузке информации об API:', e);
      // Показываем ошибку в индикаторе
      updateApiIndicator({
        name: "Ошибка",
        type: "error",
        description: "Не удалось загрузить информацию",
        status: "error"
      });
    }
  }
  
  // Обновление индикатора API
  function updateApiIndicator(apiInfo) {
    const indicator = document.getElementById("apiIndicator");
    const apiName = document.getElementById("apiName");
    const apiIcon = document.getElementById("apiIcon");
    
    if (!indicator || !apiName || !apiIcon) return;
    
    // Обновляем текст
    apiName.textContent = apiInfo.name || "—";
    
    // Обновляем тип API для стилизации
    indicator.setAttribute("data-api-type", apiInfo.type || "unknown");
    
    // Обновляем иконку в зависимости от типа API
    updateApiIcon(apiIcon, apiInfo.type);
    
    // Обновляем tooltip
    const tooltip = bootstrap.Tooltip.getInstance(indicator);
    if (tooltip) {
      tooltip.dispose();
    }
    
    // Формируем подробный tooltip
    let tooltipText = `${apiInfo.description || "API информация"}\n`;
    tooltipText += `Статус: ${apiInfo.status || "неизвестно"}`;
    
    if (apiInfo.features && apiInfo.features.length > 0) {
      tooltipText += `\nВозможности:\n• ${apiInfo.features.join('\n• ')}`;
    }
    
    new bootstrap.Tooltip(indicator, {
      title: tooltipText,
      placement: "bottom",
      trigger: "hover",
      html: true
    });
    
    // Добавляем класс для анимации
    indicator.classList.add("api-loaded");
    setTimeout(() => {
      indicator.classList.remove("api-loaded");
    }, 300);
  }
  
  // Обновление иконки API
  function updateApiIcon(iconElement, apiType) {
    if (!iconElement) return;
    
    // Удаляем старую иконку
    iconElement.remove();
    
    // Создаем новую иконку
    const newIcon = document.createElement("i");
    newIcon.className = "api-icon";
    newIcon.id = "apiIcon";
    
    // Выбираем иконку в зависимости от типа API
    let iconName = "server"; // по умолчанию
    
    switch (apiType) {
      case "simulation":
        iconName = "bot";
        break;
      case "exchange":
        iconName = "zap";
        break;
      case "error":
        iconName = "alert-triangle";
        break;
      case "unknown":
        iconName = "help-circle";
        break;
      default:
        iconName = "server";
    }
    
    newIcon.setAttribute("data-lucide", iconName);
    
    // Вставляем новую иконку
    iconElement.parentNode.insertBefore(newIcon, iconElement.nextSibling);
    
    // Создаем иконку через Lucide
    if (window.lucide) {
      lucide.createIcons();
    }
  }
  
  // Запуск таймера для обновления информации об API
  function startApiInfoTimer() {
    // Очищаем предыдущий таймер
    if (apiInfoTimer) clearInterval(apiInfoTimer);
    
    // Загружаем информацию сразу
    loadApiInfo();
    
    // Устанавливаем интервал обновления (по умолчанию каждые 30 секунд)
    const seconds = Math.max(10, +(localStorage.getItem(API_INFO_INTERVAL_KEY) || 30));
    apiInfoTimer = setInterval(() => {
      if (document.visibilityState === "visible") {
        loadApiInfo();
      }
    }, seconds * 1000);
  }
  
  // Остановка таймера
  function stopApiInfoTimer() {
    if (apiInfoTimer) {
      clearInterval(apiInfoTimer);
      apiInfoTimer = null;
    }
  }
  
  // Обработчик изменения видимости страницы
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      loadApiInfo();
    }
  });
  
  // Функция для очистки ресурсов
  function cleanup() {
    try {
      stopApiInfoTimer();
    } catch (e) {
      console.warn('Ошибка при очистке ресурсов API info:', e);
    }
  }
  
  // Экспорт функций в глобальный объект App
  window.App.apiInfo = {
    loadApiInfo,
    startApiInfoTimer,
    stopApiInfoTimer,
    cleanup
  };
  
  // Добавляем обработчик для кнопки обновления всех панелей
  document.addEventListener("DOMContentLoaded", () => {
    const refreshAllBtn = document.getElementById("refreshAll");
    if (refreshAllBtn) {
      refreshAllBtn.addEventListener("click", () => {
        // Обновляем информацию об API при нажатии на кнопку "Обновить всё"
        loadApiInfo();
      });
    }
  });
  
  // Автоматический запуск при загрузке модуля
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startApiInfoTimer);
  } else {
    startApiInfoTimer();
  }
})();
