(function(){
  window.App = window.App || {};
  const U = window.App.util;
  const { debounce, escapeHtml } = U;

  // Logs by file
  let logsTimer=null;
  async function loadLogFiles(){ const sel=$("#logFile"); sel.empty(); try{ const r=await U.withProgress(fetch("/logs")); const files=await r.json(); files.forEach(f=> sel.append(new Option(f,f))); }catch{} }
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
      const r=await U.withProgress(fetch(`/api/log_tail?filename=${encodeURIComponent(file)}&n=${n}`));
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
    $("#reloadLogs").on("click", ()=>{ loadLogTail(); U.showSnack("Лог обновлён"); });
    $("#logFile, #logTail").on("change", loadLogTail);
    $("#logsInterval, #autoRefreshLogs").on("change", ()=>{ if(logsTimer){ clearInterval(logsTimer); logsTimer=null; } if($("#autoRefreshLogs").is(":checked")){ const iv=Math.max(5, +$("#logsInterval").val()||15)*1000; logsTimer=setInterval(loadLogTail, iv); } });
  }

  // Logs all
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
      const r=await U.withProgress(fetch(`/api/logs_all?n=${n}&level=${encodeURIComponent(logsAllLevel)}&q=${encodeURIComponent(q)}`));
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
    $("#reloadLogsAll").on("click", ()=>{ loadLogsAll(); U.showSnack("Все логи обновлены"); });
    $("#logsAllQuery, #logsAllN").on("keyup/change", debounce(loadLogsAll, 300));
    $("#logsAllInterval, #autoRefreshLogsAll").on("change", ()=>{ if(logsAllTimer){ clearInterval(logsAllTimer); logsAllTimer=null; } if($("#autoRefreshLogsAll").is(":checked")){ const iv=Math.max(5, +$("#logsAllInterval").val()||15)*1000; logsAllTimer=setInterval(loadLogsAll, iv); } });
  }

  window.App.logs = {
    loadLogFiles, loadLogTail, setupLogsControls,
    loadLogsAll, setupLogsAllControls
  };
})();
