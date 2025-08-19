(function(){
  window.App = window.App || {};
  const theme = {};
  const KEY="ui-theme";

  // Длительность кроссфейда темы
  const XFADE_MS = 220;
  
  // Флаг для предотвращения прерывания анимации
  let themeChangeInProgress = false;

  theme.applyTheme = function(t){
    document.documentElement.setAttribute("data-theme", t);
    $("#themeToggle").prop("checked", t==="dark");
    
    // Обновляем состояние иконок при инициализации
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
      const label = themeToggle.nextElementSibling;
      // Убираем все классы анимации при инициализации
      label.classList.remove('theme-switching', 'theme-switching-dark', 'theme-toggle-pulse');
      
      // Устанавливаем правильное начальное положение иконок
      const moonIcon = label.querySelector('.theme-icon-moon');
      const sunIcon = label.querySelector('.theme-icon-sun');
      
      if (moonIcon && sunIcon) {
        if (t === 'dark') {
          // Темная тема: луна видна, солнце скрыто
          moonIcon.style.transform = 'translateY(0) rotate(0deg)';
          moonIcon.style.opacity = '1';
          sunIcon.style.transform = 'translateY(20px) rotate(0deg)';
          sunIcon.style.opacity = '0';
        } else {
          // Светлая тема: солнце видно, луна скрыта
          moonIcon.style.transform = 'translateY(-20px) rotate(0deg)';
          moonIcon.style.opacity = '0';
          sunIcon.style.transform = 'translateY(0) rotate(0deg)';
          sunIcon.style.opacity = '1';
        }
      }
    }
  };

  // Плавная смена темы: кроссфейд всей страницы
  function crossfadeTo(nextTheme){
    // Защита от прерывания анимации
    if (themeChangeInProgress) {
      console.log('Смена темы уже в процессе, игнорируем новый запрос');
      return;
    }
    
    themeChangeInProgress = true;
    
    // Добавляем класс для анимации иконки
    const themeToggle = document.getElementById('themeToggle');
    if (!themeToggle) { 
      theme.applyTheme(nextTheme); 
      themeChangeInProgress = false;
      return; 
    }
    const label = themeToggle.nextElementSibling;
    
    if (nextTheme === 'light') {
      // Переход к светлой теме: луна уходит, солнце входит
      label.classList.add('theme-switching');
    } else {
      // Переход к темной теме: солнце уходит, луна входит
      label.classList.add('theme-switching-dark');
    }
    
    // Включаем плавную прозрачность для <body>
    document.body.classList.add("theme-xfade");
    // Фаза 1: затемняем до 0
    requestAnimationFrame(()=>{
      document.body.style.opacity = "0";
      // На полпути — меняем тему
      setTimeout(()=>{
        theme.applyTheme(nextTheme);
        // Фаза 2: возвращаем к 1
        document.body.style.opacity = "1";
        setTimeout(()=>{
          document.body.classList.remove("theme-xfade");
          document.body.style.opacity = "";
          
          // Убираем классы анимации иконки
          label.classList.remove('theme-switching', 'theme-switching-dark');
          
          // Добавляем эффект пульсации
          label.classList.add('theme-toggle-pulse');
          setTimeout(() => {
            label.classList.remove('theme-toggle-pulse');
          }, 600);
          
          // Сбрасываем флаг анимации
          themeChangeInProgress = false;
        }, XFADE_MS);
      }, Math.floor(XFADE_MS/2));
    });
  }

  theme.initTheme = function(){
    const saved=localStorage.getItem(KEY)||"dark";
    theme.applyTheme(saved);

    $("#themeToggle").on("change",()=>{
      const next=$("#themeToggle").is(":checked")?"dark":"light";
      localStorage.setItem(KEY,next);
      crossfadeTo(next);
      // Перерисуем график после окончания анимации (чтобы адаптировать сетку/цвета)
      if (window.App?.chart) {
        setTimeout(()=>window.App.chart.drawChart(false), XFADE_MS+30);
      }
    });
  };

  theme.themeVars = function(){
    const css = window.App.util.cssVar;
    return {
      paper_bgcolor: css("--bg"),
      plot_bgcolor:  css("--surface"),
      font_color:    css("--on-surface"),
      grid:          css("--grid")
    };
  };

  // Функция для очистки ресурсов
  theme.cleanup = function(){
    try {
      // Очищаем все активные анимации смены темы
      document.body.classList.remove('theme-xfade');
      document.body.style.opacity = '';
      
      // Сбрасываем состояние переключателя темы
      const themeToggle = document.getElementById('themeToggle');
      if (themeToggle) {
        themeToggle.checked = document.documentElement.getAttribute('data-theme') === 'dark';
      }
    } catch (e) {
      console.warn('Ошибка при очистке ресурсов темы:', e);
    }
  };

  window.App.theme = theme;
})();
