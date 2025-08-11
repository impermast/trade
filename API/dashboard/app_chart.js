(function(){
  window.App = window.App || {};
  const U = window.App.util;
  const T = window.App.theme;

  // Проверка загрузки Plotly
  if (typeof Plotly === 'undefined') {
    console.error('Plotly не загружен! Графики не могут работать корректно.');
    return;
  }

  // Проверка готовности DOM и зависимостей
  if (document.readyState === 'loading' || !U || !T) {
    document.addEventListener('DOMContentLoaded', () => {
      try {
        if (U && T) {
          initChart();
        } else {
          console.warn('Зависимости не загружены, откладываем инициализацию графика');
        }
      } catch (e) {
        console.error('Ошибка инициализации графика:', e);
      }
    });
    return;
  }

  // Если все готово, инициализируем сразу
  initChart();

  function initChart() {
    console.log("Инициализация модуля графика...");
    
    // Проверяем наличие критических элементов
    const criticalElements = {
      csvFile: $("#csvFile"),
      tailRows: $("#tailRows"),
      tailSegments: $("#tailSegments"),
      chart: $("#chart")
    };
    
    console.log("Проверка критических элементов:");
    Object.entries(criticalElements).forEach(([name, element]) => {
      console.log(`${name}:`, element.length ? "найден" : "НЕ НАЙДЕН");
    });

  // CSV list (без верхней полоски: plain fetch)
  async function loadCsvList(){
    const sel = $("#csvFile"); 
    if (!sel || !sel.length) return;
    
    sel.empty();
    try{
      const r = await fetch("/csv_list");
      let files = await r.json();
      files = Array.isArray(files)
        ? files.filter(f => typeof f === "string").filter(f => f.toLowerCase().endsWith(".csv"))
        : [];
      files.sort((a, b) => a.localeCompare(b, "ru"));
      files.forEach(f => sel.append(new Option(f, f)));
      const stored = localStorage.getItem("csv-file");
      const def = (stored && files.includes(stored)) ? stored : (files[0] || "");
      if (def) sel.val(def);
      const kpiFile = $("#kpi-file");
      if (kpiFile && kpiFile.length) {
        kpiFile.text(sel.val() || "—");
      }
    } catch {
      sel.append(new Option("BTCUSDT_1m.csv","BTCUSDT_1m.csv"));
      const kpiFile = $("#kpi-file");
      if (kpiFile && kpiFile.length) {
        kpiFile.text(sel.val() || "—");
      }
    }
  }

  // Chart helpers
  function showRsiControls(){ 
    const lowerPanel = $("#lowerPanel");
    const rsiControls = $("#rsiControls");
    if (lowerPanel && rsiControls) {
      rsiControls.toggle(lowerPanel.val()==="rsi"); 
    }
  }

  // Загрузка свечей без верхней полоски (оставляем только локальный спиннер #chartLoader)
  async function loadCandles(){
    const csvFile = $("#csvFile");
    const tailRows = $("#tailRows");
    
    if (!csvFile || !csvFile.length) {
      throw new Error("Элемент выбора CSV файла не найден");
    }
    
    const file = csvFile.val(); 
    const tail = Math.max(50, +(tailRows ? tailRows.val() : 500) || 500);
    
    const r = await fetch(`/api/candles?file=${encodeURIComponent(file)}&tail=${tail}`);
    if(!r.ok) throw new Error("Ошибка загрузки свечей");
    return await r.json();
  }

  let _lastTs = null, _currentFile = null;

  function keepRightEdge(){
    const gd = document.getElementById('chart');
    if (!gd || !gd.layout) return;
    const xa = gd.layout.xaxis || {};
    const isAuto = xa.autorange === true || typeof xa.range === "undefined";
    if (isAuto) Plotly.relayout(gd, {'xaxis.autorange': true});
  }
  
  function renderEmpty(containerId, title="Нет данных", sub="Загрузите CSV или измените фильтры"){
    const el = document.getElementById(containerId);
    if (!el) return;
    
    el.innerHTML = `
      <div class="empty">
        <svg viewBox="0 0 120 120" aria-hidden="true">
          <defs><linearGradient id="gradEmpty" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%"  stop-color="${U.cssVar('--primary')}"/>
            <stop offset="100%" stop-color="${U.cssVar('--secondary')}"/>
          </linearGradient></defs>
        <circle cx="60" cy="60" r="44" fill="url(#gradEmpty)">
          <animate attributeName="r" values="40;44;40" dur="2.8s" repeatCount="indefinite"/>
        </circle>
        <rect x="30" y="40" width="60" height="8" rx="4" fill="rgba(255,255,255,0.25)"/>
        <rect x="40" y="54" width="40" height="8" rx="4" fill="rgba(255,255,255,0.18)"/>
        </svg>
        <div class="title">${title}</div>
        <div class="sub">${sub}</div>
      </div>`;
  }

  async function drawChart(animate){
    const chartLoader = $("#chartLoader");
    if (chartLoader && chartLoader.length) {
      chartLoader.show(); // локальный спиннер
    }
    
    try{
      const rows = await loadCandles();
      if (chartLoader && chartLoader.length) {
        chartLoader.hide();
      }

      if(!rows || !rows.length){
        Plotly.purge("chart");
        renderEmpty("chart","Нет данных для отображения","Проверьте CSV и параметры");
        return;
      }

      // Полный перестроение графика — чтобы обновлялись RSI/SMA/объёмы и маркеры сигналов.
      const csvFile = $("#csvFile");
      if (!csvFile || !csvFile.length) return;
      
      const fileNow = csvFile.val() || "";
      const tsArr = rows.map(r => r.ts).filter(ts => ts != null && !isNaN(ts));
      
      // Проверяем, можно ли расширить существующий график
      const gdInc = document.getElementById('chart');
      const canExtend = (
        !animate &&
        gdInc && gdInc.data && gdInc.data.length > 0 &&
        (_currentFile === fileNow) &&
        _lastTs && tsArr.length && tsArr[tsArr.length-1] > _lastTs
      );

      if (canExtend){
        let idx = tsArr.findIndex(t => t > _lastTs);
        if (idx > -1){
          const addX = tsArr.slice(idx);
          const addO = rows.slice(idx).map(r => r.open).filter(v => v != null);
          const addH = rows.slice(idx).map(r => r.high).filter(v => v != null);
          const addL = rows.slice(idx).map(r => r.low).filter(v => v != null);
          const addC = rows.slice(idx).map(r => r.close).filter(v => v != null);

          const tailMax = Math.max(50, +$("#tailRows").val()||500);

          Plotly.extendTraces(gdInc,
            { x:[addX], open:[addO], high:[addH], low:[addL], close:[addC] },
            [0], tailMax
          );

          _lastTs = tsArr[tsArr.length-1];
          keepRightEdge();
          const kpiFile = $("#kpi-file");
          if (kpiFile && kpiFile.length) {
            kpiFile.text($("#csvFile").val()||"—");
          }
          return;
        }
      }

      const ts    = rows.map(r=>r.ts);
      const open  = rows.map(r=>r.open);
      const high  = rows.map(r=>r.high);
      const low   = rows.map(r=>r.low);
      const close = rows.map(r=>r.close);
      const vol   = rows.map(r=>r.volume ?? null);

      const ord_rsi = rows.map(r => (r.orders_rsi ?? r.orders ?? null));
      const ord_xgb = rows.map(r => (r.orders_xgb ?? null));

      const traces=[];
      const cPrimary   = U.cssVar("--primary");
      const cSecondary = U.cssVar("--secondary");
      const cTertiary  = "#9C27B0";
      const cError     = U.cssVar("--error");

      const lowerIsVolume = $("#lowerPanel").val()==="volume";
      const isLog = $("#logScale").is(":checked");

      const lows  = low .filter(v => Number.isFinite(v));
      const highs = high.filter(v => Number.isFinite(v));
      let pMin = Math.min(...lows);
      let pMax = Math.max(...highs);
      if (!Number.isFinite(pMin) || !Number.isFinite(pMax)) { pMin = 0; pMax = 1; }
      if (isLog) {
        const positives = [].concat(open,high,low,close).filter(v => Number.isFinite(v) && v>0);
        const minPos = positives.length ? Math.min(...positives) : 1e-6;
        pMin = Math.max(pMin, minPos*0.95);
      }
      const pad = (pMax - pMin) * 0.04 || pMin*0.04 || 1;
      const yPriceRange = isLog ? [pMin*0.98, pMax*1.02] : [pMin - pad, pMax + pad];

      let y2Range;
      if (lowerIsVolume){
        const vVals = vol.filter(v => Number.isFinite(v));
        const vmax  = vVals.length ? Math.max(...vVals) : 1;
        y2Range = [0, vmax*1.15];
      } else {
        y2Range = [0, 100];
      }

      // Candles
      traces.push({
        type:"candlestick", x:ts, open, high, low, close, name:"OHLC", yaxis:"y",
        increasing:{line:{color:cSecondary, width:1}}, decreasing:{line:{color:cError, width:1}}
      });

      if($("#sma20").is(":checked"))
        traces.push({type:"scatter",mode:"lines",x:ts,y:U.sma(close,20),line:{width:1.8,color:cPrimary},name:"SMA 20",yaxis:"y"});
      if($("#sma50").is(":checked"))
        traces.push({type:"scatter",mode:"lines",x:ts,y:U.sma(close,50),line:{width:1.8,color:cTertiary},name:"SMA 50",yaxis:"y"});

      if (lowerIsVolume){
        traces.push({type:"bar", x:ts, y:vol, name:"Объём", opacity:.35, yaxis:"y2"});
      } else {
        const p=Math.max(2,+$("#rsiPeriod").val()||14), rv=U.rsi(close,p);
        traces.push({type:"scatter",mode:"lines",x:ts,y:rv,name:`RSI ${p}`,yaxis:"y2", line:{width:1.4}});
        traces.push({type:"scatter",mode:"lines",x:[ts[0],ts.at(-1)],y:[70,70],line:{dash:"dot",width:1},showlegend:false,yaxis:"y2"});
        traces.push({type:"scatter",mode:"lines",x:[ts[0],ts.at(-1)],y:[30,30],line:{dash:"dot",width:1},showlegend:false,yaxis:"y2"});
      }

      // Signal markers
      function addSignalMarkers(ordersArr, namePrefix) {
        if (!ordersArr.some(o => o != null && o !== 0)) return;
        const bx=[],by=[], sx=[],sy=[];
        for (let i = 0; i < ordersArr.length; i++) {
          if (ordersArr[i] > 0) { bx.push(ts[i]); by.push(close[i]); }
          if (ordersArr[i] < 0) { sx.push(ts[i]); sy.push(close[i]); }
        }
        const buyColor  = namePrefix==="RSI" ? "#00e68a" : "#1ea7ff";
        const sellColor = namePrefix==="RSI" ? "#ff5a3d" : "#ff2ea6";

        if (bx.length) traces.push({type:"scatter", mode:"markers", x:bx, y:by, name:`${namePrefix} glow1 up`, marker:{ size:24, symbol:"triangle-up", color:buyColor, opacity:.12 }, yaxis:"y", hoverinfo:"skip", showlegend:false});
        if (sx.length) traces.push({type:"scatter", mode:"markers", x:sx, y:sy, name:`${namePrefix} glow1 dn`, marker:{ size:24, symbol:"triangle-down", color:sellColor, opacity:.12 }, yaxis:"y", hoverinfo:"skip", showlegend:false});
        if (bx.length) traces.push({type:"scatter", mode:"markers", x:bx, y:by, name:`${namePrefix} glow2 up`, marker:{ size:18, symbol:"triangle-up", color:buyColor, opacity:.20 }, yaxis:"y", hoverinfo:"skip", showlegend:false});
        if (sx.length) traces.push({type:"scatter", mode:"markers", x:sx, y:sy, name:`${namePrefix} glow2 dn`, marker:{ size:18, symbol:"triangle-down", color:sellColor, opacity:.20 }, yaxis:"y", hoverinfo:"skip", showlegend:false});
        if (bx.length) traces.push({type:"scatter", mode:"markers", x:bx, y:by, name:`${namePrefix} Buy`, marker:{ size:12, symbol:"triangle-up", color:buyColor, line:{width:1.5, color:"#fff"} }, yaxis:"y"});
        if (sx.length) traces.push({type:"scatter", mode:"markers", x:sx, y:sy, name:`${namePrefix} Sell`, marker:{ size:12, symbol:"triangle-down", color:sellColor, line:{width:1.5, color:"#fff"} }, yaxis:"y"});
      }
      if ($("#signals_rsi").is(":checked")) addSignalMarkers(ord_rsi, "RSI");
      if ($("#signals_xgb").is(":checked")) addSignalMarkers(ord_xgb, "XGB");

      const {paper_bgcolor,plot_bgcolor,font_color,grid}=T.themeVars();
      const layout={
        dragmode:"zoom",
        showlegend:true,
        legend:{ orientation:"h", y:1.12, x:1, xanchor:"right", bgcolor:"rgba(0,0,0,0)", borderwidth:0, font:{size:11} },
        margin:{t:20,r:10,b:40,l:50}, paper_bgcolor, plot_bgcolor, font:{color:font_color},
        xaxis:{ gridcolor:grid, gridwidth:0.4, ticklen:4, ticks:"outside", nticks: 8, anchor:"y", domain:[0,1], autorange:true },
        yaxis:{ title:"Цена", type:(isLog?"log":"linear"), gridcolor:grid, gridwidth:0.4, ticklen:4, ticks:"outside", domain:[0.35,1], autorange:false, range:yPriceRange },
        xaxis2:{gridcolor:grid, gridwidth:0.4, anchor:"y2", domain:[0,1], matches:"x", nticks:6, ticklen:3 },
        yaxis2:{ title: ($("#lowerPanel").val()==="volume" ? "Объём" : "RSI"), gridcolor:grid, gridwidth:0.4, domain:[0,0.28], autorange:false, range:y2Range, ticklen:3, ticks:"outside" }
      };

      const gd = document.getElementById("chart");
      await Plotly.react(gd, traces, layout, { responsive:true, displaylogo:false, displayModeBar:false });

      if (animate) {
        const N = ts.length;
        if (N > 1) {
          let lastK = Math.min(2, N);
          await Plotly.restyle(gd, {
            x:    [ts.slice(0, lastK)],
            open: [open.slice(0, lastK)],
            high: [high.slice(0, lastK)],
            low:  [low.slice(0, lastK)],
            close:[close.slice(0, lastK)]
          }, [0]);

          const duration = 1100;
          const t0 = performance.now();
          const easeIn = t => t*t*t;

          function step(now){
            let p = (now - t0) / duration;
            p = Math.max(0, Math.min(1, p));
            const e = easeIn(p);
            const k = Math.max(lastK, Math.min(N, Math.floor(1 + e * (N - 1))));

            if (k !== lastK){
              Plotly.restyle(gd, {
                x:    [ts.slice(0, k)],
                open: [open.slice(0, k)],
                high: [high.slice(0, k)],
                low:  [low.slice(0, k)],
                close:[close.slice(0, k)]
              }, [0]);
              lastK = k;
            }
            if (p < 1){ requestAnimationFrame(step); }
            else { Plotly.restyle(gd, { x:[ts], open:[open], high:[high], low:[low], close:[close] }, [0]); }
          }
          requestAnimationFrame(step);
        }
      }

      _currentFile = fileNow;
      if (rows && rows.length) _lastTs = rows[rows.length-1].ts;
      const kpiFile = $("#kpi-file");
      if (kpiFile && kpiFile.length) {
        kpiFile.text($("#csvFile").val()||"—");
      }
    } catch(e) {
      console.error('Ошибка при отрисовке графика:', e);
      if (chartLoader && chartLoader.length) {
        chartLoader.hide();
      }
      
      // Более информативное сообщение об ошибке
      let errorMessage = "Проверьте CSV и колонки (time/open/high/low/close)";
      if (e.message) {
        if (e.message.includes('fetch')) {
          errorMessage = "Ошибка сети. Проверьте подключение к серверу.";
        } else if (e.message.includes('JSON')) {
          errorMessage = "Ошибка формата данных. Проверьте CSV файл.";
        } else if (e.message.includes('CSV')) {
          errorMessage = "Ошибка CSV файла. Проверьте структуру данных.";
        }
      }
      
      renderEmpty("chart", "Ошибка загрузки", errorMessage);
    }
  }

  // Auto refresh + ring
  let chartTimer=null, fabRAF=null, nextRefreshAt=0;
  const CHART_INTERVAL_KEY="chart-interval-seconds";
  const CHART_AUTO_KEY="chart-auto";
  function getChartInterval(){
    const v = +($("#chartInterval").val() || localStorage.getItem(CHART_INTERVAL_KEY) || 10);
    return Math.max(5, v|0);
  }
  function isChartAutoOn(){
    const saved = localStorage.getItem(CHART_AUTO_KEY);
    if (saved === null) return true;
    return saved === "1";
  }
  function applyAutoControlsFromStorage(){
    $("#autoRefreshChart").prop("checked", isChartAutoOn());
    const iv = +localStorage.getItem(CHART_INTERVAL_KEY) || 10;
    $("#chartInterval").val(iv);
  }
  function updateFabRing(){
    const ring = document.getElementById('fabRing');
    const btn  = document.getElementById('reloadChart');
    if (!ring || !btn) return;

    const C = 2*Math.PI*16;
    ring.style.strokeDasharray = C.toFixed(1);

    const auto = $("#autoRefreshChart").is(":checked");
    btn.classList.toggle("disabled", !auto);

    if (!auto){
      ring.style.strokeDashoffset = C.toFixed(1);
      return;
    }

    const iv = getChartInterval()*1000;
    const now = performance.now();
    const remain = Math.max(0, nextRefreshAt - now);
    const progress = 1 - (remain/iv);
    ring.style.strokeDashoffset = (C*(1-progress)).toFixed(1);

    // Останавливаем анимацию, если до следующего обновления меньше 100мс
    if (remain > 100) {
      fabRAF = requestAnimationFrame(updateFabRing);
    }
  }
  function startFabCountdown(){
    if (fabRAF) cancelAnimationFrame(fabRAF);
    nextRefreshAt = performance.now() + getChartInterval()*1000;
    fabRAF = requestAnimationFrame(updateFabRing);
  }
  function startChartTimer(){
    // Очищаем предыдущий таймер
    if(chartTimer){ clearInterval(chartTimer); chartTimer=null; }
    
    const auto = $("#autoRefreshChart").is(":checked");
    if(!auto){
      // Очищаем RAF если автообновление выключено
      if (fabRAF) { cancelAnimationFrame(fabRAF); fabRAF=null; }
      updateFabRing();
      return;
    }
    
    const iv = getChartInterval()*1000;
    startFabCountdown();
    
    // Создаем новый таймер с проверкой видимости
    chartTimer = setInterval(()=>{
      if(document.visibilityState==="visible" && $("#chart-pane").hasClass("active")){
        drawChart(false); 
        startFabCountdown();
      }
    }, iv);
  }

  // Controls
  function setupChartControls(){
    console.log("Настройка элементов управления графика...");
    const reloadChart = $("#reloadChart");
    if (reloadChart && reloadChart.length) {
      reloadChart.on("click", ()=>{ drawChart(false); startFabCountdown(); U.showSnack("График перестроен"); const btn=document.getElementById('reloadChart'); btn.classList.remove('pulse'); void btn.offsetWidth; btn.classList.add('pulse'); });
    }
    const resetZoom = $("#resetZoom");
    if (resetZoom && resetZoom.length) {
      resetZoom.on("click", ()=>{ Plotly.relayout('chart', {'xaxis.autorange':true,'yaxis.autorange':true,'yaxis2.autorange':true}); U.showSnack("Масштаб сброшен"); });
    }

    const csvFile = $("#csvFile");
    if (csvFile && csvFile.length) {
      csvFile.on("change", ()=>{ 
        localStorage.setItem("csv-file", csvFile.val()||""); 
        // Сбрасываем переменные оптимизации при смене файла
        _currentFile = null;
        _lastTs = null;
        drawChart(true); 
      });
    }
    const tailRows = $("#tailRows");
    if (tailRows && tailRows.length) {
      tailRows.on("change", U.debounce(()=> {
        // Сбрасываем переменные оптимизации при изменении количества строк
        _currentFile = null;
        _lastTs = null;
        drawChart(true);
      }, 300));
    }
    const lowerPanel = $("#lowerPanel");
    if (lowerPanel && lowerPanel.length) {
      lowerPanel.on("change", ()=>{ 
        showRsiControls(); 
        // Сбрасываем переменные оптимизации при изменении нижней панели
        _currentFile = null;
        _lastTs = null;
        drawChart(false); 
      });
    }
    const rsiPeriod = $("#rsiPeriod");
    if (rsiPeriod && rsiPeriod.length) {
      rsiPeriod.on("change", U.debounce(()=> {
        // Сбрасываем переменные оптимизации при изменении периода RSI
        _currentFile = null;
        _lastTs = null;
        drawChart(false);
      }, 300));
    }

    U.bindChip("#chipSMA20", "#sma20");
    U.bindChip("#chipSMA50", "#sma50");
    U.bindChip("#chipSigRSI", "#signals_rsi");
    U.bindChip("#chipSigXGB", "#signals_xgb");

    const tailSegments = $("#tailSegments");
    if (tailSegments && tailSegments.length) {
      console.log("Настройка обработчиков для кнопок быстрого хвоста");
      // Используем делегирование событий для кнопок внутри контейнера
      tailSegments.on("click", ".btn", function(e){
        e.preventDefault();
        console.log("Кнопка быстрого хвоста нажата:", $(this).data("tail"));
        
        const clickedBtn = $(this);
        const val = +clickedBtn.data("tail");
        
        // Убираем активный класс со всех кнопок и добавляем к нажатой
        tailSegments.find(".btn").removeClass("active");
        clickedBtn.addClass("active");
        
        // Устанавливаем значение в поле tailRows
        const tailRows = $("#tailRows");
        if (tailRows && tailRows.length) {
          tailRows.val(val);
          console.log("Установлено значение tailRows:", val);
        } else {
          console.warn("Поле tailRows не найдено");
        }
        
        // Сбрасываем переменные оптимизации при изменении сегмента
        _currentFile = null;
        _lastTs = null;
        
        // Перерисовываем график
        console.log("Запуск перерисовки графика");
        drawChart(true);
      });
      
      // Проверяем, что обработчики привязаны
      const buttons = tailSegments.find(".btn");
      console.log(`Привязано ${buttons.length} кнопок быстрого хвоста`);
    } else {
      console.warn("Контейнер tailSegments не найден");
    }
    showRsiControls();
  }

  // Advanced controls
  function setupAdvancedControls(){
    console.log("Настройка расширенных элементов управления...");
    // лог масштаб визуально связан со скрытым чекбоксом
    const logScaleSwitch = $("#logScaleSwitch");
    if (logScaleSwitch && logScaleSwitch.length) {
      logScaleSwitch.prop("checked", $("#logScale").is(":checked"));
      logScaleSwitch.on("change", ()=>{ 
        $("#logScale").prop("checked", logScaleSwitch.is(":checked")); 
        // Сбрасываем переменные оптимизации при изменении масштаба
        _currentFile = null;
        _lastTs = null;
        drawChart(false); 
      });
    }

    // Добавляем обработчик для скрытого чекбокса logScale
    const logScale = $("#logScale");
    if (logScale && logScale.length) {
      logScale.on("change", ()=>{
        // Сбрасываем переменные оптимизации при изменении масштаба
        _currentFile = null;
        _lastTs = null;
        drawChart(false);
      });
    }

    // persist & timer controls for auto-refresh
    const saveAuto = ()=> localStorage.setItem(CHART_AUTO_KEY, $("#autoRefreshChart").is(":checked") ? "1" : "0");
    const saveIv   = ()=> localStorage.setItem(CHART_INTERVAL_KEY, String(getChartInterval()));

    const autoRefreshChart = $("#autoRefreshChart");
    if (autoRefreshChart && autoRefreshChart.length) {
      autoRefreshChart.on("change", ()=>{ saveAuto(); startChartTimer(); updateFabRing(); U.showSnack($("#autoRefreshChart").is(":checked")?"Автообновление включено":"Автообновление выключено"); });
    }
    const chartInterval = $("#chartInterval");
    if (chartInterval && chartInterval.length) {
      chartInterval.on("change", U.debounce(()=>{ saveIv(); startChartTimer(); updateFabCountdown(); updateFabRing(); U.showSnack(`Интервал: ${getChartInterval()} с`); }, 300));
    }
  }

  // Функция для очистки ресурсов
  function cleanup(){
    try {
      if(chartTimer){ 
        clearInterval(chartTimer); 
        chartTimer=null; 
      }
      if(fabRAF){ 
        cancelAnimationFrame(fabRAF); 
        fabRAF=null; 
      }
      // Очищаем переменные оптимизации
      _currentFile = null;
      _lastTs = null;
      
      // Очищаем график если он существует
      const gd = document.getElementById('chart');
      if (gd && gd.data) {
        try {
          Plotly.purge('chart');
        } catch (e) {
          console.warn('Ошибка при очистке графика:', e);
        }
      }
    } catch (e) {
      console.warn('Ошибка при очистке ресурсов графика:', e);
    }
  }

  // Expose
  window.App.chart = {
    loadCsvList, drawChart, setupChartControls, setupAdvancedControls,
    startChartTimer, startFabCountdown, updateFabRing,
    applyAutoControlsFromStorage, getChartInterval, cleanup,
    // Экспортируем геттеры для доступа к переменным из других модулей
    get _currentFile() { return _currentFile; },
    get _lastTs() { return _lastTs; },
    // Функция для проверки состояния кнопок быстрого хвоста
    checkTailSegments: function() {
      const tailSegments = $("#tailSegments");
      const tailRows = $("#tailRows");
      console.log("Проверка кнопок быстрого хвоста:");
      console.log("tailSegments:", tailSegments.length ? "найден" : "не найден");
      console.log("tailRows:", tailRows.length ? "найден" : "не найден");
      if (tailSegments.length) {
        const buttons = tailSegments.find(".btn");
        console.log("Кнопки найдены:", buttons.length);
        buttons.each(function(i, btn) {
          const $btn = $(btn);
          const tail = $btn.data("tail");
          const isActive = $btn.hasClass("active");
          console.log(`Кнопка ${i+1}: tail=${tail}, active=${isActive}`);
        });
      }
    }
  };
  } // закрываем initChart
})();
