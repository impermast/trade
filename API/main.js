// tooltips
document.addEventListener('DOMContentLoaded', () => {
  const tList=[].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"],[title][data-bs-toggle2]'));
  tList.forEach(el=> new bootstrap.Tooltip(el));
});

// ==== Тема ====
const themeKey="ui-theme";
function applyTheme(t){ document.documentElement.setAttribute("data-theme", t); $("#themeToggle").prop("checked", t==="dark"); }
function initTheme(){ const saved=localStorage.getItem(themeKey)||"dark"; applyTheme(saved);
  $("#themeToggle").on("change",()=>{const next=$("#themeToggle").is(":checked")?"dark":"light"; applyTheme(next); localStorage.setItem(themeKey,next); drawChart(false);});}

// ==== Утилы ====
const debounce=(fn,ms=250)=>{let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),ms)}};
function fmtNumber(x,d=2){ if(x==null||isNaN(x)) return "—"; return Number(x).toLocaleString("ru-RU",{maximumFractionDigits:d}); }
function cssVar(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function escapeHtml(s){ return (s??"").toString()
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }

// ==== Форматирование "последнего обновления" ====
const RU_MONTHS = ["янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"];
const pad2 = n => String(n).padStart(2,"0");

function humanizeUpdated(iso){
  if(!iso) return "—";
  const dt = new Date(iso);
  if (isNaN(+dt)) return "—";

  const now = new Date();
  const diffSec = Math.max(0, Math.floor((now - dt)/1000));

  // относительное
  let rel;
  if (diffSec < 30) rel = "только что";
  else if (diffSec < 60) rel = `${diffSec} сек назад`;
  else if (diffSec < 3600) rel = `${Math.floor(diffSec/60)} мин назад`;
  else if (diffSec < 86400) rel = `${Math.floor(diffSec/3600)} ч назад`;
  else rel = `${Math.floor(diffSec/86400)} дн назад`;

  // «сегодня/вчера» или дата
  const isSameDay = (a,b)=> a.getFullYear()===b.getFullYear() && a.getMonth()===b.getMonth() && a.getDate()===b.getDate();
  const yest = new Date(now.getFullYear(), now.getMonth(), now.getDate()-1);

  const timeStr = `${pad2(dt.getHours())}:${pad2(dt.getMinutes())}:${pad2(dt.getSeconds())}`;
  let main;
  if (isSameDay(dt, now))       main = `сегодня, ${timeStr}`;
  else if (isSameDay(dt, yest)) main = `вчера, ${timeStr}`;
  else                          main = `${dt.getDate()} ${RU_MONTHS[dt.getMonth()]} ${dt.getFullYear()}, ${timeStr}`;

  return `${main} · ${rel}`;
}

let updatedTicker = null;
function startUpdatedTicker(){
  if (updatedTicker) { clearInterval(updatedTicker); updatedTicker=null; }
  updatedTicker = setInterval(()=>{
    const iso = $("#kpi-updated").data("iso") || null;
    $("#kpi-updated").text(humanizeUpdated(iso));
  }, 30000); // раз в 30 сек обновляем «N мин назад»
}

// Top progress & snack
let topProgTimer=null;
function topProgressStart(){ const el=document.getElementById("topProgress"); el.style.width="0"; el.style.display="block"; requestAnimationFrame(()=>{ el.style.width="65%"; }); }
function topProgressDone(){ const el=document.getElementById("topProgress"); el.style.width="100%"; clearTimeout(topProgTimer); topProgTimer=setTimeout(()=>{ el.style.display="none"; el.style.width="0"; }, 250); }
function showSnack(msg, timeout=2200){ $("#snackbarMsg").text(msg); $("#snackbar").fadeIn(120); setTimeout(()=>$("#snackbar").fadeOut(180), timeout); }
async function withProgress(promise){ try{ topProgressStart(); return await promise; } finally{ topProgressDone(); } }

// ==== Статус‑пилюля ====
async function pingHealth(){
  try{
    const r = await fetch("/api/health",{cache:"no-store"});
    const ok = r.ok;
    $("#statusDot").toggleClass("status-ok", ok).toggleClass("status-warn", !ok);
    $("#statusText").text(ok ? "online" : "offline");
  }catch{
    $("#statusDot").removeClass("status-ok").addClass("status-warn");
    $("#statusText").text("offline");
  }
}
setInterval(pingHealth, 5000);

// ==== Tabs ink ====
function updateTabsInk(){
  const nav = document.getElementById('viewTabs');
  const ink = document.getElementById('tabsInk');
  if(!nav || !ink) return;
  const active = nav.querySelector('.nav-link.active');
  if(!active){ ink.style.width='0'; return; }

  const navRect = nav.getBoundingClientRect();
  const rect = active.getBoundingClientRect();

  const scrollX = nav.scrollLeft || 0;
  const pad = 12;
  const left = Math.max(0, rect.left - navRect.left + scrollX + pad);
  const width = Math.max(24, rect.width - pad*2);

  ink.style.transform = `translateX(${left}px)`;
  ink.style.width = width + 'px';
}

// ==== Chips binding ====
function bindChip(id, checkboxSel){
  const chip=$(id), cb=$(checkboxSel);
  chip.on("pointerdown", e=>{ chip[0].style.setProperty('--x', e.offsetX+'px'); chip[0].style.setProperty('--y', e.offsetY+'px'); });
  function sync(){ chip.toggleClass("selected", cb.is(":checked")); }
  chip.on("click", ()=>{ cb.prop("checked", !cb.is(":checked")); sync(); drawChart(false); });
  sync();
}
const hiddenControls = $('<div style="display:none"></div>').appendTo(document.body);
hiddenControls.append('<input type="checkbox" id="sma20">');
hiddenControls.append('<input type="checkbox" id="sma50">');
hiddenControls.append('<input type="checkbox" id="signals_rsi" checked>');
hiddenControls.append('<input type="checkbox" id="signals_xgb" checked>');
hiddenControls.append('<input type="checkbox" id="logScale">');

// ==== Индикаторы (клиент) ====
function rsi(prices, period=14){
  const n=prices.length, out=Array(n).fill(null);
  if(n<period+1) return out;
  let avgGain=0, avgLoss=0;
  for(let i=1;i<=period;i++){ const ch=prices[i]-prices[i-1]; avgGain+=Math.max(ch,0); avgLoss+=Math.max(-ch,0); }
  avgGain/=period; avgLoss/=period; out[period]=avgLoss===0?100:100-100/(1+(avgGain/avgLoss));
  for(let i=period+1;i<n;i++){ const ch=prices[i]-prices[i-1], g=Math.max(ch,0), l=Math.max(-ch,0);
    avgGain=(avgGain*(period-1)+g)/period; avgLoss=(avgLoss*(period-1)+l)/period; out[i]=avgLoss===0?100:100-100/(1+(avgGain/avgLoss)); }
  return out;
}
function sma(values, period){
  const res=Array(values.length).fill(null); if(period<=1) return values.slice();
  let sum=0; for(let i=0;i<values.length;i++){ const v=+values[i]; if(!isNaN(v)) sum+=v;
    if(i>=period){ const out=+values[i-period]; if(!isNaN(out)) sum-=out; }
    if(i>=period-1) res[i]=sum/period; } return res;
}

// ==== State / KPI / Positions ====
function renderPositions(positions){
  const tb=$("#posTbody"); tb.empty();
  if(!positions || !positions.length){ tb.append(`<tr><td colspan="5" class="text-muted">Открытых позиций нет</td></tr>`); return; }
  positions.forEach(p=>{
    const sym=(p.symbol||p.ticker||"—"), qty=(p.qty||p.size||p.amount||0);
    const entry=(+p.entry_price||+p.entry||+p.avg_entry||0), price=(+p.price||+p.mark_price||+p.last||0);
    const pnl=(price && entry)?(price-entry)*qty:(p.unrealized_pnl ?? 0);
    tb.append(`<tr><td>${sym}</td><td class="num">${fmtNumber(qty,4)}</td><td class="num">${fmtNumber(entry,2)}</td><td class="num">${fmtNumber(price,2)}</td><td class="num ${pnl>=0?'text-success':'text-danger'}">${fmtNumber(pnl,2)}</td></tr>`);
  });
}

async function loadState(){
  try{
    const r=await withProgress(fetch("/api/state")); const s=await r.json();
    const total=s?.balance?.total, cur=s?.balance?.currency||"—";
    $("#kpi-balance").text(total?fmtNumber(total,2):"—"); $("#kpi-balance-cur").text(cur);
    $("#kpi-positions").text(Array.isArray(s?.positions)?s.positions.length:"—");
    const isoUpd = s?.updated || null;
    $("#kpi-updated")
      .data("iso", isoUpd)
      .text(humanizeUpdated(isoUpd))
      .attr("title", isoUpd ? new Date(isoUpd).toISOString() : "—"); // точное ISO в тултипе
    startUpdatedTicker();
    $("#state-balance").text(total?`${fmtNumber(total,2)} ${cur}`:"—");
    renderPositions(s?.positions||[]);
  }catch{}
}

// ==== CSV list ====
async function loadCsvList(){
  const sel = $("#csvFile");
  sel.empty();
  try{
    const r = await withProgress(fetch("/csv_list"));
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
  // ВАЖНО: не триггерим change здесь, чтобы не перебивать анимацию
}

// ==== Chart ====
function themeVars(){ return { paper_bgcolor:cssVar("--bg"), plot_bgcolor:cssVar("--surface"), font_color:cssVar("--on-surface"), grid:cssVar("--grid") } }
function showRsiControls(){ $("#rsiControls").toggle($("#lowerPanel").val()==="rsi"); }

async function loadCandles(){
  const file=$("#csvFile").val(); const tail=Math.max(50,+$("#tailRows").val()||500);
  const r=await withProgress(fetch(`/api/candles?file=${encodeURIComponent(file)}&tail=${tail}`));
  if(!r.ok) throw new Error("Ошибка загрузки свечей"); return await r.json();
}

let _lastTs = null;
let _currentFile = null;
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
        <defs>
          <linearGradient id="gradEmpty" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%"  stop-color="${cssVar('--primary')}"/>
            <stop offset="100%" stop-color="${cssVar('--secondary')}"/>
          </linearGradient>
        </defs>
      <circle cx="60" cy="60" r="44" fill="url(#gradEmpty)">
        <animate attributeName="r" values="40;44;40" dur="2.8s" repeatCount="indefinite"/>
      </circle>
      <rect x="30" y="40" width="60" height="8" rx="4" fill="rgba(255,255,255,.25)"/>
      <rect x="40" y="54" width="40" height="8" rx="4" fill="rgba(255,255,255,.18)"/>
      </svg>
      <div class="title">${title}</div>
      <div class="sub">${sub}</div>
    </div>`;
}

async function drawChart(animate){
  $("#chartLoader").show();
  try{
    const rows = await loadCandles();
    $("#chartLoader").hide();

    if(!rows || !rows.length){
      Plotly.purge("chart");
      renderEmpty("chart","Нет данных для отображения","Проверьте CSV и параметры");
      return;
    }

    const fileNow = $("#csvFile").val() || "";
    const tsArr = rows.map(r=>r.ts);
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
        const addO = rows.slice(idx).map(r=>r.open);
        const addH = rows.slice(idx).map(r=>r.high);
        const addL = rows.slice(idx).map(r=>r.low);
        const addC = rows.slice(idx).map(r=>r.close);

        const tailMax = Math.max(50, +$("#tailRows").val()||500);

        Plotly.extendTraces(gdInc,
          { x:[addX], open:[addO], high:[addH], low:[addL], close:[addC] },
          [0], tailMax
        );

        _lastTs = tsArr[tsArr.length-1];
        keepRightEdge();
        $("#kpi-file").text($("#csvFile").val()||"—");
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
    const cPrimary   = cssVar("--primary");
    const cSecondary = cssVar("--secondary");
    const cTertiary  = "#9C27B0";
    const cError     = cssVar("--error");

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

    // --- Candles ---
    traces.push({
      type:"candlestick", x:ts, open, high, low, close, name:"OHLC", yaxis:"y",
      increasing:{line:{color:cSecondary, width:1}}, decreasing:{line:{color:cError, width:1}}
    });

    if($("#sma20").is(":checked"))
      traces.push({type:"scatter",mode:"lines",x:ts,y:sma(close,20),line:{width:1.8,color:cPrimary},name:"SMA 20",yaxis:"y"});
    if($("#sma50").is(":checked"))
      traces.push({type:"scatter",mode:"lines",x:ts,y:sma(close,50),line:{width:1.8,color:cTertiary},name:"SMA 50",yaxis:"y"});

    if (lowerIsVolume){
      traces.push({type:"bar", x:ts, y:vol, name:"Объём", opacity:.35, yaxis:"y2"});
    } else {
      const p=Math.max(2,+$("#rsiPeriod").val()||14), rv=rsi(close,p);
      traces.push({type:"scatter",mode:"lines",x:ts,y:rv,name:`RSI ${p}`,yaxis:"y2", line:{width:1.4}});
      traces.push({type:"scatter",mode:"lines",x:[ts[0],ts.at(-1)],y:[70,70],line:{dash:"dot",width:1},showlegend:false,yaxis:"y2"});
      traces.push({type:"scatter",mode:"lines",x:[ts[0],ts.at(-1)],y:[30,30],line:{dash:"dot",width:1},showlegend:false,yaxis:"y2"});
    }

    // ==== Маркеры сигналов ====
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

    const {paper_bgcolor,plot_bgcolor,font_color,grid}=themeVars();
    const layout={
      dragmode:"zoom",
      showlegend:true,
      legend:{ orientation:"h", y:1.12, x:1, xanchor:"right", bgcolor:"rgba(0,0,0,0)", borderwidth:0, font:{size:11} },
      margin:{t:20,r:10,b:40,l:50}, paper_bgcolor, plot_bgcolor, font:{color:font_color},
      xaxis:{ gridcolor:grid, gridwidth:0.4, ticklen:4, ticks:"outside", nticks: 8, anchor:"y", domain:[0,1], autorange:true, range:[ts[0], ts.at(-1)] },
      yaxis:{ title:"Цена", type:(isLog?"log":"linear"), gridcolor:grid, gridwidth:0.4, ticklen:4, ticks:"outside", domain:[0.35,1], autorange:false, range:yPriceRange },
      xaxis2:{gridcolor:grid, gridwidth:0.4, anchor:"y2", domain:[0,1], matches:"x", nticks:6, ticklen:3 },
      yaxis2:{ title: ($("#lowerPanel").val()==="volume" ? "Объём" : "RSI"), gridcolor:grid, gridwidth:0.4, domain:[0,0.28], autorange:false, range:y2Range, ticklen:3, ticks:"outside" }
    };

    const gd = document.getElementById("chart");
    await Plotly.react(gd, traces, layout, { responsive:true, displaylogo:false, displayModeBar:false });

    // плавная поэтапная отрисовка при ручном действии
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

          if (p < 1){
            requestAnimationFrame(step);
          } else {
            Plotly.restyle(gd, { x:[ts], open:[open], high:[high], low:[low], close:[close] }, [0]);
          }
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

// ==== Автообновление графика + Кольцо ====
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

  if (!auto){ ring.style.strokeDashoffset = C.toFixed(1); return; }

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
  if(!$("#autoRefreshChart").is(":checked")){ updateFabRing(); return; }
  const iv = getChartInterval()*1000;
  startFabCountdown();
  chartTimer = setInterval(()=>{
    if(document.visibilityState==="visible" && $("#chart-pane").hasClass("active")){
      drawChart(false); startFabCountdown();
    }
  }, iv);
}

function setupChartAutoControls(){
  applyAutoControlsFromStorage();

  $("#autoRefreshChart").on("change", ()=>{ localStorage.setItem(CHART_AUTO_KEY, $("#autoRefreshChart").is(":checked") ? "1" : "0"); startChartTimer(); });
  $("#chartInterval").on("change", ()=>{ const iv = getChartInterval(); $("#chartInterval").val(iv); localStorage.setItem(CHART_INTERVAL_KEY, iv.toString()); startChartTimer(); startFabCountdown(); });

  document.getElementById("chart-tab").addEventListener("shown.bs.tab", ()=>{ startChartTimer(); drawChart(false); });
  document.addEventListener("visibilitychange", ()=>{ if(document.visibilityState==="visible"){ startChartTimer(); } });
  document.addEventListener("visibilitychange", ()=>{ if(document.visibilityState==="visible"){ const iso=$("#kpi-updated").data("iso"); $("#kpi-updated").text(humanizeUpdated(iso)); }});
  startChartTimer(); startFabCountdown();
}

// ==== Controls ====
function setupChartControls(){
  $("#reloadChart").on("click", ()=>{ drawChart(false); startFabCountdown(); showSnack("График перестроен"); const btn=document.getElementById('reloadChart'); btn.classList.remove('pulse'); void btn.offsetWidth; btn.classList.add('pulse'); });
  $("#resetZoom").on("click", ()=>{ Plotly.relayout('chart', {'xaxis.autorange':true,'yaxis.autorange':true,'yaxis2.autorange':true}); showSnack("Масштаб сброшен"); });

  $("#csvFile").on("change", ()=>{ localStorage.setItem("csv-file", $("#csvFile").val()||""); drawChart(true); });
  $("#tailRows").on("change", ()=> drawChart(true));
  $("#lowerPanel").on("change", ()=>{ showRsiControls(); drawChart(false); });
  $("#rsiPeriod").on("change", ()=> drawChart(false));

  bindChip("#chipSMA20", "#sma20");
  bindChip("#chipSMA50", "#sma50");
  bindChip("#chipSigRSI", "#signals_rsi");
  bindChip("#chipSigXGB", "#signals_xgb");

  $("#tailSegments .btn").on("click", function(){
    $("#tailSegments .btn").removeClass("active");
    $(this).addClass("active");
    const val=+$(this).data("tail"); $("#tailRows").val(val);
    drawChart(true);
  });
  showRsiControls();
}

// ==== Доп. параметры ====
function setupAdvancedControls(){
  $("#logScaleSwitch").prop("checked", $("#logScale").is(":checked"));
  $("#logScaleSwitch").on("change", ()=>{ $("#logScale").prop("checked", $("#logScaleSwitch").is(":checked")); drawChart(false); });
}

// ==== Logs by file ====
let logsTimer=null;
async function loadLogFiles(){ const sel=$("#logFile"); sel.empty(); try{ const r=await withProgress(fetch("/logs")); const files=await r.json(); files.forEach(f=> sel.append(new Option(f,f))); }catch{} }
function colorizeLogLine(line){
  const up = line.toUpperCase();
  let cls="log-info";
  if (up.includes(" ERROR")) cls="log-error";
  else if (up.includes("[ERROR]")) cls="log-error";
  else if (up.includes(" WARN") || up.includes("[WARN") || up.includes(" WARNING")) cls="log-warn";
  else if (up.includes(" DEBUG") || up.includes("[DEBUG")) cls="log-debug";
  return `<div class="${cls}">${escapeHtml(line)}</div>`;
}
async function loadLogTail(){
  $("#logLoader").show();
  try{
    const file=$("#logFile").val(); const n=Math.max(100, +$("#logTail").val()||500);
    if(!file){ $("#logBox").html(`<div class="empty"><div class="title">Нет файла</div><div class="sub">Выберите лог слева</div></div>`); return; }
    const r=await withProgress(fetch(`/api/log_tail?filename=${encodeURIComponent(file)}&n=${n}`));
    if(!r.ok) throw new Error("Ошибка загрузки логов");
    const data=await r.json();
    const lines=(data?.lines||[]).map(colorizeLogLine).join("") || "";
    $("#logBox").html(lines || "Лог пуст");
    const el=document.getElementById("logBox"); el.scrollTop=el.scrollHeight;
  }catch{
    $("#logBox").html(`<div class="empty"><div class="title">Ошибка чтения</div><div class="sub">Проверьте путь к логам</div></div>`);
  }
  finally{ $("#logLoader").hide(); }
}
function setupLogsControls(){
  $("#reloadLogs").on("click", ()=>{ loadLogTail(); showSnack("Лог обновлён"); });
  $("#logFile, #logTail").on("change", loadLogTail);
  $("#logsInterval, #autoRefreshLogs").on("change", ()=>{ if(logsTimer){ clearInterval(logsTimer); logsTimer=null; } if($("#autoRefreshLogs").is(":checked")){ const iv=Math.max(5, +$("#logsInterval").val()||15)*1000; logsTimer=setInterval(loadLogTail, iv); } });
}

// ==== Logs all ====
let logsAllTimer=null, logsAllLevel="ALL";
function setLevelButtons(lv){ $(".btn-filter").removeClass("active"); $(`.btn-filter[data-level='${lv}']`).addClass("active"); }
function colorizeAllEntry(ts, level, src, msg){
  const lv = (level||"").toUpperCase();
  const cls = lv==="ERROR"?"log-error": lv==="WARN"?"log-warn": lv==="DEBUG"?"log-debug":"log-info";
  const tsHtml = ts ? `<span class="log-ts">${escapeHtml(ts)}</span>` : "";
  const srcHtml = src ? ` <span class="log-src">[${escapeHtml(src)}]</span>` : "";
  const lvHtml = lv ? ` <span class="${cls}">[${lv}]</span>` : "";
  return `<div>${tsHtml}${srcHtml}${lvHtml} ${escapeHtml(msg)}</div>`;
}
async function loadLogsAll(){
  $("#logsAllLoader").show();
  try{
    const n=Math.max(100, +$("#logsAllN").val()||1000), q=($("#logsAllQuery").val()||"").trim();
    const r=await withProgress(fetch(`/api/logs_all?n=${n}&level=${encodeURIComponent(logsAllLevel)}&q=${encodeURIComponent(q)}`));
    const arr=await r.json();
    const lines=arr.map(e=>colorizeAllEntry(e.ts??"", e.level??"", e.src??"", e.msg??"")).join("");
    $("#logsAllBox").html(lines || "Логи пусты");
    const el=document.getElementById("logsAllBox"); el.scrollTop=el.scrollHeight;
  }catch{
    $("#logsAllBox").html(`<div class="empty"><div class="title">Ошибка</div><div class="sub">Не удалось загрузить логи</div></div>`);
  }
  finally{ $("#logsAllLoader").hide(); }
}
function setupLogsAllControls(){
  $(".btn-filter").on("click", function(){ logsAllLevel=$(this).data("level"); setLevelButtons(logsAllLevel); loadLogsAll(); });
  $("#reloadLogsAll").on("click", ()=>{ loadLogsAll(); showSnack("Все логи обновлены"); });
  $("#logsAllQuery, #logsAllN").on("keyup/change", debounce(loadLogsAll, 300));
  $("#logsAllInterval, #autoRefreshLogsAll").on("change", ()=>{ if(logsAllTimer){ clearInterval(logsAllTimer); logsAllTimer=null; } if($("#autoRefreshLogsAll").is(":checked")){ const iv=Math.max(5, +$("#logsAllInterval").val()||15)*1000; logsAllTimer=setInterval(loadLogsAll, iv); } });
}

// ==== CSV preview ====
async function loadCsvPreview(){
  $("#csvLoader").show();
  try{
    const file = $("#csvFile").val();
    const tail = Math.max(50, +$("#csvViewTail").val() || 300);
    const r = await withProgress(fetch(`/api/candles?file=${encodeURIComponent(file)}&tail=${tail}`));
    if (!r.ok) throw new Error("Ошибка загрузки CSV");
    const rows = await r.json();
    renderCsvTable(rows);
  } catch(e){
    console.error(e);
    $("#csvThead").html("");
    $("#csvTbody").html(`<tr><td class="text-danger">Не удалось загрузить CSV</td></tr>`);
  } finally{
    $("#csvLoader").hide();
  }
}
function renderCsvTable(rows){
  const thead = $("#csvThead");
  const tbody = $("#csvTbody");
  thead.empty(); tbody.empty();

  if (!Array.isArray(rows) || rows.length === 0){
    tbody.html(`<tr><td class="text-muted">Нет данных</td></tr>`);
    return;
  }

  const cols = Object.keys(rows[0]);
  thead.append(`<tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>`);

  const frag = document.createDocumentFragment();
  rows.forEach(r => {
    const tr = document.createElement("tr");
    const hasRsi = Number(r["orders_rsi"] ?? 0) !== 0;
    const hasXgb = Number(r["orders_xgb"] ?? 0) !== 0 || Number(r["orders"] ?? 0) !== 0;
    if (hasRsi) tr.classList.add("has-rsi");
    if (hasXgb) tr.classList.add("has-xgb");
    tr.innerHTML = cols.map(c => `<td class="${/^(open|high|low|close|volume|orders|orders_rsi|orders_xgb)$/i.test(c)?'num':''}">${r[c] ?? ""}</td>`).join("");
    frag.appendChild(tr);
  });
  tbody[0].innerHTML = "";
  tbody[0].appendChild(frag);
}
function downloadCsvFromPreview(){
  const rows = [];
  const ths = Array.from(document.querySelectorAll("#csvThead th")).map(th => th.textContent || "");
  if (!ths.length){ showSnack("Нет данных для экспорта"); return; }
  rows.push(ths);
  $("#csvTbody tr").each(function(){ const tds = $(this).find("td"); if (!tds.length) return; rows.push(tds.map((_,td)=>$(td).text()).get()); });
  const csv = rows.map(r => r.map(x => `"${(x??"").toString().replace(/"/g,'""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], {type:"text/csv;charset=utf-8;"}); const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = ($("#csvFile").val() || "data") + ".preview.csv"; a.click(); URL.revokeObjectURL(url);
}
function setupCsvPreviewControls(){
  $("#csvReload").on("click", ()=>{ loadCsvPreview(); showSnack("CSV обновлен"); });
  $("#csvDownload").on("click", downloadCsvFromPreview);
  $("#csvViewTail").on("change", loadCsvPreview);
  $("#csvFile").on("change", loadCsvPreview);
  document.getElementById("csv-tab").addEventListener("shown.bs.tab", loadCsvPreview);
}

// ==== State auto-refresh ====
let stateTimer=null;
const STATE_INTERVAL_KEY="state-interval-seconds";
function startStateTimer(){
  const seconds=Math.max(5, +(localStorage.getItem(STATE_INTERVAL_KEY)||15));
  if(stateTimer) clearInterval(stateTimer);
  stateTimer=setInterval(()=>{ if(document.visibilityState==="visible") loadState(); }, seconds*1000);
}
document.addEventListener("visibilitychange", ()=>{ if(document.visibilityState==="visible") loadState(); });

// ==== Positions actions ====
function exportPositionsCsv(){
  const rows=[["symbol","qty","entry","price","pnl"]];
  $("#posTbody tr").each(function(){
    const tds=$(this).find("td"); if(tds.length!==5) return;
    rows.push(tds.map((_,td)=>($(td).text()||"").trim()).get());
  });
  const csv = rows.map(r => r.map(x => `"${(x??"").replace(/"/g,'""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], {type:"text/csv;charset=utf-8;"}); const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href=url; a.download="positions.csv"; a.click(); URL.revokeObjectURL(url);
}

// ==== Refresh all ====
function setupGlobalRefresh(){
  $("#refreshAll").on("click", async ()=>{ await Promise.all([loadState(), drawChart(false), loadLogTail(), loadLogsAll(), loadCsvPreview()]); startFabCountdown(); showSnack("Данные обновлены"); });
  $("#posRefresh").on("click", ()=>{ loadState(); showSnack("Позиции обновлены"); });
  $("#posExport").on("click", exportPositionsCsv);
}

// Ресайз Plotly
window.addEventListener('resize', debounce(()=>{ const gd = document.getElementById('chart'); if (gd && gd.data) Plotly.Plots.resize(gd); }, 120));

// Вариативные ширины скелетонов
function randomizeSkeletons(){
  document.querySelectorAll('.skeleton').forEach(el=>{ const w = 70 + Math.round(Math.random()*25); el.style.width = w + '%'; });
}

/* ======= UI ENHANCERS: NiceSelect + Number steppers ======= */
function enhanceSelect(select){
  if(select.dataset.enhanced === "1") return;
  select.dataset.enhanced = "1";

  const wrap = document.createElement('div');
  wrap.className = 'nselect';
  const parent = select.parentElement;
  parent.insertBefore(wrap, select);
  wrap.appendChild(select);

  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'nselect-toggle';
  btn.innerHTML = `<span class="nselect-label"></span><span class="nselect-caret" aria-hidden="true"></span>`;
  wrap.appendChild(btn);

  const menu = document.createElement('div');
  menu.className = 'nselect-menu';
  wrap.appendChild(menu);

  function buildMenu(){
    menu.innerHTML = '';
    Array.from(select.options).forEach(opt=>{
      const item = document.createElement('div');
      item.className = 'nselect-option' + (opt.selected?' is-selected':'');
      item.dataset.value = opt.value;
      item.textContent = opt.textContent;
      item.addEventListener('click', ()=>{
        select.value = opt.value;
        select.dispatchEvent(new Event('change', {bubbles:true}));
        closeMenu();
        updateLabel();
        syncSelected();
      });
      menu.appendChild(item);
    });
  }
  function syncSelected(){
    const val = select.value;
    menu.querySelectorAll('.nselect-option').forEach(el=>{
      el.classList.toggle('is-selected', el.dataset.value === val);
    });
  }
  function updateLabel(){
    const sel = select.options[select.selectedIndex];
    wrap.querySelector('.nselect-label').textContent = sel ? sel.textContent : '';
  }
  function openMenu(){ wrap.classList.add('is-open'); positionMenu(); document.addEventListener('click', onDocClick, {once:true}); }
  function closeMenu(){ wrap.classList.remove('is-open'); }
  function onDocClick(e){ if(!wrap.contains(e.target)) closeMenu(); }

  function positionMenu(){
    const rect = wrap.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const desired = 280;
    menu.style.top = '';
    menu.style.bottom = '';
    if (spaceBelow < desired){
      menu.style.bottom = `calc(100% + 6px)`;
    } else {
      menu.style.top = `calc(100% + 6px)`;
    }
  }

  btn.addEventListener('click', ()=> wrap.classList.contains('is-open') ? closeMenu() : openMenu());
  select.addEventListener('change', ()=>{ updateLabel(); syncSelected(); });
  const mo = new MutationObserver(()=>{ buildMenu(); updateLabel(); syncSelected(); });
  mo.observe(select, {childList:true});

  buildMenu(); updateLabel(); syncSelected();
}

function refreshNiceSelect(select){
  if(!select) return;
  if(!select.dataset.enhanced){ enhanceSelect(select); return; }
  // раньше здесь диспатчили change -> вызывалась drawChart(true) второй раз и ломала анимацию
  // теперь просто обновляем подпись/выбор
  const wrap = select.parentElement?.classList.contains('nselect') ? select.parentElement : null;
  if (wrap){
    const label = wrap.querySelector('.nselect-label');
    const sel = select.options[select.selectedIndex];
    if (label && sel) label.textContent = sel.textContent;
  }
}

function enhanceNumberInput(input){
  if(input.dataset.enhanced === "1") return;
  input.dataset.enhanced = "1";

  const wrap = document.createElement('div');
  wrap.className = 'num-input';
  input.parentElement.insertBefore(wrap, input);
  wrap.appendChild(input);

  const box = document.createElement('div');
  box.className = 'num-step';
  box.innerHTML = `<button type="button" class="up" aria-label="Увеличить"></button><button type="button" class="down" aria-label="Уменьшить"></button>`;
  wrap.appendChild(box);

  const step = ()=> Number(input.step || 1);
  const clamp = (v)=>{
    const min = input.min!=='' ? Number(input.min) : -Infinity;
    const max = input.max!=='' ? Number(input.max) :  Infinity;
    return Math.max(min, Math.min(max, v));
  };

  box.querySelector('.up').addEventListener('click', ()=>{ const v = clamp((Number(input.value)||0) + step()); input.value = v; input.dispatchEvent(new Event('change', {bubbles:true})); });
  box.querySelector('.down').addEventListener('click', ()=>{ const v = clamp((Number(input.value)||0) - step()); input.value = v; input.dispatchEvent(new Event('change', {bubbles:true})); });

  input.addEventListener('wheel', (e)=>{ if(document.activeElement!==input) return;
    e.preventDefault(); const dir = Math.sign(e.deltaY); const s = step(); const v = clamp((Number(input.value)||0) + (dir>0?-s:s)); input.value=v; input.dispatchEvent(new Event('change',{bubbles:true})); }, {passive:false});
}

// ===== Init enhancers for selects & numbers =====
function initEnhancers(){
  document.querySelectorAll('select.form-select').forEach(enhanceSelect);
  document.querySelectorAll('input[type=number].form-control').forEach(enhanceNumberInput);
}

/* ======= Init ======= */
$(async function(){
  initTheme();
  pingHealth();

  // tabs ink init & listeners
  updateTabsInk();
  window.addEventListener('resize', debounce(updateTabsInk, 100));
  document.getElementById("viewTabs").addEventListener("click", e=>{ if(e.target.closest('.nav-link')) setTimeout(updateTabsInk, 0); });
  document.querySelectorAll('#viewTabs .nav-link').forEach(btn=>{ btn.addEventListener('shown.bs.tab', updateTabsInk); });
  document.getElementById("viewTabs").addEventListener('scroll', debounce(updateTabsInk, 50));

  // Визуальные энхансеры
  initEnhancers();

  setupChartControls();
  setupChartAutoControls();
  setupAdvancedControls();
  setupLogsControls();
  setupLogsAllControls();
  setupCsvPreviewControls();
  setupGlobalRefresh();

  await Promise.all([loadCsvList(), loadLogFiles(), loadState()]);
  // refreshNiceSelect не вызываем, чтобы не триггерить лишний change

  await drawChart(true);    // один вызов с анимацией
  await loadLogTail();
  await loadLogsAll();

  startStateTimer();
  randomizeSkeletons();
});
