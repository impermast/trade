// Entry point: wire everything together
(function(){
  // Проверка загрузки всех критических зависимостей
  if (typeof window.App === 'undefined') {
    console.error('App не инициализирован! Проверьте загрузку core.js');
    return;
  }
  
  const U = window.App.util;
  if (!U) {
    console.error('App.util не найден! Проверьте загрузку core.js');
    return;
  }

  // Проверка jQuery
  if (typeof $ === 'undefined') {
    console.error('jQuery не загружен! Дашборд не может работать корректно.');
    return;
  }

  $(async function(){
    // Глобальный переключатель подробных логов: localStorage.debug === '1'
    const DEBUG = (localStorage.getItem('debug') === '1');
    if (!DEBUG) {
      try { console.log = function(){}; } catch (e) {}
    }
    console.log("Инициализация дашборда...");
    try {
      // Theme & health
      console.log("Инициализация темы и проверки здоровья...");
      if (App.theme && App.theme.initTheme) {
        console.log("Вызов App.theme.initTheme");
        App.theme.initTheme();
      } else {
        console.warn('App.theme.initTheme не найден');
      }
      
      // API Info initialization
      console.log("Инициализация информации об API...");
      if (App.apiInfo && App.apiInfo.startApiInfoTimer) {
        console.log("Вызов App.apiInfo.startApiInfoTimer");
        App.apiInfo.startApiInfoTimer();
      } else {
        console.warn('App.apiInfo.startApiInfoTimer не найден');
      }
      
      if (U.pingHealth) {
        console.log("Вызов U.pingHealth");
        // Менеджер пинга с паузой при скрытии вкладки
        let _pingTimer = null;
        const startPing = () => {
          if (_pingTimer) { clearInterval(_pingTimer); _pingTimer = null; }
          // Мгновенный пинг
          try { U.pingHealth(); } catch (e) {}
          // Запускаем периодический пинг только когда вкладка видима
          _pingTimer = setInterval(() => {
            if (document.visibilityState === 'visible') {
              try { U.pingHealth(); } catch (e) {}
            }
          }, 5000);
        };
        const stopPing = () => { if (_pingTimer) { clearInterval(_pingTimer); _pingTimer = null; } };
        startPing();
        document.addEventListener('visibilitychange', () => {
          if (document.visibilityState === 'visible') startPing(); else stopPing();
        });
      } else {
        console.warn('U.pingHealth не найден');
      }

      // Tabs ink init & listeners
      console.log("Инициализация вкладок...");
      if (App.ui && App.ui.updateTabsInk) {
        console.log("Вызов App.ui.updateTabsInk");
        App.ui.updateTabsInk();
        window.addEventListener('resize', U.debounce(App.ui.updateTabsInk, 100));
        
        const viewTabs = document.getElementById("viewTabs");
        if (viewTabs) {
          console.log("Настройка обработчиков для вкладок");
          viewTabs.addEventListener('click', e=>{ 
            if(e.target.closest('.nav-link')) {
              setTimeout(() => {
                if (App.ui && App.ui.updateTabsInk) {
                  App.ui.updateTabsInk();
                }
              }, 0); 
            }
          });
          
          const navLinks = viewTabs.querySelectorAll('.nav-link');
          navLinks.forEach(btn=>{ 
            btn.addEventListener('shown.bs.tab', () => {
              if (App.ui && App.ui.updateTabsInk) {
                App.ui.updateTabsInk();
              }
            }); 
          });
          
          viewTabs.addEventListener('scroll', U.debounce(() => {
            if (App.ui && App.ui.updateTabsInk) {
              App.ui.updateTabsInk();
            }
          }, 50));
        }
      } else {
        console.warn('App.ui.updateTabsInk не найден');
      }

      // Visual enhancers
      console.log("Инициализация визуальных улучшений...");
      if (App.ui && App.ui.initEnhancers) {
        console.log("Вызов App.ui.initEnhancers");
        App.ui.initEnhancers();
      } else {
        console.warn('App.ui.initEnhancers не найден');
      }
      
             if (App.ui && App.ui.initTabAnimations) {
         console.log("Вызов App.ui.initTabAnimations");
         App.ui.initTabAnimations();
       } else {
         console.warn('App.ui.initTabAnimations не найден');
       }
       
       if (App.ui && App.ui.initBootstrapComponents) {
         console.log("Вызов App.ui.initBootstrapComponents");
         App.ui.initBootstrapComponents();
       } else {
         console.warn('App.ui.initBootstrapComponents не найден');
       }

      // Controls
      console.log("Настройка элементов управления...");
      if(App.chart && App.chart.setupChartControls) {
        console.log("Вызов App.chart.setupChartControls");
        App.chart.setupChartControls();
      } else {
        console.warn("App.chart.setupChartControls не найден");
      }
      if(App.chart && App.chart.applyAutoControlsFromStorage) {
        console.log("Вызов App.chart.applyAutoControlsFromStorage");
        App.chart.applyAutoControlsFromStorage();
      } else {
        console.warn("App.chart.applyAutoControlsFromStorage не найден");
      }
      if(App.chart && App.chart.setupAdvancedControls) {
        console.log("Вызов App.chart.setupAdvancedControls");
        App.chart.setupAdvancedControls();
      } else {
        console.warn("App.chart.setupAdvancedControls не найден");
      }
      if(App.logs && App.logs.setupLogsControls) {
        console.log("Вызов App.logs.setupLogsControls");
        App.logs.setupLogsControls();
      } else {
        console.warn("App.logs.setupLogsControls не найден");
      }
      if(App.logs && App.logs.setupLogsAllControls) {
        console.log("Вызов App.logs.setupLogsAllControls");
        App.logs.setupLogsAllControls();
      } else {
        console.warn("App.logs.setupLogsAllControls не найден");
      }
      if(App.csv && App.csv.setupCsvPreviewControls) {
        console.log("Вызов App.csv.setupCsvPreviewControls");
        App.csv.setupCsvPreviewControls();
      } else {
        console.warn("App.csv.setupCsvPreviewControls не найден");
      }

      // Global refresh & positions actions
      const refreshAll = $("#refreshAll");
      if (refreshAll && refreshAll.length) {
        refreshAll.on("click", async ()=>{ 
          try {
            if(App.chart && App.chart.drawChart) {
              await Promise.all([
                App.state && App.state.loadState ? App.state.loadState() : Promise.resolve(),
                App.chart.drawChart(false), 
                App.logs && App.logs.loadLogTail ? App.logs.loadLogTail() : Promise.resolve(),
                App.logs && App.logs.loadLogsAll ? App.logs.loadLogsAll() : Promise.resolve(),
                App.csv && App.csv.loadCsvPreview ? App.csv.loadCsvPreview() : Promise.resolve()
              ]); 
              if(App.chart.startFabCountdown) App.chart.startFabCountdown(); 
            }
            if (U.showSnack) {
              U.showSnack("Данные обновлены"); 
            }
          } catch (e) {
            console.error('Ошибка при обновлении данных:', e);
            if (U.showSnack) {
              U.showSnack("Ошибка обновления данных"); 
            }
          }
        });
      }
      
      const posRefresh = $("#posRefresh");
      if (posRefresh && posRefresh.length) {
        posRefresh.on("click", ()=>{ 
          if (App.state && App.state.loadState) {
            App.state.loadState();
          }
          if (U.showSnack) {
            U.showSnack("Позиции обновлены"); 
          }
        });
      }
      
      const posExport = $("#posExport");
      if (posExport && posExport.length) {
        posExport.on("click", () => {
          if (App.state && App.state.exportPositionsCsv) {
            App.state.exportPositionsCsv();
          }
        });
      }

      // Initial data
      console.log("Загрузка начальных данных...");
      if(App.chart && App.chart.loadCsvList) {
        console.log("Вызов App.chart.loadCsvList");
        try {
          await Promise.all([
            App.chart.loadCsvList(), 
            App.logs && App.logs.loadLogFiles ? App.logs.loadLogFiles() : Promise.resolve(),
            App.state && App.state.loadState ? App.state.loadState() : Promise.resolve()
          ]);
          // первый график с анимацией
          if(App.chart.drawChart) {
            console.log("Вызов App.chart.drawChart(true)");
            await App.chart.drawChart(true);
          } else {
            console.warn("App.chart.drawChart не найден");
          }
        } catch (e) {
          console.error('Ошибка при загрузке начальных данных:', e);
        }
      } else {
        console.warn("App.chart.loadCsvList не найден");
        try {
          await Promise.all([
            App.logs && App.logs.loadLogFiles ? App.logs.loadLogFiles() : Promise.resolve(),
            App.state && App.state.loadState ? App.state.loadState() : Promise.resolve()
          ]);
        } catch (e) {
          console.error('Ошибка при загрузке начальных данных:', e);
        }
      }
      
      // Strategy Voting initialization
      console.log("Инициализация модуля голосования стратегий...");
      if (App.strategyVoting && App.strategyVoting.init) {
        console.log("Вызов App.strategyVoting.init");
        App.strategyVoting.init();
      } else {
        console.warn('App.strategyVoting.init не найден');
      }
      
      // KPI initialization
      console.log("Инициализация KPI модуля...");
      if (App.kpi && App.kpi.init) {
        console.log("Вызов App.kpi.init");
        App.kpi.init();
      } else {
        console.warn('App.kpi.init не найден');
      }
      
      if(App.logs && App.logs.loadLogTail) {
        console.log("Вызов App.logs.loadLogTail");
        await App.logs.loadLogTail();
      } else {
        console.warn("App.logs.loadLogTail не найден");
      }
      if(App.logs && App.logs.loadLogsAll) {
        console.log("Вызов App.logs.loadLogsAll");
        await App.logs.loadLogsAll();
      } else {
        console.warn("App.logs.loadLogsAll не найден");
      }

      // Timers & small touches
      console.log("Запуск таймеров...");
      if(App.chart && App.chart.startChartTimer) {
        console.log("Вызов App.chart.startChartTimer");
        App.chart.startChartTimer();
      } else {
        console.warn("App.chart.startChartTimer не найден");
      }
      if(App.chart && App.chart.startFabCountdown) {
        console.log("Вызов App.chart.startFabCountdown");
        App.chart.startFabCountdown();
      } else {
        console.warn("App.chart.startFabCountdown не найден");
      }
      if(App.state && App.state.startStateTimer) {
        console.log("Вызов App.state.startStateTimer");
        App.state.startStateTimer();
      } else {
        console.warn("App.state.startStateTimer не найден");
      }
      if(App.ui && App.ui.randomizeSkeletons) {
        console.log("Вызов App.ui.randomizeSkeletons");
        App.ui.randomizeSkeletons();
      } else {
        console.warn("App.ui.randomizeSkeletons не найден");
      }

      // Обновление humanize «на вид»
      document.addEventListener("visibilitychange", ()=>{ 
        if(document.visibilityState==="visible" && U && U.humanizeUpdated){ 
          const kpiUpdated = $("#kpi-updated");
          if (kpiUpdated && kpiUpdated.length) {
            const iso = kpiUpdated.data("iso"); 
            kpiUpdated.text(U.humanizeUpdated(iso)); 
          }
        } 
      });
      
      const chartTab = document.getElementById("chart-tab");
      if (chartTab) {
        chartTab.addEventListener("shown.bs.tab", ()=>{ 
          if(App.chart && App.chart.startChartTimer) App.chart.startChartTimer(); 
          if(App.chart && App.chart.drawChart) App.chart.drawChart(false); 
        });
      }

      // Очистка ресурсов при выгрузке страницы
      window.addEventListener('beforeunload', () => {
        try {
          if(App.chart && App.chart.cleanup) App.chart.cleanup();
          if(App.logs && App.logs.cleanup) App.logs.cleanup();
          if(App.state && App.state.cleanup) App.state.cleanup();
          if(App.csv && App.csv.cleanup) App.csv.cleanup();
          if(App.ui && App.ui.cleanup) App.ui.cleanup();
          if(App.theme && App.theme.cleanup) App.theme.cleanup();
          if(App.util && App.util.cleanup) App.util.cleanup();
          if(App.apiInfo && App.apiInfo.cleanup) App.apiInfo.cleanup();
          if(App.strategyVoting && App.strategyVoting.cleanup) App.strategyVoting.cleanup();
          if(App.kpi && App.kpi.cleanup) App.kpi.cleanup();
        } catch (e) {
          console.warn('Ошибка при очистке ресурсов:', e);
        }
      });

      // Убираем доступ к внутренним таймерам модулей; модули сами учитывают visibility
      // Здесь оставляем только мягкое перезапускание публичных таймеров при возврате
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
          try {
            if(App.chart && App.chart.startChartTimer) App.chart.startChartTimer();
            if(App.state && App.state.startStateTimer) App.state.startStateTimer();
          } catch (e) {
            console.warn('Ошибка при перезапуске таймеров:', e);
          }
        }
      });
      
    } catch (e) {
      console.error('Критическая ошибка при инициализации дашборда:', e);
    }
  });
})();
