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
    
    // Формируем подробный tooltip как безопасный HTML
    const esc = (s)=> window.App && window.App.util && window.App.util.escapeHtml ? window.App.util.escapeHtml(String(s==null?"":s)) : String(s==null?"":s);
    const desc = esc(apiInfo.description || "API информация");
    const status = esc(apiInfo.status || "неизвестно");
    const feat = Array.isArray(apiInfo.features) ? apiInfo.features.map(f=>`<li>${esc(f)}</li>`).join("") : "";
    const tooltipHtml = `
      <div class="text-start">
        <div><strong>${desc}</strong></div>
        <div class="mt-1">Статус: <span class="badge bg-secondary">${status}</span></div>
        ${feat?`<div class="mt-1">Возможности:<ul class="mb-0 ps-3">${feat}</ul></div>`:""}
      </div>`;
    
    new bootstrap.Tooltip(indicator, {
      title: tooltipHtml,
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
    
    // Создаем новый placeholder для Lucide и безопасно заменяем текущий узел
    const newIcon = document.createElement("i");
    newIcon.className = "api-icon";
    newIcon.id = "apiIcon";
    newIcon.setAttribute("data-lucide", iconName);
    
    if (typeof iconElement.replaceWith === "function") {
      iconElement.replaceWith(newIcon);
    } else if (iconElement.parentNode) {
      // Fallback для старых браузеров
      iconElement.parentNode.insertBefore(newIcon, iconElement.nextSibling);
      iconElement.parentNode.removeChild(iconElement);
    }
    
    // Перерисовываем SVG через Lucide
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
  
  // Изменение интервала обновления
  function setApiInfoInterval(seconds) {
    const interval = Math.max(10, Math.min(300, seconds)); // от 10 до 300 секунд
    localStorage.setItem(API_INFO_INTERVAL_KEY, interval.toString());
    
    if (apiInfoTimer) {
      startApiInfoTimer(); // перезапускаем с новым интервалом
    }
    
    console.log(`API Info интервал изменен на ${interval} секунд`);
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
    setApiInfoInterval,
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
  // Убираем автоматический запуск, так как он будет вызван из app_init.js
  // if (document.readyState === "loading") {
  //   document.addEventListener("DOMContentLoaded", startApiInfoTimer);
  // } else {
  //   startApiInfoTimer();
  // }
})();
