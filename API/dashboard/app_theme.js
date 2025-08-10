(function(){
  window.App = window.App || {};
  const theme = {};
  const KEY="ui-theme";

  theme.applyTheme = function(t){
    document.documentElement.setAttribute("data-theme", t);
    $("#themeToggle").prop("checked", t==="dark");
  };
  theme.initTheme = function(){
    const saved=localStorage.getItem(KEY)||"dark";
    theme.applyTheme(saved);
    $("#themeToggle").on("change",()=>{
      const next=$("#themeToggle").is(":checked")?"dark":"light";
      theme.applyTheme(next);
      localStorage.setItem(KEY,next);
      if(window.App.chart) window.App.chart.drawChart(false);
    });
  };
  theme.themeVars = function(){
    const css = window.App.util.cssVar;
    return {
      paper_bgcolor: css("--bg"),
      plot_bgcolor:  css("--surface"),
      font_color:    css("--on-surface"),
      grid:          css("--grid")
    };
  };

  window.App.theme = theme;
})();
