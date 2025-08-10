// UI helpers: tooltips, enhancers, skeletons, resize Plotly, tabs ink listeners
(function(){
  window.App = window.App || {};
  const { debounce } = window.App.util;

  // Bootstrap tooltips
  document.addEventListener('DOMContentLoaded', () => {
    const tList=[].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"],[title][data-bs-toggle2]'));
    tList.forEach(el=> new bootstrap.Tooltip(el));
  });

  // Enhancers: NiceSelect
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
      menu.style.top = ''; menu.style.bottom = '';
      if (spaceBelow < desired){ menu.style.bottom = `calc(100% + 6px)`; } else { menu.style.top = `calc(100% + 6px)`; }
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
    const wrap = select.parentElement?.classList.contains('nselect') ? select.parentElement : null;
    if (wrap){
      const label = wrap.querySelector('.nselect-label');
      const sel = select.options[select.selectedIndex];
      if (label && sel) label.textContent = sel.textContent;
    }
  }

  // Number input enhancers
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

  window.App.ui = { enhanceSelect, refreshNiceSelect, enhanceNumberInput, initEnhancers, randomizeSkeletons };
})();
