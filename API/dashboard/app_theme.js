(function(){
  window.App = window.App || {};
  const theme = {};
  const KEY="ui-theme";

  // Длительность кроссфейда темы
  const XFADE_MS = 220;

  theme.applyTheme = function(t){
    document.documentElement.setAttribute("data-theme", t);
    $("#themeToggle").prop("checked", t==="dark");
  };

  // Плавная смена темы: кроссфейд всей страницы
  function crossfadeTo(nextTheme){
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
