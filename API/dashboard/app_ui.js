// UI helpers: tooltips, enhancers, skeletons, resize Plotly, tabs ink listeners, tab animations
(function(){
  window.App = window.App || {};
  const { debounce } = window.App.util;

  // Проверка загрузки Bootstrap
  if (typeof bootstrap === 'undefined') {
    console.error('Bootstrap не загружен! UI компоненты не могут работать корректно.');
    return;
  }

  // Bootstrap tooltips
  function initTooltips() {
    try {
      const tList=[].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"],[title][data-bs-toggle2]'));
      tList.forEach(el=> {
        try {
          // Проверяем, не инициализирован ли уже tooltip
          if (!el._tooltip) {
            el._tooltip = new bootstrap.Tooltip(el);
          }
        } catch (e) {
          console.warn('Ошибка создания tooltip для элемента:', el, e);
        }
      });
    } catch (e) {
      console.warn('Ошибка инициализации tooltips:', e);
    }
  }

  // Инициализируем tooltips при готовности DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTooltips);
  } else {
    initTooltips();
  }

  // === NiceSelect / Number inputs (без изменений) ===
  function enhanceSelect(select){
    if(!select || select.dataset.enhanced === "1") return;
    select.dataset.enhanced = "1";

    const wrap = document.createElement('div');
    wrap.className = 'nselect';
    const parent = select.parentElement;
    if (!parent) return;
    
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
      const label = wrap.querySelector('.nselect-label');
      if (label) {
        label.textContent = sel ? sel.textContent : '';
      }
    }
    function openMenu(){ wrap.classList.add('is-open'); positionMenu(); document.addEventListener('click', onDocClick, {once:true}); }
    function closeMenu(){ wrap.classList.remove('is-open'); }
    function onDocClick(e){ if(!wrap.contains(e.target)) closeMenu(); }
    function positionMenu(){
      try {
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
      } catch (e) {
        console.warn('Ошибка позиционирования меню:', e);
      }
    }

    btn.addEventListener('click', ()=> wrap.classList.contains('is-open') ? closeMenu() : openMenu());
    select.addEventListener('change', ()=>{ updateLabel(); syncSelected(); });
    const mo = new MutationObserver(()=>{ buildMenu(); updateLabel(); syncSelected(); });
    mo.observe(select, {childList:true});
    // Сохраняем MutationObserver для последующей очистки
    if (window.App.ui && window.App.ui.addMutationObserver) {
      window.App.ui.addMutationObserver(mo);
    }

    buildMenu(); updateLabel(); syncSelected();
  }

  function refreshNiceSelect(select){
    if(!select) return;
    if(!select.dataset.enhanced){ enhanceSelect(select); return; }
    const wrap = select.parentElement?.classList.contains('nselect') ? select.parentElement : null;
    if (wrap){
      const label = wrap.querySelector('.nselect-label');
      const sel = select.options[select.selectedIndex];
      if (label && sel) label.textContent = sel.textContent;
    }
  }

  function enhanceNumberInput(input){
    if(!input || input.dataset.enhanced === "1") return;
    input.dataset.enhanced = "1";

    const wrap = document.createElement('div');
    wrap.className = 'num-input';
    const parent = input.parentElement;
    if (!parent) return;
    
    parent.insertBefore(wrap, input);
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

  function initEnhancers(){
    document.querySelectorAll('select.form-select').forEach(enhanceSelect);
    document.querySelectorAll('input[type=number].form-control').forEach(enhanceNumberInput);
  }

  // Random skeleton widths
  function randomizeSkeletons(){
    document.querySelectorAll('.skeleton').forEach(el=>{ const w = 70 + Math.round(Math.random()*25); el.style.width = w + '%'; });
  }

  // Plotly resize
  window.addEventListener('resize', debounce(()=>{ const gd = document.getElementById('chart'); if (gd && gd.data) Plotly.Plots.resize(gd); }, 120));

  // === Анимация переключения вкладок: fade + slide ===
  function initTabAnimations(){
    const nav = document.getElementById('viewTabs');
    if(!nav) return;

    const tabs = Array.from(nav.querySelectorAll('.nav-link'));
    let currentIndex = tabs.findIndex(t => t.classList.contains('active'));
    if (currentIndex < 0) currentIndex = 0;

    // Помечаем корень, чтобы включить CSS-анимации вкладок
    document.documentElement.classList.add('tabs-animated');

    tabs.forEach((btn, idx)=>{
      btn.addEventListener('show.bs.tab', (e)=>{
        const targetSel = btn.getAttribute('data-bs-target');
        const pane = document.querySelector(targetSel);
        if(!pane) return;

        // Направление: вправо, если идём к бóльшему индексу
        const dir = (idx > currentIndex) ? 1 : -1;
        // Установим величину сдвига через CSS-переменную
        pane.classList.add('tab-anim');
        pane.style.setProperty('--tab-slide', (12 * dir) + 'px');
      });

      btn.addEventListener('shown.bs.tab', (e)=>{
        currentIndex = idx;
        // Очистка инлайнов после завершения перехода
        const targetSel = btn.getAttribute('data-bs-target');
        const pane = document.querySelector(targetSel);
        if(!pane) return;
        // немного позже убираем var, чтобы не мешать следующий вход
        setTimeout(()=>{ pane.style.removeProperty('--tab-slide'); }, 260);
      });
    });
  }

  // Tabs ink recalculation moved here as well (unchanged)
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
    ink.style.transform = `translateX(${left}px)`; ink.style.width = width + 'px';
  }

  window.addEventListener('resize', debounce(updateTabsInk, 100));
  document.addEventListener('DOMContentLoaded', ()=> {
    const nav = document.getElementById("viewTabs");
    if (nav){
      nav.addEventListener("click", e=>{ if(e.target.closest('.nav-link')) setTimeout(updateTabsInk, 0); });
      nav.querySelectorAll('.nav-link').forEach(btn=>{ btn.addEventListener('shown.bs.tab', updateTabsInk); });
      nav.addEventListener('scroll', debounce(updateTabsInk, 50));
    }
  });

  // Массив для хранения MutationObserver
  const _mutationObservers = [];

  // Функция для очистки ресурсов
  function cleanup(){
    try {
      // Очищаем все MutationObserver
      if(_mutationObservers && _mutationObservers.length > 0) {
        _mutationObservers.forEach(mo => {
          try {
            mo.disconnect();
          } catch (e) {
            console.warn('Ошибка при отключении MutationObserver:', e);
          }
        });
        _mutationObservers.length = 0;
      }
      
      // Очищаем все tooltips
      const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"],[title][data-bs-toggle2]');
      tooltipElements.forEach(el => {
        try {
          if (el._tooltip && typeof el._tooltip.dispose === 'function') {
            el._tooltip.dispose();
            delete el._tooltip;
          }
        } catch (e) {
          console.warn('Ошибка при очистке tooltip:', e);
        }
      });
    } catch (e) {
      console.warn('Ошибка при очистке ресурсов UI:', e);
    }
  }

  // Функция для добавления MutationObserver в массив
  function addMutationObserver(mo) {
    if (mo && typeof mo.disconnect === 'function') {
      _mutationObservers.push(mo);
    }
  }

  window.App.ui = {
    enhanceSelect, refreshNiceSelect, enhanceNumberInput, initEnhancers,
    randomizeSkeletons, // public
    // экспорт ink обновления, чтобы app_init мог вызывать
    updateTabsInk,
    initTabAnimations, cleanup, addMutationObserver,
    _mutationObservers
  };
})();
