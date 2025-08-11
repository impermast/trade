(function(){
  window.App = window.App || {};
  const { fmtNumber, humanizeUpdated } = window.App.util;

  let updatedTicker = null;
  function startUpdatedTicker(){
    if (updatedTicker) { clearInterval(updatedTicker); updatedTicker=null; }
    updatedTicker = setInterval(()=>{
      const iso = $("#kpi-updated").data("iso") || null;
      $("#kpi-updated").text(humanizeUpdated(iso));
    }, 30000);
  }

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
      const r=await App.util.withProgress(fetch("/api/state"));
      const s=await r.json();
      const total=s?.balance?.total, cur=s?.balance?.currency||"—";
      $("#kpi-balance").text(total?fmtNumber(total,2):"—"); $("#kpi-balance-cur").text(cur);
      $("#kpi-positions").text(Array.isArray(s?.positions)?s.positions.length:"—");
      const isoUpd = s?.updated || null;
      $("#kpi-updated").data("iso", isoUpd).text(humanizeUpdated(isoUpd)).attr("title", isoUpd ? new Date(isoUpd).toISOString() : "—");
      startUpdatedTicker();
      $("#state-balance").text(total?`${fmtNumber(total,2)} ${cur}`:"—");
      renderPositions(s?.positions||[]);
    }catch(e){
      console.warn('Ошибка при загрузке состояния:', e);
      // Показываем пользователю, что данные не загружены
      $("#kpi-balance").text("—");
      $("#kpi-balance-cur").text("—");
      $("#kpi-positions").text("—");
      $("#kpi-updated").text("—");
      $("#state-balance").text("—");
      renderPositions([]);
    }
  }

  // Positions export / refresh hooks
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

  // State auto-refresh
  let stateTimer=null;
  const STATE_INTERVAL_KEY="state-interval-seconds";
  function startStateTimer(){
    // Очищаем предыдущий таймер
    if(stateTimer) clearInterval(stateTimer);
    
    const seconds=Math.max(5, +(localStorage.getItem(STATE_INTERVAL_KEY)||15));
    stateTimer=setInterval(()=>{ 
      if(document.visibilityState==="visible") loadState(); 
    }, seconds*1000);
  }
  document.addEventListener("visibilitychange", ()=>{ if(document.visibilityState==="visible") loadState(); });

  // Функция для очистки ресурсов
  function cleanup(){
    try {
      if(stateTimer){ 
        clearInterval(stateTimer); 
        stateTimer=null; 
      }
      if(updatedTicker){ 
        clearInterval(updatedTicker); 
        updatedTicker=null; 
      }
    } catch (e) {
      console.warn('Ошибка при очистке ресурсов состояния:', e);
    }
  }

  window.App.state = { loadState, startStateTimer, exportPositionsCsv, cleanup };
})();
