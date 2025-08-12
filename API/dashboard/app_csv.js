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

    // Фильтруем и переименовываем столбцы
    const cols = Object.keys(rows[0]).filter(col => {
      // Скрываем столбцы HIGH, LOW, OPEN
      return !['high', 'low', 'open'].includes(col.toLowerCase());
    });

    // Создаем заголовки с переименованием столбцов ORDERS
    const headerHtml = cols.map(col => {
      let displayName = col;
      let dataAttr = '';
      
      // Переименовываем столбцы ORDERS и добавляем атрибуты для стилизации
      if (col.toLowerCase() === 'orders_rsi') {
        displayName = 'ORDERS_RSI';
        dataAttr = ' data-orders-type="rsi"';
      } else if (col.toLowerCase() === 'orders_macd') {
        displayName = 'ORDERS_MACD';
        dataAttr = ' data-orders-type="macd"';
      } else if (col.toLowerCase() === 'orders_bollinger') {
        displayName = 'ORDERS_BOLL';
        dataAttr = ' data-orders-type="bollinger"';
      } else if (col.toLowerCase() === 'orders_stochastic') {
        displayName = 'ORDERS_STOCH';
        dataAttr = ' data-orders-type="stochastic"';
      } else if (col.toLowerCase() === 'orders_williams_r') {
        displayName = 'ORDERS_W%R';
        dataAttr = ' data-orders-type="williams_r"';
      } else if (col.toLowerCase() === 'orders_xgb') {
        displayName = 'ORDERS_XGB';
        dataAttr = ' data-orders-type="xgb"';
      }
      
      return `<th${dataAttr}>${displayName}</th>`;
    }).join("");
    
    thead.append(`<tr>${headerHtml}</tr>`);

    // Оптимизация: создаем HTML строку вместо множественных DOM операций
    const rowsHtml = rows.map(r => {
      const hasRsi = Number(r["orders_rsi"] ?? 0) !== 0;
      const hasXgb = Number(r["orders_xgb"] ?? 0) !== 0 || Number(r["orders"] ?? 0) !== 0;
      const hasMacd = Number(r["orders_macd"] ?? 0) !== 0;
      const hasBollinger = Number(r["orders_bollinger"] ?? 0) !== 0;
      const classes = [];
      if (hasRsi) classes.push("has-rsi");
      if (hasXgb) classes.push("has-xgb");
      if (hasMacd) classes.push("has-macd");
      if (hasBollinger) classes.push("has-bollinger");
      
      const classAttr = classes.length > 0 ? ` class="${classes.join(' ')}"` : '';
      const cells = cols.map(c => {
        const cellClass = /^(close|volume|orders|orders_rsi|orders_xgb|orders_macd|orders_bollinger|orders_stochastic|orders_williams_r)$/i.test(c) ? 'num' : '';
        const cellClassAttr = cellClass ? ` class="${cellClass}"` : '';
        
        let cellValue = r[c] ?? "";
        
        // Округляем значения в столбце CLOSE до 2 знаков после запятой
        if (c.toLowerCase() === 'close' && cellValue !== "") {
          const numValue = parseFloat(cellValue);
          if (!isNaN(numValue)) {
            cellValue = numValue.toFixed(2);
          }
        }
        
        return `<td${cellClassAttr}>${cellValue}</td>`;
      }).join("");
      
      return `<tr${classAttr}>${cells}</tr>`;
    }).join("");

    tbody.html(rowsHtml);
  }

  function downloadCsvFromPreview(){
    const rows = [];
    
    // Получаем заголовки из видимой таблицы (уже с переименованными столбцами)
    const ths = Array.from(document.querySelectorAll("#csvThead th")).map(th => th.textContent || "");
    if (!ths.length){ U.showSnack("Нет данных для экспорта"); return; }
    
    rows.push(ths);
    
    // Получаем данные из видимых строк
    $("#csvTbody tr").each(function(){ 
      const tds = $(this).find("td"); 
      if (!tds.length) return; 
      rows.push(tds.map((_,td)=>$(td).text()).get()); 
    });
    
    const csv = rows.map(r => r.map(x => `"${(x??"").toString().replace(/"/g,'""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], {type:"text/csv;charset=utf-8;"}); 
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); 
    a.href = url; 
    a.download = ($("#csvFile").val() || "data") + ".preview.csv"; 
    a.click(); 
    URL.revokeObjectURL(url);
  }

  function setupCsvPreviewControls(){
    $("#csvReload").on("click", ()=>{ loadCsvPreview(); U.showSnack("CSV обновлен"); });
    $("#csvDownload").on("click", downloadCsvFromPreview);
    $("#csvViewTail").on("change", U.debounce(loadCsvPreview, 300));
    $("#csvFile").on("change", loadCsvPreview);
    document.getElementById("csv-tab").addEventListener("shown.bs.tab", loadCsvPreview);
  }

  // Функция для очистки ресурсов
  function cleanup(){
    // В данном модуле нет таймеров или других ресурсов для очистки
  }

  window.App.csv = { loadCsvPreview, setupCsvPreviewControls, cleanup };
})();
