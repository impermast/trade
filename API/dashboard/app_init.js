// Entry point: wire everything together
(function(){
  const U = window.App.util;

  $(async function(){
    // Theme & health
    App.theme.initTheme();
    U.pingHealth();
    setInterval(U.pingHealth, 5000);

    // Tabs ink init & listeners
    App.ui.updateTabsInk();
    window.addEventListener('resize', U.debounce(App.ui.updateTabsInk, 100));
    document.getElementById("viewTabs").addEventListener("click", e=>{ if(e.target.closest('.nav-link')) setTimeout(App.ui.updateTabsInk, 0); });
    document.querySelectorAll('#viewTabs .nav-link').forEach(btn=>{ btn.addEventListener('shown.bs.tab', App.ui.updateTabsInk); });
    document.getElementById("viewTabs").addEventListener('scroll', U.debounce(App.ui.updateTabsInk, 50));

    // Visual enhancers
    App.ui.initEnhancers();
    App.ui.initTabAnimations();

    // Controls
    if(App.chart && App.chart.setupChartControls) App.chart.setupChartControls();
    if(App.chart && App.chart.applyAutoControlsFromStorage) App.chart.applyAutoControlsFromStorage();
    if(App.chart && App.chart.setupAdvancedControls) App.chart.setupAdvancedControls();
    if(App.logs && App.logs.setupLogsControls) App.logs.setupLogsControls();
    if(App.logs && App.logs.setupLogsAllControls) App.logs.setupLogsAllControls();
    if(App.csv && App.csv.setupCsvPreviewControls) App.csv.setupCsvPreviewControls();

    // Global refresh & positions actions
    $("#refreshAll").on("click", async ()=>{ 
      if(App.chart && App.chart.drawChart) {
        await Promise.all([App.state.loadState(), App.chart.drawChart(false), App.logs.loadLogTail(), App.logs.loadLogsAll(), App.csv.loadCsvPreview()]); 
        if(App.chart.startFabCountdown) App.chart.startFabCountdown(); 
      }
      U.showSnack("Данные обновлены"); 
    });
    $("#posRefresh").on("click", ()=>{ App.state.loadState(); U.showSnack("Позиции обновлены"); });
    $("#posExport").on("click", App.state.exportPositionsCsv);

    // Initial data
    if(App.chart && App.chart.loadCsvList) {
      await Promise.all([
        App.chart.loadCsvList(), 
        App.logs && App.logs.loadLogFiles ? App.logs.loadLogFiles() : Promise.resolve(),
        App.state && App.state.loadState ? App.state.loadState() : Promise.resolve()
      ]);
      // первый график с анимацией
      if(App.chart.drawChart) await App.chart.drawChart(true);
    } else {
      await Promise.all([
        App.logs && App.logs.loadLogFiles ? App.logs.loadLogFiles() : Promise.resolve(),
        App.state && App.state.loadState ? App.state.loadState() : Promise.resolve()
      ]);
    }
    if(App.logs && App.logs.loadLogTail) await App.logs.loadLogTail();
    if(App.logs && App.logs.loadLogsAll) await App.logs.loadLogsAll();

    // Timers & small touches
    if(App.chart && App.chart.startChartTimer) App.chart.startChartTimer();
    if(App.chart && App.chart.startFabCountdown) App.chart.startFabCountdown();
    if(App.state && App.state.startStateTimer) App.state.startStateTimer();
    if(App.ui && App.ui.randomizeSkeletons) App.ui.randomizeSkeletons();

    // Обновление humanize «на вид»
    document.addEventListener("visibilitychange", ()=>{ 
      if(document.visibilityState==="visible" && U && U.humanizeUpdated){ 
        const iso=$("#kpi-updated").data("iso"); 
        $("#kpi-updated").text(U.humanizeUpdated(iso)); 
      } 
    });
    document.getElementById("chart-tab").addEventListener("shown.bs.tab", ()=>{ 
      if(App.chart && App.chart.startChartTimer) App.chart.startChartTimer(); 
      if(App.chart && App.chart.drawChart) App.chart.drawChart(false); 
    });

    // Очистка ресурсов при выгрузке страницы
    window.addEventListener('beforeunload', () => {
      try {
        if(App.chart && App.chart.cleanup) App.chart.cleanup();
        if(App.logs && App.logs.cleanup) App.logs.cleanup();
        if(App.state && App.state.cleanup) App.state.cleanup();
        if(App.csv && App.csv.cleanup) App.csv.cleanup();
        if(App.ui && App.ui.cleanup) App.ui.cleanup();
        if(App.theme && App.theme.cleanup) App.theme.cleanup();
      } catch (e) {
        console.warn('Ошибка при очистке ресурсов:', e);
      }
    });
  });
})();
