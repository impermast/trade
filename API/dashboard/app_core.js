// Core utils & globals
(function(){
  window.App = window.App || {};
  const util = {};

  // Система управления зависимостями и инициализацией
  const DependencyManager = {
    dependencies: {
      jQuery: false,
      Bootstrap: false,
      Plotly: false,
      Lucide: false
    },
    
    // Проверка конкретной зависимости
    checkDependency: function(name) {
      switch(name) {
        case 'jQuery':
          return typeof window.jQuery !== 'undefined' && typeof window.$ !== 'undefined';
        case 'Bootstrap':
          return typeof window.bootstrap !== 'undefined';
        case 'Plotly':
          return typeof window.Plotly !== 'undefined';
        case 'Lucide':
          return typeof window.lucide !== 'undefined';
        default:
          return false;
      }
    },
    
    // Обновление статуса зависимости
    updateDependencyStatus: function() {
      Object.keys(this.dependencies).forEach(name => {
        this.dependencies[name] = this.checkDependency(name);
      });
    },
    
    // Проверка готовности всех зависимостей
    areAllDependenciesReady: function() {
      this.updateDependencyStatus();
      return Object.values(this.dependencies).every(ready => ready);
    },
    
    // Получение статуса зависимостей для отладки
    getDependencyStatus: function() {
      this.updateDependencyStatus();
      return { ...this.dependencies };
    }
  };

  // Функция ожидания всех критических зависимостей с улучшенной логикой
  function waitForDependencies() {
    return new Promise((resolve, reject) => {
      const maxWaitTime = 30000; // 30 секунд максимум
      const checkInterval = 100;
      let elapsed = 0;
      
      const check = () => {
        if (DependencyManager.areAllDependenciesReady()) {
          console.log('✅ Все зависимости загружены:', DependencyManager.getDependencyStatus());
          resolve();
          return;
        }
        
        elapsed += checkInterval;
        if (elapsed >= maxWaitTime) {
          const status = DependencyManager.getDependencyStatus();
          console.error('❌ Таймаут ожидания зависимостей:', status);
          reject(new Error(`Таймаут загрузки зависимостей: ${JSON.stringify(status)}`));
          return;
        }
        
        console.log('⏳ Ожидание зависимостей...', DependencyManager.getDependencyStatus());
        setTimeout(check, checkInterval);
      };
      
      check();
    });
  }

  // Проверка загрузки jQuery
  const $ = window.jQuery || window.$;
  if (!$) {
    console.error('❌ jQuery не загружен! Дашборд не может работать корректно.');
    return;
  }

  // Система управления модулями
  const ModuleManager = {
    modules: {},
    initQueue: [],
    isInitialized: false,
    
    // Регистрация модуля
    register: function(name, module) {
      this.modules[name] = module;
      console.log(`📦 Модуль зарегистрирован: ${name}`);
    },
    
    // Получение модуля
    get: function(name) {
      return this.modules[name];
    },
    
    // Проверка готовности модуля
    isModuleReady: function(name) {
      return this.modules[name] && typeof this.modules[name] === 'object';
    },
    
    // Добавление в очередь инициализации
    addToInitQueue: function(initFunction, priority = 0) {
      this.initQueue.push({ fn: initFunction, priority });
      this.initQueue.sort((a, b) => b.priority - a.priority); // Приоритет по убыванию
    },
    
    // Выполнение инициализации
    executeInit: async function() {
      if (this.isInitialized) {
        console.warn('⚠️ Инициализация уже выполнена');
        return;
      }
      
      console.log('🚀 Начинаем инициализацию модулей...');
      
      try {
        for (const item of this.initQueue) {
          try {
            console.log(`⚡ Выполняем инициализацию с приоритетом ${item.priority}`);
            await item.fn();
          } catch (error) {
            console.error(`❌ Ошибка инициализации модуля:`, error);
          }
        }
        
        this.isInitialized = true;
        console.log('✅ Инициализация всех модулей завершена');
        
        // Уведомляем о готовности
        window.dispatchEvent(new CustomEvent('dashboardReady'));
        
      } catch (error) {
        console.error('❌ Критическая ошибка инициализации:', error);
      }
    }
  };

  // Проверка готовности DOM и зависимостей
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', async () => {
      try {
        console.log('📄 DOM загружен, ожидаем зависимости...');
        await waitForDependencies();
        await initCore();
      } catch (e) {
        console.error('❌ Ошибка инициализации core:', e);
      }
    });
    return;
  }

  // Если DOM уже готов, ждем зависимости и инициализируем
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    waitForDependencies().then(async () => {
      await initCore();
    }).catch(e => {
      console.error('❌ Ошибка ожидания зависимостей:', e);
    });
  }

  async function initCore() {
    console.log("🔧 Инициализация core модуля...");

    // Регистрируем core модуль
    ModuleManager.register('core', { util, DependencyManager, ModuleManager });

    // bootstrap tooltips init lives in ui.js (visual)
    // Debounce
    util.debounce = (fn,ms=250)=>{let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),ms)}};

    // Numbers/format
    util.fmtNumber = (x,d=2)=>{ if(x==null||isNaN(x)) return "—"; return Number(x).toLocaleString("ru-RU",{maximumFractionDigits:d}); };

    // CSS var
    util.cssVar = (name)=> {
      try {
        const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || '';
      } catch (e) {
        console.warn('⚠️ Ошибка получения CSS переменной:', name, e);
        return '';
      }
    };

    // HTML escape
    util.escapeHtml = (s)=> (s??"").toString()
      .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
      .replace(/"/g,"&quot;").replace(/'/g,"&#39;");

    // Humanize updated
    const RU_MONTHS=["янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"];
    const pad2 = n => String(n).padStart(2,"0");
    util.humanizeUpdated = (iso)=>{
      if(!iso) return "—";
      try {
        const dt = new Date(iso); 
        if(isNaN(+dt)) return "—";
        const now = new Date(); 
        const diffSec = Math.max(0, Math.floor((now - dt)/1000));
        let rel;
        if (diffSec < 30) rel = "недавно";
        else if (diffSec < 60) rel = `${diffSec} сек назад`;
        else if (diffSec < 3600) rel = `${Math.floor(diffSec/60)} мин назад`;
        else if (diffSec < 86400) rel = `${Math.floor(diffSec/3600)} ч назад`;
        else rel = `${Math.floor(diffSec/86400)} дн назад`;

        const isSameDay=(a,b)=> a.getFullYear()===b.getFullYear()&&a.getMonth()===b.getMonth()&&a.getDate()===b.getDate();
        const yest = new Date(now.getFullYear(), now.getMonth(), now.getDate()-1);
        const timeStr = `${pad2(dt.getHours())}:${pad2(dt.getMinutes())}:${pad2(dt.getSeconds())}`;
        let main;
        if (isSameDay(dt, now))       main = `сегодня, ${timeStr}`;
        else if (isSameDay(dt, yest)) main = `вчера, ${timeStr}`;
        else                          main = `${dt.getDate()} ${RU_MONTHS[dt.getMonth()]} ${dt.getFullYear()}, ${timeStr}`;
        return `${main} · ${rel}`;
      } catch (e) {
        console.warn('⚠️ Ошибка в humanizeUpdated:', e);
        return "—";
      }
    };

    // Top progress & snack
    let topProgTimer=null;
    util.topProgressStart = function(){ 
      try {
        const el=document.getElementById("topProgress"); 
        if(!el) return; 
        el.style.width="0"; 
        el.style.display="block"; 
        requestAnimationFrame(()=>{ el.style.width="65%"; }); 
      } catch (e) {
        console.warn('⚠️ Ошибка в topProgressStart:', e);
      }
    };
    util.topProgressDone  = function(){ 
      try {
        const el=document.getElementById("topProgress"); 
        if(!el) return; 
        el.style.width="100%"; 
        clearTimeout(topProgTimer); 
        topProgTimer=setTimeout(()=>{ el.style.display="none"; el.style.width="0"; }, 250); 
      } catch (e) {
        console.warn('⚠️ Ошибка в topProgressDone:', e);
      }
    };
    util.showSnack = (msg, timeout=2200)=>{ 
      try {
        if ($ && $("#snackbarMsg").length && $("#snackbar").length) {
          $("#snackbarMsg").text(msg); 
          $("#snackbar").fadeIn(120); 
          setTimeout(()=>$("#snackbar").fadeOut(180), timeout); 
        }
      } catch (e) {
        console.warn('⚠️ Ошибка в showSnack:', e);
      }
    };
    util.withProgress = async (promise)=>{ 
      try{ 
        util.topProgressStart(); 
        return await promise; 
      } finally{ 
        util.topProgressDone(); 
      } 
    };

    // Health ping
    util.pingHealth = async function(){
      try{
        const r = await fetch("/api/health",{cache:"no-store"});
        const ok = r.ok;
        if ($ && $("#statusDot").length && $("#statusText").length) {
          $("#statusDot").toggleClass("status-ok", ok).toggleClass("status-warn", !ok);
          $("#statusText").text(ok ? "online" : "offline");
        }
      } catch (e) {
        if ($ && $("#statusDot").length && $("#statusText").length) {
          $("#statusDot").removeClass("status-ok").addClass("status-warn");
          $("#statusText").text("offline");
        }
      }
    };

    // Chips binding + hidden checkboxes state
    util.bindChip = function(id, checkboxSel){
      const chip=$(id), cb=$(checkboxSel);
      chip.on("pointerdown", e=>{ chip[0].style.setProperty('--x', e.offsetX+'px'); chip[0].style.setProperty('--y', e.offsetY+'px'); });
      function sync(){ chip.toggleClass("selected", cb.is(":checked")); }
      chip.on("click", ()=>{ 
        cb.prop("checked", !cb.is(":checked")); 
        sync(); 
        // Сбрасываем переменные оптимизации при изменении чекбоксов
        if(window.App.chart && window.App.chart._currentFile !== undefined) {
          window.App.chart._currentFile = null;
          window.App.chart._lastTs = null;
        }
        if(window.App.chart && window.App.chart.drawChart) {
          window.App.chart.drawChart(false);
        } 
      });
      sync();
    };
    const hiddenControls = $('<div style="display:none"></div>').appendTo(document.body);
    hiddenControls.append('<input type="checkbox" id="sma20">');
    hiddenControls.append('<input type="checkbox" id="sma50">');
    hiddenControls.append('<input type="checkbox" id="signals_rsi">');
    hiddenControls.append('<input type="checkbox" id="signals_xgb">');
    hiddenControls.append('<input type="checkbox" id="signals_macd">');
    hiddenControls.append('<input type="checkbox" id="signals_bollinger">');
    hiddenControls.append('<input type="checkbox" id="signals_stochastic">');
    hiddenControls.append('<input type="checkbox" id="signals_williams_r">');
    hiddenControls.append('<input type="checkbox" id="logScale">');

    // Добавляем обработчики для скрытых чекбоксов, чтобы сбрасывать переменные оптимизации
    $("#sma20, #sma50, #signals_rsi, #signals_xgb, #signals_macd, #signals_bollinger, #signals_stochastic, #signals_williams_r, #logScale").on("change", function() {
      // Сбрасываем переменные оптимизации при изменении любых чекбоксов
      if(window.App.chart && window.App.chart._currentFile !== undefined) {
        window.App.chart._currentFile = null;
        window.App.chart._lastTs = null;
      }
    });

    // Indicators (client)
    util.rsi = function(prices, period=14){
      const n=prices.length, out=Array(n).fill(null);
      if(n<period+1) return out;
      let avgGain=0, avgLoss=0;
      for(let i=1;i<=period;i++){ const ch=prices[i]-prices[i-1]; avgGain+=Math.max(ch,0); avgLoss+=Math.max(-ch,0); }
      avgGain/=period; avgLoss/=period; out[period]=avgLoss===0?100:100-100/(1+(avgGain/avgLoss));
      for(let i=period+1;i<n;i++){ const ch=prices[i]-prices[i-1], g=Math.max(ch,0), l=Math.max(-ch,0);
        avgGain=(avgGain*(period-1)+g)/period; avgLoss=(avgLoss*(period-1)+l)/period; out[i]=avgLoss===0?100:100-100/(1+(avgGain/avgLoss)); } 
      return out;
    };
    util.sma = function(values, period){
      const res=Array(values.length).fill(null); if(period<=1) return values.slice();
      let sum=0; for(let i=0;i<values.length;i++){ const v=+values[i]; if(!isNaN(v)) sum+=v;
        if(i>=period){ const out=+values[i-period]; if(!isNaN(out)) sum-=out; }
        if(i>=period-1) res[i]=sum/period; } return res;
    };

    // Функция для очистки ресурсов
    util.cleanup = function(){
      try {
        if(topProgTimer){ 
          clearTimeout(topProgTimer); 
          topProgTimer=null; 
        }
        // Очищаем скрытые контролы
        if(hiddenControls && hiddenControls.length) {
          hiddenControls.remove();
        }
      } catch (e) {
        console.warn('⚠️ Ошибка при очистке ресурсов util:', e);
      }
    };

    // Экспортируем функции управления зависимостями и модулями
    util.waitForDependencies = waitForDependencies;
    util.DependencyManager = DependencyManager;
    util.ModuleManager = ModuleManager;

    // Добавляем core в глобальный App
    window.App.util = util;
    window.App.DependencyManager = DependencyManager;
    window.App.ModuleManager = ModuleManager;

    console.log("✅ Core модуль инициализирован");
  } // закрываем initCore
})();
