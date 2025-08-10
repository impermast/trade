(function(){
  window.App = window.App || {};
  const U = window.App.util;

  async function loadCsvPreview(){
    $("#csvLoader").show();
    try{
      const file = $("#csvFile").val();
      const tail = Math.max(50, +$("#csvViewTail").val() || 300);
      const r = await U.withProgress(fetch(`/api/candles?file=${encodeURIComponent(file)}&tail=${tail}`));
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
    if (!ths.length){ U.showSnack("Нет данных для экспорта"); return; }
    rows.push(ths);
    $("#csvTbody tr").each(function(){ const tds = $(this).find("td"); if (!tds.length) return; rows.push(tds.map((_,td)=>$(td).text()).get()); });
    const csv = rows.map(r => r.map(x => `"${(x??"").toString().replace(/"/g,'""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], {type:"text/csv;charset=utf-8;"}); const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = ($("#csvFile").val() || "data") + ".preview.csv"; a.click(); URL.revokeObjectURL(url);
  }

  function setupCsvPreviewControls(){
    $("#csvReload").on("click", ()=>{ loadCsvPreview(); U.showSnack("CSV обновлен"); });
    $("#csvDownload").on("click", downloadCsvFromPreview);
    $("#csvViewTail").on("change", loadCsvPreview);
    $("#csvFile").on("change", loadCsvPreview);
    document.getElementById("csv-tab").addEventListener("shown.bs.tab", loadCsvPreview);
  }

  window.App.csv = { loadCsvPreview, setupCsvPreviewControls };
})();
