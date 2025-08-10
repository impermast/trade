// Entry point: wire everything together
(function(){
  const U = window.App.util;

  $(async function(){
    // Theme & health
    App.theme.initTheme();
    U.pingHealth();
    setInterval(U.pingHealth, 5000);

    // Tabs ink init & listeners
    U.updateTabsInk();
    window.addEventListener('resize', U.debounce(U.updateTabsInk, 100));
    document.getElementById("viewTabs").addEventListener("click", e=>{ if(e.target.closest('.nav-link')) setTimeout(U.updateTabsInk, 0); });
    document.querySelectorAll('#viewTabs .nav-link').forEach(btn=>{ btn.addEventListener('shown.bs.tab', U.updateTabsInk); });
    document.getElementById("viewTabs").addEventListener('scroll', U.debounce(U.updateTabsInk, 50));

    // Visual enhancers
    App.ui.initEnhancers();

    // Controls
    App.chart.setupChartControls();
    App.chart.applyAutoControlsFromStorage();
    App.chart.setupAdvancedControls();
    App.logs.setupLogsControls();
    App.logs.setupLogsAllControls();
    App.csv.setupCsvPreviewControls();

    // Global refresh & positions actions
    $("#refreshAll").on("click", async ()=>{ await Promise.all([App.state.loadState(), App.chart.drawChart(false), App.logs.loadLogTail(), App.logs.loadLogsAll(), App.csv.loadCsvPreview()]); App.chart.startFabCountdown(); U.showSnack("Данные обновлены"); });
    $("#posRefresh").on("click", ()=>{ App.state.loadState(); U.showSnack("Позиции обновлены"); });
    $("#posExport").on("click", App.state.exportPositionsCsv);

    // Initial data
    await Promise.all([App.chart.loadCsvList(), App.logs.loadLogFiles(), App.state.loadState()]);
    // первый график с анимацией
    await App.chart.drawChart(true);
    await App.logs.loadLogTail();
    await App.logs.loadLogsAll();

    // Timers & small touches
    App.chart.startChartTimer();
    App.chart.startFabCountdown();
    App.state.startStateTimer();
    App.ui.randomizeSkeletons();

    // Обновление humanize «на вид»
    document.addEventListener("visibilitychange", ()=>{ if(document.visibilityState==="visible"){ const iso=$("#kpi-updated").data("iso"); $("#kpi-updated").text(U.humanizeUpdated(iso)); } });
    document.getElementById("chart-tab").addEventListener("shown.bs.tab", ()=>{ App.chart.startChartTimer(); App.chart.drawChart(false); });
  });
})();
