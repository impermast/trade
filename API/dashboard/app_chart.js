(function(){
  window.App = window.App || {};
  const U = window.App.util;
  const T = window.App.theme;

  // CSV list (без верхней полоски: plain fetch)
  async function loadCsvList(){
    const sel = $("#csvFile"); sel.empty();
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
      $("#kpi-file").text(sel.val() || "—");
    } catch {
      sel.append(new Option("BTCUSDT_1m.csv","BTCUSDT_1m.csv"));
      $("#kpi-file").text(sel.val() || "—");
    }
  }

  // Chart helpers
  function showRsiControls(){ $("#rsiControls").toggle($("#lowerPanel").val()==="rsi"); }

  // Загрузка свечей без верхней полоски (оставляем только локальный спиннер #chartLoader)
  async function loadCandles(){
    const file=$("#csvFile").val(); const tail=Math.max(50,+$("#tailRows").val()||500);
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
    $("#chartLoader").show(); // локальный спиннер
    try{
      const rows = await loadCandles();
      $("#chartLoader").hide();

      if(!rows || !rows.length){
        Plotly.purge("chart");
        renderEmpty("chart","Нет данных для отображения","Проверьте CSV и параметры");
        return;
      }

      // Полный перестроение графика — чтобы обновлялись RSI/SMA/объёмы и маркеры сигналов.
      const fileNow = $("#csvFile").val() || "";

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
      $("#kpi-file").text($("#csvFile").val()||"—");
    } catch(e) {
      console.error(e);
      $("#chartLoader").hide();
      renderEmpty("chart","Ошибка загрузки","Проверьте CSV и колонки (time/open/high/low/close)");
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

    fabRAF = requestAnimationFrame(updateFabRing);
  }
  function startFabCountdown(){
    if (fabRAF) cancelAnimationFrame(fabRAF);
    nextRefreshAt = performance.now() + getChartInterval()*1000;
    fabRAF = requestAnimationFrame(updateFabRing);
  }
  function startChartTimer(){
    if(chartTimer){ clearInterval(chartTimer); chartTimer=null; }
    const auto = $("#autoRefreshChart").is(":checked");
    if(!auto){
      if (fabRAF) { cancelAnimationFrame(fabRAF); fabRAF=null; }
      updateFabRing();
      return;
    }
    const iv = getChartInterval()*1000;
    startFabCountdown();
    chartTimer = setInterval(()=>{
      if(document.visibilityState==="visible" && $("#chart-pane").hasClass("active")){
        drawChart(false); startFabCountdown();
      }
    }, iv);
  }

  // Controls
  function setupChartControls(){
    $("#reloadChart").on("click", ()=>{ drawChart(false); startFabCountdown(); U.showSnack("График перестроен"); const btn=document.getElementById('reloadChart'); btn.classList.remove('pulse'); void btn.offsetWidth; btn.classList.add('pulse'); });
    $("#resetZoom").on("click", ()=>{ Plotly.relayout('chart', {'xaxis.autorange':true,'yaxis.autorange':true,'yaxis2.autorange':true}); U.showSnack("Масштаб сброшен"); });

    $("#csvFile").on("change", ()=>{ localStorage.setItem("csv-file", $("#csvFile").val()||""); drawChart(true); });
    $("#tailRows").on("change", ()=> drawChart(true));
    $("#lowerPanel").on("change", ()=>{ showRsiControls(); drawChart(false); });
    $("#rsiPeriod").on("change", ()=> drawChart(false));

    U.bindChip("#chipSMA20", "#sma20");
    U.bindChip("#chipSMA50", "#sma50");
    U.bindChip("#chipSigRSI", "#signals_rsi");
    U.bindChip("#chipSigXGB", "#signals_xgb");

    $("#tailSegments .btn").on("click", function(){
      $("#tailSegments .btn").removeClass("active");
      $(this).addClass("active");
      const val=+$(this).data("tail"); $("#tailRows").val(val);
      drawChart(true);
    });
    showRsiControls();
  }

  // Advanced controls
  function setupAdvancedControls(){
    // лог масштаб визуально связан со скрытым чекбоксом
    $("#logScaleSwitch").prop("checked", $("#logScale").is(":checked"));
    $("#logScaleSwitch").on("change", ()=>{ $("#logScale").prop("checked", $("#logScaleSwitch").is(":checked")); drawChart(false); });

    // persist & timer controls for auto-refresh
    const saveAuto = ()=> localStorage.setItem(CHART_AUTO_KEY, $("#autoRefreshChart").is(":checked") ? "1" : "0");
    const saveIv   = ()=> localStorage.setItem(CHART_INTERVAL_KEY, String(getChartInterval()));

    $("#autoRefreshChart").on("change", ()=>{ saveAuto(); startChartTimer(); updateFabRing(); U.showSnack($("#autoRefreshChart").is(":checked")?"Автообновление включено":"Автообновление выключено"); });
    $("#chartInterval").on("change", ()=>{ saveIv(); startChartTimer(); updateFabRing(); U.showSnack(`Интервал: ${getChartInterval()} с`); });
  }

  // Expose
  window.App.chart = {
    loadCsvList, drawChart, setupChartControls, setupAdvancedControls,
    startChartTimer, startFabCountdown, updateFabRing,
    applyAutoControlsFromStorage, getChartInterval
  };
})();
