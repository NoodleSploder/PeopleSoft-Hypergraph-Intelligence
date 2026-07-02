import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

@router.get("/tree", response_class=HTMLResponse)
def admin_tree():
    return _shell("Tree Explorer", "tree", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:300px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00e5ff33;background:#001830;font-size:11px;margin:2px}
.stat b{color:#00e5ff;font-size:16px;display:block}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="tSearch" type="text" placeholder="Search tree name or description..." style="width:260px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <input id="tSetid" type="text" placeholder="SETID filter..." style="width:120px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Trees</h2>
    <div id="list" class="muted">Search to load trees.</div>
  </div>
  <div class="content">
    <h2>Selected Tree</h2>
    <div id="detail" class="muted">Select a tree from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) return null;
  return res.json();
}

function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function doSearch() {
  const q = document.getElementById('tSearch').value.trim();
  const setid = document.getElementById('tSetid').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<span class="muted">Loading...</span>';
  document.getElementById('detail').innerHTML = '<span class="muted">Select a tree.</span>';

  const rows = await api(`/api/peoplesoft/trees?env=${ENV}&q=${encodeURIComponent(q)}&setid=${encodeURIComponent(setid)}&limit=200`);
  if (!rows) { list.innerHTML = '<span class="muted">Error loading trees.</span>'; return; }

  document.getElementById('stats').textContent = `${rows.length} result${rows.length===1?'':'s'}`;
  list.innerHTML = '';
  if (!rows.length) { list.innerHTML = '<span class="muted">No trees found.</span>'; return; }

  rows.forEach(r => {
    const div = document.createElement('div');
    div.className = 'item';
    const active = (r.eff_status || '').toUpperCase() === 'A';
    div.innerHTML = `
      <div class="item-name">${esc(r.treename)} <span class="chip ${active ? 'chip-ok' : 'chip-warn'}">${active ? 'ACTIVE' : 'INACTIVE'}</span></div>
      <div class="item-meta">${r.setid ? '<span class="chip chip-muted">'+esc(r.setid)+'</span> ' : ''}${r.descr ? esc(r.descr) : ''}</div>
      <div class="item-meta" style="margin-top:2px">${r.treestrctpnm ? esc(r.treestrctpnm) : ''}</div>`;
    div.onclick = () => selectTree(r, div);
    list.appendChild(div);
  });
}

function selectTree(r, el) {
  document.querySelectorAll('.item').forEach(i => i.classList.remove('sel'));
  if (el) el.classList.add('sel');
  const d = document.getElementById('detail');
  const active = (r.eff_status || '').toUpperCase() === 'A';
  d.innerHTML = `
    <div style="margin-bottom:12px">
      <span style="font-size:16px;font-family:monospace;color:#d7faff">${esc(r.treename)}</span>
      <span class="chip ${active ? 'chip-ok' : 'chip-warn'}" style="margin-left:8px">${active ? 'ACTIVE' : 'INACTIVE'}</span>
      <a href="/admin/object/tree/${encodeURIComponent(r.treename)}?env=${ENV}" style="margin-left:12px;font-size:11px;color:#00e5ff">Open in Object Explorer &#x2197;</a>
    </div>
    ${r.descr ? `<div style="color:#8ab;font-size:12px;margin-bottom:10px">${esc(r.descr)}</div>` : ''}
    <div style="margin-bottom:10px">
      <span class="stat"><b>${esc(r.setid || '—')}</b>SETID</span>
      <span class="stat"><b>${esc(r.setcntrlvalue || '—')}</b>Set Control</span>
    </div>
    <div style="font-size:12px">
      ${r.treestrctpnm && r.treestrctpnm.trim() ? `<div style="margin-bottom:6px">Structure Record: <a href="/admin/object/record/${encodeURIComponent(r.treestrctpnm.trim())}?env=${ENV}" style="color:#00e5ff">${esc(r.treestrctpnm.trim())} &#x2197;</a></div>` : ''}
      ${r.tree_recname && r.tree_recname.trim() ? `<div>Leaf Record: <a href="/admin/object/record/${encodeURIComponent(r.tree_recname.trim())}?env=${ENV}" style="color:#00e5ff">${esc(r.tree_recname.trim())} &#x2197;</a></div>` : ''}
    </div>`;
}

doSearch();
</script>""")


@router.get("/ci", response_class=HTMLResponse)
def admin_ci():
    return _shell("Component Interface Explorer", "ci", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:300px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00e5ff33;background:#001830;font-size:11px;margin:2px}
.stat b{color:#00e5ff;font-size:16px;display:block}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="ciSearch" type="text" placeholder="Search component interface name or description..." style="width:300px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Component Interfaces</h2>
    <div id="list" class="muted">Search to load CIs.</div>
  </div>
  <div class="content">
    <h2>Selected CI</h2>
    <div id="detail" class="muted">Select a component interface from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) return null;
  return res.json();
}

function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

const CI_TYPE = {'0':'Standard', '1':'Find-only', '2':'Read-only'};

async function doSearch() {
  const q = document.getElementById('ciSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<span class="muted">Loading...</span>';
  document.getElementById('detail').innerHTML = '<span class="muted">Select a CI.</span>';

  const rows = await api(`/api/peoplesoft/cis?env=${ENV}&q=${encodeURIComponent(q)}&limit=200`);
  if (!rows) { list.innerHTML = '<span class="muted">Error loading CIs.</span>'; return; }

  document.getElementById('stats').textContent = `${rows.length} result${rows.length===1?'':'s'}`;
  list.innerHTML = '';
  if (!rows.length) { list.innerHTML = '<span class="muted">No CIs found.</span>'; return; }

  rows.forEach(r => {
    const div = document.createElement('div');
    div.className = 'item';
    const typeLabel = CI_TYPE[String(r.bctype)] || ('Type '+r.bctype);
    div.innerHTML = `
      <div class="item-name">${esc(r.bcname)}</div>
      <div class="item-meta"><span class="chip chip-muted">${esc(typeLabel)}</span>${r.descr ? ' '+esc(r.descr) : ''}</div>
      <div class="item-meta" style="margin-top:2px">${r.pnlgrpname && r.pnlgrpname.trim() ? '&#x2192; '+esc(r.pnlgrpname.trim()) : ''}</div>`;
    div.onclick = () => selectCi(r, div);
    list.appendChild(div);
  });
}

function selectCi(r, el) {
  document.querySelectorAll('.item').forEach(i => i.classList.remove('sel'));
  if (el) el.classList.add('sel');
  const d = document.getElementById('detail');
  const typeLabel = CI_TYPE[String(r.bctype)] || ('Type '+r.bctype);
  d.innerHTML = `
    <div style="margin-bottom:12px">
      <span style="font-size:16px;font-family:monospace;color:#d7faff">${esc(r.bcname)}</span>
      <span class="chip chip-info" style="margin-left:8px">${esc(typeLabel)}</span>
      <a href="/admin/object/ci/${encodeURIComponent(r.bcname)}?env=${ENV}" style="margin-left:12px;font-size:11px;color:#00e5ff">Open in Object Explorer &#x2197;</a>
    </div>
    ${r.bcdisplayname && r.bcdisplayname.trim() ? `<div style="color:#8ab;font-size:13px;margin-bottom:4px">${esc(r.bcdisplayname.trim())}</div>` : ''}
    ${r.descr ? `<div style="color:#667;font-size:12px;margin-bottom:10px">${esc(r.descr)}</div>` : ''}
    <div style="font-size:12px;margin-top:8px">
      ${r.pnlgrpname && r.pnlgrpname.trim()
        ? `<div style="margin-bottom:6px">Wrapped Component: <a href="/admin/object/component/${encodeURIComponent(r.pnlgrpname.trim())}?env=${ENV}" style="color:#00e5ff">${esc(r.pnlgrpname.trim())} &#x2197;</a></div>`
        : ''}
      ${r.objectownerid && r.objectownerid.trim() ? `<div style="color:#445;margin-bottom:4px">Owner: ${esc(r.objectownerid.trim())}</div>` : ''}
      ${r.lastupddttm ? `<div style="color:#445;font-size:11px">Last updated: ${esc(String(r.lastupddttm))}</div>` : ''}
    </div>`;
}

doSearch();
</script>""")


@router.get("/menu", response_class=HTMLResponse)
def admin_menu():
    return _shell("Menu Explorer", "menu", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:300px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.item-row{padding:5px 6px;font-size:11px;border-bottom:1px solid #0d1a22}
.item-row:hover{background:#0a1820}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="mSearch" type="text" placeholder="Search menu name or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Menus</h2>
    <div id="list" class="muted">Search to load menus.</div>
  </div>
  <div class="content">
    <h2>Menu Items</h2>
    <div id="detail" class="muted">Select a menu to see its items.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
const MENU_TYPE = {'0':'Standard','1':'Pop-up'};
async function api(path) { const r=await fetch(path); return r.ok?r.json():null; }
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
async function doSearch() {
  const q=document.getElementById('mSearch').value.trim();
  const list=document.getElementById('list');
  list.innerHTML='<span class="muted">Loading...</span>';
  document.getElementById('detail').innerHTML='<span class="muted">Select a menu.</span>';
  const rows=await api('/api/peoplesoft/menus?env='+ENV+'&q='+encodeURIComponent(q));
  if(!rows){list.innerHTML='<span class="muted">Error.</span>';return;}
  document.getElementById('stats').textContent=rows.length+' result'+(rows.length===1?'':'s');
  list.innerHTML='';
  if(!rows.length){list.innerHTML='<span class="muted">No menus found.</span>';return;}
  rows.forEach(r=>{
    const div=document.createElement('div');div.className='item';
    const tl=MENU_TYPE[String(r.menutype)]||('Type '+r.menutype);
    div.innerHTML='<div class="item-name">'+esc(r.menuname)+' <span class="chip chip-muted">'+esc(tl)+'</span></div>'
      +'<div class="item-meta">'+(r.descr?esc(r.descr):'')+'</div>';
    div.onclick=()=>selectMenu(r,div);list.appendChild(div);});
}
async function selectMenu(r,el){
  document.querySelectorAll('.item').forEach(i=>i.classList.remove('sel'));
  if(el)el.classList.add('sel');
  const d=document.getElementById('detail');
  d.innerHTML='<span class="muted">Loading items...</span>';
  const items=await api('/api/peoplesoft/menus/'+encodeURIComponent(r.menuname)+'/items?env='+ENV);
  const tl=MENU_TYPE[String(r.menutype)]||('Type '+r.menutype);
  const hdr='<div style="margin-bottom:12px"><span style="font-size:16px;font-family:monospace;color:#d7faff">'+esc(r.menuname)+'</span>'
    +' <span class="chip chip-info">'+esc(tl)+'</span>'
    +' <a href="/admin/object/menu/'+encodeURIComponent(r.menuname)+'?env='+ENV+'" style="margin-left:12px;font-size:11px;color:#00e5ff">Open in Object Explorer &#x2197;</a></div>'
    +(r.descr?'<div style="color:#8ab;font-size:12px;margin-bottom:10px">'+esc(r.descr)+'</div>':'');
  if(!items||!items.length){d.innerHTML=hdr+'<span class="muted">No items found.</span>';return;}
  let table='<table style="width:100%;border-collapse:collapse;font-size:11px">'
    +'<thead><tr style="color:#00e5ff;border-bottom:1px solid #1e3040">'
    +'<th style="text-align:left;padding:4px 6px">Bar</th><th style="text-align:left;padding:4px 6px">Item</th>'
    +'<th style="text-align:left;padding:4px 6px">Label</th><th style="text-align:left;padding:4px 6px">Component</th>'
    +'</tr></thead><tbody>';
  items.forEach(i=>{
    const comp=(i.pnlgrpname||'').trim();
    table+='<tr class="item-row">'
      +'<td style="padding:4px 6px;color:#445">'+esc(i.barname||'')+'</td>'
      +'<td style="padding:4px 6px;font-family:monospace">'+esc(i.itemname||'')+'</td>'
      +'<td style="padding:4px 6px;color:#8ab">'+esc(i.itemlabel||i.barlabel||'')+'</td>'
      +'<td style="padding:4px 6px">'+(comp?'<a href="/admin/object/component/'+encodeURIComponent(comp)+'?env='+ENV+'" style="color:#00e5ff">'+esc(comp)+'</a>':'')+'</td>'
      +'</tr>';});
  table+='</tbody></table>';
  d.innerHTML=hdr+table;
}
doSearch();
</script>""")


@router.get("/approval", response_class=HTMLResponse)
def admin_approval():
    return _shell("Approval Framework Explorer", "approval", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00e5ff33;background:#001830;font-size:11px;margin:2px}
.stat b{color:#00e5ff;font-size:16px;display:block}
.stage-row{padding:8px 10px;border-left:3px solid #00e5ff44;margin-bottom:6px;background:#030d14}
.stage-title{font-family:monospace;font-size:12px;color:#d7faff}
.stage-meta{font-size:10px;color:#556;margin-top:2px}
.step-row{padding:5px 10px;border-bottom:1px solid #0d1a22;font-size:11px}
.step-row:hover{background:#0a1820}
a{color:#00e5ff;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="awSearch" type="text" placeholder="Search workflow name or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="awStatus" onchange="doSearch()" style="width:110px">
    <option value="">All Status</option>
    <option value="A">Active</option>
    <option value="I">Inactive</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Approval Definitions</h2>
    <div id="list" class="muted">Search to load approval definitions.</div>
  </div>
  <div class="content">
    <h2>Selected Workflow</h2>
    <div id="detail" class="muted">Select an approval workflow from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
const STATUS_LABELS = {'A':['chip-ok','Active'], 'I':['chip-muted','Inactive']};

async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function statusChip(s) {
  const [cls, label] = STATUS_LABELS[String(s||'').trim()] || ['chip-muted', s||'?'];
  return `<span class="chip ${cls}">${label}</span>`;
}

async function doSearch() {
  const q = document.getElementById('awSearch').value.trim();
  const status = document.getElementById('awStatus').value;
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  if (status) params.set('status', status);
  const d = await api(`/api/peoplesoft/approvals?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading approvals.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No approval definitions found.</div>'; return; }
  list.innerHTML = items.map((a, i) =>
    `<div class="item" id="item-${i}" onclick="selectApproval('${esc(a.eoawprcs_id)}', ${i})">
       <div class="item-name">${esc(a.eoawprcs_id)}</div>
       <div class="item-meta">${esc((a.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
  window._awItems = items;
}

async function selectApproval(eoawprcsId, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/approval/${encodeURIComponent(eoawprcsId)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/approval/${esc(eoawprcsId)}`;
  let html = `
    <div style="margin-bottom:12px">
      <span style="font-family:monospace;font-size:14px;font-weight:bold">${esc(eoawprcsId)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>
    ${ov.description ? `<div style="color:#aac;font-size:12px;margin-bottom:10px">${esc(ov.description)}</div>` : ''}
    <div style="margin-bottom:12px">
      <div class="stat"><b>${ov.process_definition_count||0}</b>Process Defs</div>
      <div class="stat"><b>${ov.stage_count||0}</b>Stages</div>
      <div class="stat"><b>${ov.step_count||0}</b>Steps</div>
      <div class="stat"><b>${ov.path_count||0}</b>Paths</div>
      ${ov.owner ? `<div class="stat"><b>${esc(ov.owner)}</b>Owner</div>` : ''}
    </div>`;

  const procDefs = (d.sections||[]).find(s => s.name === 'Process Definitions');
  if (procDefs && procDefs.items && procDefs.items.length) {
    html += '<h2>Process Definitions</h2><div style="border:1px solid #1e3040">';
    html += procDefs.items.map(pd => `
      <div class="step-row">
        ${pd.relationship ? `<span class="chip ${pd.relationship === 'Active' ? 'chip-ok' : 'chip-muted'}" style="font-size:10px">${esc(pd.relationship)}</span>` : ''}
        ${pd.default ? '<span class="chip chip-info" style="font-size:10px">Default</span>' : ''}
        <span style="font-family:monospace;font-size:11px">${esc(pd.title||'')}</span>
        ${pd.admin_role ? `<span style="font-size:10px;color:#556;margin-left:8px">Admin Role: ${esc(pd.admin_role)}</span>` : ''}
      </div>`).join('');
    html += '</div>';
  }

  const stages = (d.sections||[]).find(s => s.name === 'Stages');
  if (stages && stages.items && stages.items.length) {
    html += '<h2>Stages</h2>';
    html += stages.items.map(s => `
      <div class="stage-row">
        <div class="stage-title">${s.relationship ? `<span class="chip chip-info">${esc(s.relationship)}</span>` : ''}${esc(s.title||'')}</div>
        <div class="stage-meta">${s.step_count||0} step${(s.step_count||0)!==1?'s':''}</div>
      </div>`).join('');
  }

  const steps = (d.sections||[]).find(s => s.name === 'Steps');
  if (steps && steps.items && steps.items.length) {
    html += '<h2>Steps</h2><div style="border:1px solid #1e3040">';
    html += steps.items.map(st => `
      <div class="step-row">
        ${st.relationship ? `<span class="chip chip-info" style="font-size:10px">${esc(st.relationship)}</span>` : ''}
        <span style="font-family:monospace;font-size:11px">${esc(st.title||'')}</span>
        ${st.min_approvers ? `<span style="font-size:10px;color:#556;margin-left:8px">Min Approvers: ${esc(st.min_approvers)}</span>` : ''}
      </div>`).join('');
    html += '</div>';
  }

  const paths = (d.sections||[]).find(s => s.name === 'Paths');
  if (paths && paths.items && paths.items.length) {
    html += '<h2>Paths</h2><div style="border:1px solid #1e3040">';
    html += paths.items.map(p => `
      <div class="step-row">
        ${p.relationship ? `<span class="chip chip-info" style="font-size:10px">${esc(p.relationship)}</span>` : ''}
        <span style="font-family:monospace;font-size:11px">${esc(p.title||'')}</span>
      </div>`).join('');
    html += '</div>';
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/appclass", response_class=HTMLResponse)
def admin_appclass(request: Request, env: str = "HCM"):
    nav = _nav_html("appclass", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Application Classes</title>
<meta charset="utf-8">
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:380px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:6px;display:flex;gap:6px">
    <input id="q" placeholder="Search class or package…" oninput="doSearch()"
      style="flex:1;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
    <input id="pkg" placeholder="Exact package…" oninput="doSearch()"
      style="width:130px;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 8px;border-radius:4px;font-size:12px">
  </div>
  <div id="list" style="font-size:12px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select an Application Class to view its package context and sibling classes.</div>
</div>
</div>
<script>
{_ESC_JS}
const ENV = {repr(env)};
let selected = null;

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const pkg = document.getElementById('pkg').value.trim();
  const url = `/api/peoplesoft/app-classes?env=${{encodeURIComponent(ENV)}}&q=${{encodeURIComponent(q)}}&pkg=${{encodeURIComponent(pkg)}}&limit=200`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const key = r._key || '';
    const cid = r.appclassid || '';
    const pkg2 = r.packageroot || '';
    const qp = (r.qualifypath || '').trim();
    const path = qp === ':' || !qp ? `${{pkg2}}:${{cid}}` : `${{pkg2}}:${{qp}}:${{cid}}`;
    return `<div class="list-item${{selected===key?' selected':''}}" onclick="loadDetail('${{esc(key)}}')"
      style="padding:5px 10px;border-radius:4px;cursor:pointer;margin-bottom:1px;border-bottom:1px solid #0d1520">
      <div style="font-weight:bold;color:#aa66ff;font-family:monospace;font-size:11px">${{esc(cid)}}</div>
      <div style="color:#445;font-size:10px;font-family:monospace;word-break:break-all">${{esc(path)}}</div>
    </div>`;
  }}).join('');
}}

async function loadDetail(key) {{
  selected = key;
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('selected', el.dataset?.key === key));
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading…</div>';
  const url = `/api/peoplesoft/object/app_class/${{encodeURIComponent(key)}}?env=${{encodeURIComponent(ENV)}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));
  const sibSec = secs.find(s=>s.title?.includes('Sibling'));
  const spSec = secs.find(s=>s.title?.includes('Sub-Package'));

  let html = `<h1 style="color:#aa66ff;font-size:16px;margin:0 0 4px;font-family:monospace">${{esc(uom.display_name || key)}}</h1>`;

  // Overview KV
  if (ovSec?.rows?.length) {{
    html += '<table style="border-collapse:collapse;margin-bottom:16px;font-size:13px">';
    ovSec.rows.forEach(row => {{
      html += `<tr><td style="color:#556;padding:2px 16px 2px 0;white-space:nowrap;vertical-align:top">${{esc(row.key)}}</td>
        <td style="color:#acd;font-family:monospace;word-break:break-all">${{esc(String(row.value || '—'))}}</td></tr>`;
    }});
    html += '</table>';
  }}

  // Sub-packages section (show as KV-style summary)
  if (spSec?.items?.length) {{
    html += `<h2 style="color:#aab;font-size:13px;margin:16px 0 6px">${{esc(spSec.title)}}</h2>`;
    html += '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px">';
    spSec.items.forEach(sp => {{
      const cnt = sp.chips?.[0]?.label || '';
      html += `<span style="display:inline-block;background:#0a1528;border:1px solid #1a3a5a;border-radius:3px;padding:2px 8px;font-size:11px;font-family:monospace;color:#7ab">${{esc(sp.name)}} <span style="color:#445">${{esc(cnt)}}</span></span>`;
    }});
    html += '</div>';
  }}

  // Siblings
  if (sibSec?.items?.length) {{
    html += `<h2 style="color:#aab;font-size:13px;margin:16px 0 6px">${{esc(sibSec.title)}}</h2>`;
    html += '<div style="display:flex;flex-wrap:wrap;gap:4px">';
    sibSec.items.forEach(sib => {{
      const chips = sib.chips?.map(ch => `<span style="font-size:9px;color:#996;margin-left:4px">${{esc(ch.label)}}</span>`).join('') || '';
      html += `<span style="display:inline-block;background:#0a0818;border:1px solid #2a1a4a;border-radius:3px;padding:2px 8px;font-size:11px;font-family:monospace;color:#aa66ff;cursor:pointer" onclick="loadDetail(${{JSON.stringify(key.split('~').slice(0,2).join('~') + '~' + sib.name)}})">${{esc(sib.name)}}${{chips}}</span>`;
    }});
    html += '</div>';
  }}

  if (!ovSec && !sibSec) {{
    html += '<div class="muted">No detail available.</div>';
  }}
  detail.innerHTML = html;
}}

doSearch();
</script>
</body></html>""")


@router.get("/contsvc", response_class=HTMLResponse)
def admin_contsvc(request: Request, env: str = "HCM"):
    nav = _nav_html("contsvc", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Content Services</title>
<meta charset="utf-8">
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:360px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:6px;display:flex;gap:6px">
    <input id="q" placeholder="Search service ID, name, or desc…" oninput="doSearch()"
      style="flex:1;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
    <input id="owner" placeholder="Owner…" oninput="doSearch()"
      style="width:80px;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 8px;border-radius:4px;font-size:12px">
  </div>
  <div id="list" style="font-size:12px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select a Content Service to view its parameters and usage.</div>
</div>
</div>
<script>
{_ESC_JS}
const ENV = {repr(env)};
let selected = null;

const URL_TYPE_COLOR = {{
  UPGE:'#22cc66', UAPC:'#aa66ff', UTIL:'#ffaa22', UGEN:'#44aaff', USCR:'#ff8844'
}};
const URL_TYPE_LABEL = {{
  UPGE:'Page', UAPC:'App Class', UTIL:'Utility', UGEN:'Generic URL', USCR:'Script'
}};

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const owner = document.getElementById('owner').value.trim();
  const url = `/api/peoplesoft/content-services?env=${{encodeURIComponent(ENV)}}&q=${{encodeURIComponent(q)}}&owner=${{encodeURIComponent(owner)}}&limit=200`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const sid = r.ptcs_serviceid || '';
    const name = (r.ptcs_servicename || '').trim();
    const descr = (r.descr254 || '').trim().slice(0, 70);
    const urlType = r.ptcs_serviceurltyp || '';
    const tc = URL_TYPE_COLOR[urlType] || '#778';
    const tl = URL_TYPE_LABEL[urlType] || urlType;
    const owner2 = (r.objectownerid || '').trim();
    const paramCnt = r.param_count || 0;
    return `<div class="list-item${{selected===sid?' selected':''}}" onclick="loadDetail('${{esc(sid)}}')"
      style="padding:6px 10px;border-radius:4px;cursor:pointer;margin-bottom:2px;border-bottom:1px solid #0d1520">
      <div style="font-weight:bold;color:#44ee88;font-family:monospace;font-size:11px">${{esc(sid)}}</div>
      ${{name && name!==sid ? `<div style="color:#8ab;font-size:11px">${{esc(name)}}</div>` : ''}}
      <div style="display:flex;gap:8px;margin-top:2px;align-items:center">
        <span style="font-size:10px;font-weight:bold;color:${{tc}}">${{esc(tl)}}</span>
        ${{owner2 ? `<span style="font-size:10px;color:#445">${{esc(owner2)}}</span>` : ''}}
        ${{paramCnt ? `<span style="font-size:10px;color:#334">${{paramCnt}}p</span>` : ''}}
      </div>
      ${{descr ? `<div style="color:#445;font-size:10px;margin-top:1px">${{esc(descr)}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

async function loadDetail(sid) {{
  selected = sid;
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('selected', el.innerText.trim().startsWith(sid)));
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading…</div>';
  const url = `/api/peoplesoft/object/content_service/${{encodeURIComponent(sid)}}?env=${{encodeURIComponent(ENV)}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));
  const paramSec = secs.find(s=>s.title?.includes('Parameter'));
  const useSec = secs.find(s=>s.title?.includes('Used'));

  let html = `<h1 style="color:#44ee88;font-size:16px;margin:0 0 4px">${{esc(uom.display_name || sid)}}</h1>`;
  html += `<div style="color:#445;font-family:monospace;font-size:11px;margin-bottom:14px">${{esc(sid)}}</div>`;

  // Overview KV
  if (ovSec?.rows?.length) {{
    html += '<table style="border-collapse:collapse;margin-bottom:16px;font-size:13px">';
    ovSec.rows.forEach(row => {{
      if (!row.value || row.value === '—' || row.value === '0') return;
      html += `<tr><td style="color:#556;padding:2px 16px 2px 0;white-space:nowrap;vertical-align:top">${{esc(row.key)}}</td>
        <td style="color:#acd;font-family:monospace;word-break:break-all">${{esc(String(row.value))}}</td></tr>`;
    }});
    html += '</table>';
  }}

  // Parameters
  if (paramSec?.items?.length) {{
    html += `<h2 style="color:#aab;font-size:13px;margin:16px 0 6px">${{esc(paramSec.title)}}</h2>`;
    html += paramSec.items.map(p => {{
      const req = p.chips?.[0]?.label === 'required';
      const rc = req ? '#ff6655' : '#445';
      const meta = p.meta ? `<span style="color:#445;font-size:11px;margin-left:12px">${{esc(p.meta)}}</span>` : '';
      return `<div style="padding:3px 8px;border-bottom:1px solid #0d1a2a;font-family:monospace;font-size:12px">
        <span style="color:#44ee88">${{esc(p.name)}}</span>
        <span style="color:${{rc}};font-size:10px;margin-left:8px">${{req?'required':'optional'}}</span>
        ${{meta}}
      </div>`;
    }}).join('');
  }}

  // Where used
  if (useSec?.items?.length) {{
    html += `<h2 style="color:#aab;font-size:13px;margin:16px 0 6px">${{esc(useSec.title)}}</h2>`;
    html += '<div style="display:flex;flex-wrap:wrap;gap:4px">';
    useSec.items.forEach(u => {{
      const portal = u.chips?.[0]?.label || '';
      html += `<span style="display:inline-block;background:#0a1a0a;border:1px solid #1a3a1a;border-radius:3px;padding:2px 8px;font-size:11px;font-family:monospace;color:#7c9">${{esc(u.name)}}<span style="color:#334;margin-left:6px;font-size:10px">${{esc(portal)}}</span></span>`;
    }});
    html += '</div>';
  }}

  if (!ovSec && !paramSec) {{
    html += '<div class="muted">No detail available.</div>';
  }}
  detail.innerHTML = html;
}}

doSearch();
</script>
</body></html>""")


@router.get("/adsdef", response_class=HTMLResponse)
def admin_adsdef(request: Request, env: str = "HCM"):
    nav = _nav_html("adsdef", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>ADS Definitions</title>
<meta charset="utf-8">
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:340px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:6px;display:flex;gap:6px">
    <input id="q" placeholder="Search ADS name or description…" oninput="doSearch()"
      style="flex:1;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
    <input id="own" placeholder="Owner" oninput="doSearch()"
      style="width:80px;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 6px;border-radius:4px;font-size:12px">
  </div>
  <div id="list" style="font-size:12px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select an Application Data Set definition to view its records and groups.</div>
</div>
</div>
<script>
{_ESC_JS}
const ENV = {repr(env)};
let selected = null;

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const own = document.getElementById('own').value.trim();
  const url = `/api/peoplesoft/ads-definitions?env=${{encodeURIComponent(ENV)}}&q=${{encodeURIComponent(q)}}&owner=${{encodeURIComponent(own)}}&limit=200`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const name = r.ptadsname || '';
    const descr = (r.descr || '').trim().slice(0, 60);
    const owner = (r.objectownerid || '').trim();
    const recs = r.record_count || 0;
    return `<div class="list-item${{selected===name?' selected':''}}" onclick="loadDetail('${{esc(name)}}')"
      style="padding:6px 10px;border-radius:4px;cursor:pointer;margin-bottom:2px;border-bottom:1px solid #0d1520">
      <div style="font-weight:bold;color:#6688ff;font-family:monospace;font-size:11px">${{esc(name)}}</div>
      <div style="display:flex;gap:8px;margin-top:2px;align-items:center">
        ${{recs ? `<span style="font-size:10px;color:#445">${{recs}} records</span>` : ''}}
        ${{owner ? `<span style="font-size:10px;color:#556">${{esc(owner)}}</span>` : ''}}
      </div>
      ${{descr ? `<div style="color:#445;font-size:10px;margin-top:1px">${{esc(descr)}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

async function loadDetail(name) {{
  selected = name;
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('selected', el.innerText.trim().startsWith(name)));
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading…</div>';
  const url = `/api/peoplesoft/object/ads_definition/${{encodeURIComponent(name)}}?env=${{encodeURIComponent(ENV)}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));
  const recSec = secs.find(s=>s.title?.includes('Records'));
  const grpSec = secs.find(s=>s.title?.includes('Groups'));

  function kvTable(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">` +
      sec.items.map(i=>`<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap;vertical-align:top">${{esc(i.label)}}</td>
        <td style="padding:4px 0;color:#c8d8e8">${{esc(String(i.value||''))}}</td></tr>`).join('') +
      `</table>`;
  }}

  function itemList(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<div style="display:flex;flex-direction:column;gap:4px">` +
      sec.items.map(i=>{{
        const chips = (i.chips||[]).map(c=>`<span style="padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;background:#1a1a2a;border:1px solid #334;color:#aac">${{esc(c.label||c)}}</span>`).join(' ');
        return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid #0d1520">
          <span style="font-family:monospace;font-size:11px;color:#c8d8e8">${{esc(i.name||'')}}</span>
          ${{chips}}
          ${{i.meta ? `<span style="font-size:10px;color:#445">${{esc(i.meta)}}</span>` : ''}}
        </div>`;
      }}).join('') + `</div>`;
  }}

  const ov = uom.overview || {{}};
  detail.innerHTML = `
    <h2 style="font-family:monospace;color:#6688ff;font-size:14px;margin:0 0 4px">${{esc(name)}}</h2>
    <div style="font-size:12px;color:#556;margin-bottom:16px">${{esc(uom.display_name||'')}}</div>
    <div style="display:flex;gap:12px;margin-bottom:16px;font-size:12px;color:#778">
      <span>Key cols: <b style="color:#aac">${{ov.key_columns||0}}</b></span>
      <span>Records: <b style="color:#aac">${{ov.record_count||0}}</b></span>
      <span>Groups: <b style="color:#aac">${{ov.group_count||0}}</b></span>
    </div>
    ${{uom.warnings?.length ? `<div style="color:#f90;font-size:11px;margin-bottom:12px">${{uom.warnings.map(w=>esc(w)).join('<br>')}}</div>` : ''}}
    ${{ovSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>${{kvTable(ovSec)}}` : ''}}
    ${{recSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">${{esc(recSec.title)}}</h3>${{itemList(recSec)}}` : ''}}
    ${{grpSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">${{esc(grpSec.title)}}</h3>${{itemList(grpSec)}}` : ''}}
  `;
}}

doSearch();
</script>
</body></html>""")


@router.get("/urldef", response_class=HTMLResponse)
def admin_urldef(request: Request, env: str = "HCM"):
    nav = _nav_html("urldef", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>URL Definitions</title>
<meta charset="utf-8">
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:340px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:6px;display:flex;gap:6px">
    <input id="q" placeholder="Search URL ID, description, or URL…" oninput="doSearch()"
      style="flex:1;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
  </div>
  <div id="list" style="font-size:12px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select a URL definition to view its details.</div>
</div>
</div>
<script>
{_ESC_JS}
const ENV = {repr(env)};
let selected = null;

function urlType(url) {{
  const u = (url||'').toUpperCase();
  if (u.startsWith('RECORD://')) return 'Record';
  if (u.startsWith('HTTP')) return 'HTTP';
  if (u.startsWith('FTP')) return 'FTP';
  if (u.startsWith('MAILTO')) return 'Email';
  if (u.startsWith('%')) return 'Variable';
  return 'Generic';
}}

const TYPE_COLOR = {{
  Record:'#aa66ff', HTTP:'#44aaff', FTP:'#ffaa44',
  Email:'#44ffaa', Variable:'#ffff44', Generic:'#778'
}};

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const url = `/api/peoplesoft/url-definitions?env=${{encodeURIComponent(ENV)}}&q=${{encodeURIComponent(q)}}&limit=200`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const name = r.url_id || '';
    const descr = (r.descr || '').trim().slice(0, 50);
    const uval = (r.url || '').trim().slice(0, 60);
    const tp = urlType(r.url);
    const tc = TYPE_COLOR[tp] || '#778';
    return `<div class="list-item${{selected===name?' selected':''}}" onclick="loadDetail('${{esc(name)}}')"
      style="padding:6px 10px;border-radius:4px;cursor:pointer;margin-bottom:2px;border-bottom:1px solid #0d1520">
      <div style="font-weight:bold;color:#55dd33;font-family:monospace;font-size:11px">${{esc(name)}}</div>
      <div style="display:flex;gap:8px;margin-top:2px;align-items:center">
        <span style="font-size:10px;font-weight:bold;color:${{tc}}">${{esc(tp)}}</span>
      </div>
      ${{descr ? `<div style="color:#445;font-size:10px;margin-top:1px">${{esc(descr)}}</div>` : ''}}
      ${{uval ? `<div style="color:#334;font-size:10px;font-family:monospace">${{esc(uval)}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

async function loadDetail(name) {{
  selected = name;
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('selected', el.innerText.trim().startsWith(name)));
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading…</div>';
  const url = `/api/peoplesoft/object/url_definition/${{encodeURIComponent(name)}}?env=${{encodeURIComponent(ENV)}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));

  function kvTable(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">` +
      sec.items.map(i=>`<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap;vertical-align:top">${{esc(i.label)}}</td>
        <td style="padding:4px 0;color:#c8d8e8;word-break:break-all">${{esc(String(i.value||''))}}</td></tr>`).join('') +
      `</table>`;
  }}

  const ov = uom.overview || {{}};
  detail.innerHTML = `
    <h2 style="font-family:monospace;color:#55dd33;font-size:14px;margin:0 0 4px">${{esc(name)}}</h2>
    <div style="font-size:12px;color:#556;margin-bottom:16px">${{esc(uom.display_name||'')}}</div>
    <div style="margin-bottom:16px;font-size:12px;color:#778">
      Type: <b style="color:#aac">${{esc(ov.url_type||'')}}</b>
    </div>
    ${{uom.warnings?.length ? `<div style="color:#f90;font-size:11px;margin-bottom:12px">${{uom.warnings.map(w=>esc(w)).join('<br>')}}</div>` : ''}}
    ${{ovSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>${{kvTable(ovSec)}}` : ''}}
  `;
}}

doSearch();
</script>
</body></html>""")


@router.get("/cbskill", response_class=HTMLResponse)
def admin_cbskill(request: Request, env: str = "HCM"):
    nav = _nav_html("cbskill", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Chatbot Skills</title>
<meta charset="utf-8">
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:340px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:6px;display:flex;gap:6px">
    <input id="q" placeholder="Search skill name, description, or URL param…" oninput="doSearch()"
      style="flex:1;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
  </div>
  <div id="list" style="font-size:12px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select a Chatbot Skill to view its parameters and result states.</div>
</div>
</div>
<script>
{_ESC_JS}
const ENV = {repr(env)};
let selected = null;

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const url = `/api/peoplesoft/chatbot-skills?env=${{encodeURIComponent(ENV)}}&q=${{encodeURIComponent(q)}}&limit=200`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const name = r.ptcbapplname || '';
    const descr = (r.descr50 || '').trim().slice(0, 50);
    const urlp = (r.ptcburlparamname || '').trim();
    const pcnt = r.param_count || 0;
    return `<div class="list-item${{selected===name?' selected':''}}" onclick="loadDetail('${{esc(name)}}')"
      style="padding:6px 10px;border-radius:4px;cursor:pointer;margin-bottom:2px;border-bottom:1px solid #0d1520">
      <div style="font-weight:bold;color:#dd44ff;font-family:monospace;font-size:11px">${{esc(name)}}</div>
      <div style="display:flex;gap:8px;margin-top:2px;align-items:center">
        ${{pcnt ? `<span style="font-size:10px;color:#445">${{pcnt}} params</span>` : ''}}
        ${{urlp ? `<span style="font-size:10px;color:#334;font-family:monospace">${{esc(urlp)}}</span>` : ''}}
      </div>
      ${{descr ? `<div style="color:#445;font-size:10px;margin-top:1px">${{esc(descr)}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

async function loadDetail(name) {{
  selected = name;
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('selected', el.innerText.trim().startsWith(name)));
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading…</div>';
  const url = `/api/peoplesoft/object/chatbot_skill/${{encodeURIComponent(name)}}?env=${{encodeURIComponent(ENV)}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));
  const paramSec = secs.find(s=>s.title?.includes('Parameter'));
  const stateSec = secs.find(s=>s.title?.includes('State'));

  function kvTable(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">` +
      sec.items.map(i=>`<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap;vertical-align:top">${{esc(i.label)}}</td>
        <td style="padding:4px 0;color:#c8d8e8;font-family:monospace">${{esc(String(i.value||''))}}</td></tr>`).join('') +
      `</table>`;
  }}

  function itemList(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<div style="display:flex;flex-direction:column;gap:4px">` +
      sec.items.map(i=>{{
        const chips = (i.chips||[]).map(c=>`<span style="padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;background:#1a1a2a;border:1px solid #334;color:#aac">${{esc(c.label||c)}}</span>`).join(' ');
        return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid #0d1520">
          <span style="font-family:monospace;font-size:11px;color:#c8d8e8">${{esc(i.name||'')}}</span>
          ${{chips}}
          ${{i.meta ? `<span style="font-size:10px;color:#445">${{esc(i.meta)}}</span>` : ''}}
        </div>`;
      }}).join('') + `</div>`;
  }}

  const ov = uom.overview || {{}};
  detail.innerHTML = `
    <h2 style="font-family:monospace;color:#dd44ff;font-size:14px;margin:0 0 4px">${{esc(name)}}</h2>
    <div style="font-size:12px;color:#556;margin-bottom:4px">${{esc(uom.display_name||'')}}</div>
    ${{ov.url_parameter ? `<div style="font-family:monospace;font-size:11px;color:#778;margin-bottom:16px">${{esc(ov.url_parameter)}}</div>` : ''}}
    <div style="display:flex;gap:12px;margin-bottom:16px;font-size:12px;color:#778">
      <span>Params: <b style="color:#aac">${{ov.param_count||0}}</b></span>
      <span>States: <b style="color:#aac">${{ov.state_count||0}}</b></span>
    </div>
    ${{uom.warnings?.length ? `<div style="color:#f90;font-size:11px;margin-bottom:12px">${{uom.warnings.map(w=>esc(w)).join('<br>')}}</div>` : ''}}
    ${{ovSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>${{kvTable(ovSec)}}` : ''}}
    ${{paramSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">${{esc(paramSec.title)}}</h3>${{itemList(paramSec)}}` : ''}}
    ${{stateSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">${{esc(stateSec.title)}}</h3>${{itemList(stateSec)}}` : ''}}
  `;
}}

doSearch();
</script>
</body></html>""")




@router.get("/objects", response_class=HTMLResponse)
def admin_objects(request: Request, env: str = "HCM"):
    nav = _nav_html("objects", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Object Explorer</title>
<meta charset="utf-8">
{_NAV_CSS}
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#050b12;color:#c8d8e8;font-family:Arial,sans-serif}}
.muted{{color:#446;font-style:italic;font-size:12px}}
.search-bar{{display:flex;gap:8px;align-items:center;padding:12px 20px;border-bottom:1px solid #1a2a3a;background:#060d18;flex-wrap:wrap}}
input.main-q{{flex:1;min-width:240px;background:#0a1520;border:1px solid #1a3a5a;color:#d7faff;padding:8px 12px;border-radius:4px;font-size:14px}}
input.main-q:focus{{outline:none;border-color:#00e5ff}}
.filter-row{{display:flex;flex-wrap:wrap;gap:4px;align-items:center;padding:7px 20px;background:#060d18;border-bottom:1px solid #0d1520}}
.filter-lbl{{font-size:10px;color:#334;margin-right:4px}}
.type-pill{{display:inline-block;padding:2px 9px;border-radius:12px;font-size:11px;font-weight:bold;cursor:pointer;border:1px solid transparent;margin:1px}}
.type-pill.on{{border-color:currentColor}}
.results-area{{padding:14px 20px;overflow-y:auto;height:calc(100vh - 115px)}}
.result-group{{margin-bottom:18px}}
.group-hdr{{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#445;margin-bottom:5px;padding-bottom:3px;border-bottom:1px solid #0d1520;display:flex;align-items:center;gap:6px}}
.result-item{{display:flex;align-items:baseline;gap:8px;padding:4px 8px;border-radius:3px;border-bottom:1px solid #090f17;text-decoration:none}}
.result-item:hover{{background:rgba(0,229,255,.06)}}
.result-name{{font-family:monospace;font-size:12px;font-weight:bold}}
.result-desc{{font-size:11px;color:#445;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.total-note{{font-size:11px;color:#334;margin-bottom:10px}}
</style>
</head><body class="ds-body">
{nav}
<div class="search-bar">
  <input class="main-q" id="q" placeholder="Search across all PeopleSoft object types…" autofocus
    onkeydown="if(event.key==='Enter')doSearch()" oninput="debounce()">
  <button onclick="doSearch()"
    style="background:#00e5ff;border:none;padding:7px 16px;border-radius:4px;cursor:pointer;font-size:13px;font-weight:bold;color:#000">Search</button>
  <span id="status" class="muted" style="font-size:11px"></span>
</div>
<div class="filter-row" id="frow" style="display:none">
  <span class="filter-lbl">TYPE:</span>
  <span class="type-pill on" style="color:#778" id="p-all" onclick="setType('')">All</span>
  <span id="pills"></span>
</div>
<div class="results-area" id="results">
  <div class="muted" style="margin-top:48px;text-align:center">Enter a search term to find PeopleSoft objects across all types.</div>
</div>
<script>
{_ESC_JS}
const ENV = {repr(env)};
let _rows = [], _type = '', _timer = null;

const TC = {{
  record:'#44ddff', field:'#00e5ff', component:'#44aaff', page:'#8888ff',
  operator:'#ffdd44', role:'#ffaa22', permissionlist:'#ff9900',
  application_engine:'#22cc88', peoplecode:'#aa66ff',
  application_class:'#cc88ff', application_package:'#cc88ff', app_class:'#cc88ff',
  sql_definition:'#4488ff', query:'#88ddff', ci:'#22ddaa',
  menu:'#8899aa', portal_registry:'#7799bb', xlat_field:'#99aa66',
  message:'#ff6688', routing:'#ff4488', ib_routing:'#ff4488',
  service_operation:'#ff4488', ib_operation:'#ff6688',
  ib_service_group:'#cc4466', message_catalog:'#aa3355',
  file_layout:'#77aacc', xml_publisher_report:'#aa7755',
  xml_publisher_datasource:'#996655', prcs_defn:'#88cc44',
}};
const tc = t => TC[t] || '#778';

function debounce() {{ clearTimeout(_timer); _timer = setTimeout(doSearch, 280); }}

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const res = document.getElementById('results');
  if (!q) {{
    res.innerHTML = '<div class="muted" style="margin-top:48px;text-align:center">Enter a search term.</div>';
    document.getElementById('frow').style.display = 'none';
    return;
  }}
  document.getElementById('status').textContent = 'Searching…';
  _rows = await fetch(`/api/peoplesoft/search?env=${{encodeURIComponent(ENV)}}&q=${{encodeURIComponent(q)}}&limit=300`).then(r=>r.json()).catch(()=>[]);
  _type = '';
  render();
  document.getElementById('status').textContent = `${{_rows.length}} result${{_rows.length===1?'':'s'}}`;
}}

function setType(t) {{
  _type = t;
  document.querySelectorAll('.type-pill').forEach(p => {{
    const isAll = p.id==='p-all', match = isAll ? !t : p.dataset.t===t;
    p.classList.toggle('on', match);
    if (match && !isAll) {{ const col=tc(t); p.style.background=col+'22'; p.style.borderColor=col; }}
    else if (!isAll) {{ p.style.background=''; p.style.borderColor='transparent'; }}
  }});
  render();
}}

function render() {{
  const byType = {{}};
  for (const r of _rows) {{ (byType[r.type]||(byType[r.type]=[])).push(r); }}
  const typeOrder = Object.entries(byType).sort((a,b)=>b[1].length-a[1].length).map(([t])=>t);

  const frow = document.getElementById('frow');
  frow.style.display = _rows.length ? '' : 'none';
  document.getElementById('p-all').classList.toggle('on', !_type);
  document.getElementById('pills').innerHTML = typeOrder.map(t => {{
    const col = tc(t);
    const on = _type===t;
    return `<span class="type-pill${{on?' on':''}}" style="color:${{col}};background:${{on?col+'22':''}};border-color:${{on?col:'transparent'}}"
      id="p-${{esc(t)}}" data-t="${{esc(t)}}" onclick="setType('${{esc(t)}}')">${{t.replace(/_/g,' ')}} ${{byType[t].length}}</span>`;
  }}).join('');

  const filtered = _type ? _rows.filter(r=>r.type===_type) : _rows;
  const byFilt = {{}};
  for (const r of filtered) {{ if (!r.error) (byFilt[r.type]||(byFilt[r.type]=[])).push(r); }}
  const filtOrder = _type ? [_type] : typeOrder.filter(t=>byFilt[t]);

  if (!filtered.length) {{ document.getElementById('results').innerHTML = '<div class="muted">No results.</div>'; return; }}

  let html = `<div class="total-note">${{filtered.length}} result${{filtered.length===1?'':'s'}}${{_type?' &mdash; type <b>'+esc(_type.replace(/_/g,' '))+'</b>':''}}</div>`;
  for (const t of filtOrder) {{
    const items = byFilt[t]||[];
    if (!items.length) continue;
    const col = tc(t);
    const lbl = t.replace(/_/g,' ').replace(/\b./g,c=>c.toUpperCase());
    html += `<div class="result-group"><div class="group-hdr">
      <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${{col}};flex-shrink:0"></span>
      <span style="color:${{col}}">${{esc(lbl)}}</span>
      <span style="color:#334">(${{items.length}})</span></div>`;
    for (const r of items) {{
      const link = (r._links&&r._links.admin)||'#';
      html += `<a class="result-item" href="${{esc(link)}}">
        <span class="result-name" style="color:${{col}}">${{esc(r.name||'')}}</span>
        <span class="result-desc">${{esc((r.description||'').trim())}}</span>
      </a>`;
    }}
    html += '</div>';
  }}
  document.getElementById('results').innerHTML = html;
}}

(function(){{
  const q = new URLSearchParams(location.search).get('q');
  if (q) {{ document.getElementById('q').value=q; doSearch(); }}
}})();
</script>
</body></html>""")
