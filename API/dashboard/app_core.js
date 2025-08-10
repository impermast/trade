// Core utils & globals
(function(){
  window.App = window.App || {};
  const util = {};

  // bootstrap tooltips init lives in ui.js (visual)
  // Debounce
  util.debounce = (fn,ms=250)=>{let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),ms)}};

  // Numbers/format
  util.fmtNumber = (x,d=2)=>{ if(x==null||isNaN(x)) return "—"; return Number(x).toLocaleString("ru-RU",{maximumFractionDigits:d}); };

  // CSS var
  util.cssVar = (name)=> getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  // HTML escape
  util.escapeHtml = (s)=> (s??"").toString()
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#39;");

  // Humanize updated
  const RU_MONTHS=["янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"];
  const pad2 = n => String(n).padStart(2,"0");
  util.humanizeUpdated = (iso)=>{
    if(!iso) return "—";
    const dt = new Date(iso); if(isNaN(+dt)) return "—";
    const now = new Date(); const diffSec = Math.max(0, Math.floor((now - dt)/1000));
    let rel;
    if (diffSec < 30) rel = "только что";
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
  };

  // Top progress & snack
  let topProgTimer=null;
  util.topProgressStart = function(){ const el=document.getElementById("topProgress"); if(!el) return; el.style.width="0"; el.style.display="block"; requestAnimationFrame(()=>{ el.style.width="65%"; }); };
  util.topProgressDone  = function(){ const el=document.getElementById("topProgress"); if(!el) return; el.style.width="100%"; clearTimeout(topProgTimer); topProgTimer=setTimeout(()=>{ el.style.display="none"; el.style.width="0"; }, 250); };
  util.showSnack = (msg, timeout=2200)=>{ $("#snackbarMsg").text(msg); $("#snackbar").fadeIn(120); setTimeout(()=>$("#snackbar").fadeOut(180), timeout); };
  util.withProgress = async (promise)=>{ try{ util.topProgressStart(); return await promise; } finally{ util.topProgressDone(); } };

  // Health ping
  util.pingHealth = async function(){
    try{
      const r = await fetch("/api/health",{cache:"no-store"});
      const ok = r.ok;
      $("#statusDot").toggleClass("status-ok", ok).toggleClass("status-warn", !ok);
      $("#statusText").text(ok ? "online" : "offline");
    }catch{
      $("#statusDot").removeClass("status-ok").addClass("status-warn");
      $("#statusText").text("offline");
    }
  };

  // Tabs ink
  util.updateTabsInk = function(){
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
    ink.style.transform = `translateX(${left}px)`; ink.style.width = width + 'px';
  };

  // Chips binding + hidden checkboxes state
  util.bindChip = function(id, checkboxSel){
    const chip=$(id), cb=$(checkboxSel);
    chip.on("pointerdown", e=>{ chip[0].style.setProperty('--x', e.offsetX+'px'); chip[0].style.setProperty('--y', e.offsetY+'px'); });
    function sync(){ chip.toggleClass("selected", cb.is(":checked")); }
    chip.on("click", ()=>{ cb.prop("checked", !cb.is(":checked")); sync(); if(window.App.chart) window.App.chart.drawChart(false); });
    sync();
  };
  const hiddenControls = $('<div style="display:none"></div>').appendTo(document.body);
  hiddenControls.append('<input type="checkbox" id="sma20">');
  hiddenControls.append('<input type="checkbox" id="sma50">');
  hiddenControls.append('<input type="checkbox" id="signals_rsi" checked>');
  hiddenControls.append('<input type="checkbox" id="signals_xgb" checked>');
  hiddenControls.append('<input type="checkbox" id="logScale">');

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

  window.App.util = util;
})();
