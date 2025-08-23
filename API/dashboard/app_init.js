// Entry point: wire everything together with improved initialization
(function(){
  // Ждем загрузки core модуля
  function waitForCore() {
    return new Promise((resolve) => {
      const check = () => {
        if (window.App && window.App.ModuleManager) {
          resolve();
        } else {
          setTimeout(check, 50);
        }
      };
      check();
    });
  }

  // Основная функция инициализации
  async function initializeDashboard() {
    try {
      console.log("🚀 Начинаем инициализацию дашборда...");
      
      const ModuleManager = window.App.ModuleManager;
      const util = window.App.util;
      
      if (!ModuleManager || !util) {
        throw new Error('Core модуль не инициализирован');
      }

      // Глобальный переключатель подробных логов
      const DEBUG = (localStorage.getItem('debug') === '1');
      if (!DEBUG) {
        try { console.log = function(){}; } catch (e) {} 
      }

      // 1. ИНИЦИАЛИЗАЦИЯ ТЕМЫ (приоритет 100)
      ModuleManager.addToInitQueue(async () => {
        console.log("🎨 Инициализация темы...");
        if (App.theme && App.theme.initTheme) {
          App.theme.initTheme();
          console.log("✅ Тема инициализирована");
        } else {
          console.warn('⚠️ App.theme.initTheme не найден');
        }
      }, 100);

      // 2. ИНИЦИАЛИЗАЦИЯ UI КОМПОНЕНТОВ (приоритет 90)
      ModuleManager.addToInitQueue(async () => {
        console.log("🎭 Инициализация UI компонентов...");
        
        // Tabs ink init & listeners
        if (App.ui && App.ui.updateTabsInk) {
          App.ui.updateTabsInk();
          window.addEventListener('resize', util.debounce(App.ui.updateTabsInk, 100));
          
          const viewTabs = document.getElementById("viewTabs");
          if (viewTabs) {
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
            
            viewTabs.addEventListener('scroll', util.debounce(() => {
              if (App.ui && App.ui.updateTabsInk) {
                App.ui.updateTabsInk();
              }
            }, 50));
          }
        }

        // Visual enhancers
        if (App.ui && App.ui.initEnhancers) {
          App.ui.initEnhancers();
        }
        
        if (App.ui && App.ui.initTabAnimations) {
          App.ui.initTabAnimations();
        }
        
        if (App.ui && App.ui.initBootstrapComponents) {
          App.ui.initBootstrapComponents();
        }

        // Randomize skeletons
        if (App.ui && App.ui.randomizeSkeletons) {
          App.ui.randomizeSkeletons();
        }

        console.log("✅ UI компоненты инициализированы");
      }, 90);

      // 3. ИНИЦИАЛИЗАЦИЯ API ИНФОРМАЦИИ (приоритет 80)
      ModuleManager.addToInitQueue(async () => {
        console.log("📡 Инициализация API информации...");
        
        if (App.apiInfo && App.apiInfo.startApiInfoTimer) {
          App.apiInfo.startApiInfoTimer();
        }

        // Менеджер пинга с паузой при скрытии вкладки
        if (util.pingHealth) {
          let _pingTimer = null;
          const startPing = () => {
            if (_pingTimer) { clearInterval(_pingTimer); _pingTimer = null; }
            // Мгновенный пинг
            try { util.pingHealth(); } catch (e) {}
            // Запускаем периодический пинг только когда вкладка видима
            _pingTimer = setInterval(() => {
              if (document.visibilityState === 'visible') {
                try { util.pingHealth(); } catch (e) {}
              }
            }, 5000);
          };
          const stopPing = () => { if (_pingTimer) { clearInterval(_pingTimer); _pingTimer = null; } };
          startPing();
          document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') startPing(); else stopPing();
          });
        }

        console.log("✅ API информация инициализирована");
      }, 80);

      // 4. НАСТРОЙКА ЭЛЕМЕНТОВ УПРАВЛЕНИЯ (приоритет 70)
      ModuleManager.addToInitQueue(async () => {
        console.log("🎛️ Настройка элементов управления...");
        
        // Chart controls
        if(App.chart && App.chart.setupChartControls) {
          App.chart.setupChartControls();
        }
        if(App.chart && App.chart.applyAutoControlsFromStorage) {
          App.chart.applyAutoControlsFromStorage();
        }
        if(App.chart && App.chart.setupAdvancedControls) {
          App.chart.setupAdvancedControls();
        }

        // Logs controls
        if(App.logs && App.logs.setupLogsControls) {
          App.logs.setupLogsControls();
        }
        if(App.logs && App.logs.setupLogsAllControls) {
          App.logs.setupLogsAllControls();
        }

        // CSV controls
        if(App.csv && App.csv.setupCsvPreviewControls) {
          App.csv.setupCsvPreviewControls();
        }

        console.log("✅ Элементы управления настроены");
      }, 70);

      // 5. НАСТРОЙКА ГЛОБАЛЬНЫХ ОБРАБОТЧИКОВ (приоритет 60)
      ModuleManager.addToInitQueue(async () => {
        console.log("🔗 Настройка глобальных обработчиков...");
        
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
              if (util.showSnack) {
                util.showSnack("Данные обновлены"); 
              }
            } catch (e) {
              console.error('❌ Ошибка при обновлении данных:', e);
              if (util.showSnack) {
                util.showSnack("Ошибка обновления данных"); 
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
            if (util.showSnack) {
              util.showSnack("Позиции обновлены"); 
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

        // Chart tab activation handler
        const chartTab = document.getElementById("chart-tab");
        if (chartTab) {
          chartTab.addEventListener("shown.bs.tab", ()=>{ 
            if(App.chart && App.chart.startChartTimer) App.chart.startChartTimer(); 
            if(App.chart && App.chart.drawChart) App.chart.drawChart(false); 
          });
        }

        // Humanize update on visibility change
        document.addEventListener("visibilitychange", ()=>{ 
          if(document.visibilityState==="visible" && util && util.humanizeUpdated){ 
            const kpiUpdated = $("#kpi-updated");
            if (kpiUpdated && kpiUpdated.length) {
              const iso = kpiUpdated.data("iso"); 
              kpiUpdated.text(util.humanizeUpdated(iso)); 
            }
          } 
        });

        console.log("✅ Глобальные обработчики настроены");
      }, 60);

      // 6. ЗАГРУЗКА НАЧАЛЬНЫХ ДАННЫХ (приоритет 50)
      ModuleManager.addToInitQueue(async () => {
        console.log("📊 Загрузка начальных данных...");
        
        try {
          await Promise.all([
            App.chart && App.chart.loadCsvList ? App.chart.loadCsvList() : Promise.resolve(),
            App.logs && App.logs.loadLogFiles ? App.logs.loadLogFiles() : Promise.resolve(),
            App.state && App.state.loadState ? App.state.loadState() : Promise.resolve()
          ]);

          // Первый график с анимацией
          if(App.chart && App.chart.drawChart) {
            await App.chart.drawChart(true);
          }

          // Загрузка логов
          if(App.logs && App.logs.loadLogTail) {
            await App.logs.loadLogTail();
          }
          if(App.logs && App.logs.loadLogsAll) {
            await App.logs.loadLogsAll();
          }

          console.log("✅ Начальные данные загружены");
        } catch (e) {
          console.error('❌ Ошибка при загрузке начальных данных:', e);
        }
      }, 50);

      // 7. ИНИЦИАЛИЗАЦИЯ СПЕЦИАЛИЗИРОВАННЫХ МОДУЛЕЙ (приоритет 40)
      ModuleManager.addToInitQueue(async () => {
        console.log("🔧 Инициализация специализированных модулей...");
        
        // Strategy Voting
        if (App.strategyVoting && App.strategyVoting.init) {
          App.strategyVoting.init();
        }
        
        // KPI
        if (App.kpi && App.kpi.init) {
          App.kpi.init();
        }

        console.log("✅ Специализированные модули инициализированы");
      }, 40);

      // 8. ЗАПУСК ТАЙМЕРОВ (приоритет 30)
      ModuleManager.addToInitQueue(async () => {
        console.log("⏰ Запуск таймеров...");
        
        if(App.chart && App.chart.startChartTimer) {
          App.chart.startChartTimer();
        }
        if(App.chart && App.chart.startFabCountdown) {
          App.chart.startFabCountdown();
        }
        if(App.state && App.state.startStateTimer) {
          App.state.startStateTimer();
        }

        console.log("✅ Таймеры запущены");
      }, 30);

      // 9. ФИНАЛЬНАЯ НАСТРОЙКА (приоритет 20)
      ModuleManager.addToInitQueue(async () => {
        console.log("🎯 Финальная настройка...");
        
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
            console.warn('⚠️ Ошибка при очистке ресурсов:', e);
          }
        });

        // Перезапуск таймеров при возврате на вкладку
        document.addEventListener('visibilitychange', () => {
          if (document.visibilityState === 'visible') {
            try {
              if(App.chart && App.chart.startChartTimer) App.chart.startChartTimer();
              if(App.state && App.state.startStateTimer) App.state.startStateTimer();
            } catch (e) {
              console.warn('⚠️ Ошибка при перезапуске таймеров:', e);
            }
          }
        });

        console.log("✅ Финальная настройка завершена");
      }, 20);

      // Запускаем инициализацию
      console.log("🚀 Запуск инициализации модулей...");
      await ModuleManager.executeInit();
      
      console.log("🎉 Дашборд полностью инициализирован!");
      
    } catch (e) {
      console.error('❌ Критическая ошибка при инициализации дашборда:', e);
    }
  }

  // Ждем загрузки core и запускаем инициализацию
  waitForCore().then(() => {
    // Проверяем, что все необходимые модули загружены
    if (typeof window.App === 'undefined') {
      console.error('❌ App не инициализирован! Проверьте загрузку core.js');
      return;
    }
    
    // Запускаем инициализацию
    initializeDashboard();
  }).catch(e => {
    console.error('❌ Ошибка ожидания core модуля:', e);
  });

})();
