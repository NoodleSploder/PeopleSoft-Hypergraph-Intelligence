import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

@router.get("/efmapping", response_class=HTMLResponse)
def admin_efmapping():
    return _shell("Event Mapping Explorer", "efmapping", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#ddcc00;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #ddcc0033;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #ddcc0022;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #ddcc0022;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #ddcc0044;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#ddcc00}
button{background:#ddcc00;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(221,204,0,.07);border-left-color:#ddcc0055}
.item.sel{background:rgba(221,204,0,.12);border-left-color:#ddcc00}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#1a1800;border:1px solid #ddcc0044;color:#ddcc00}
.stat{display:inline-block;padding:4px 12px;border:1px solid #ddcc0033;background:#1a1800;font-size:11px;margin:2px}
.stat b{color:#ddcc00;font-size:16px;display:block}
.ctx-row{padding:6px 10px;border-bottom:1px solid #1a1800;font-size:11px}
.ctx-row:hover{background:#120e00}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right}
.kv-val{color:#d7faff;font-family:monospace}
a{color:#ddcc00;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="efSearch" type="text" placeholder="Search mapping ID or description..." style="width:270px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="efStatus" onchange="doSearch()" style="width:110px">
    <option value="">All Status</option>
    <option value="A">Active</option>
    <option value="I">Inactive</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Event Mappings</h2>
    <div id="list" class="muted">Search to load event mappings.</div>
  </div>
  <div class="content">
    <h2>Selected Mapping</h2>
    <div id="detail" class="muted">Select an event mapping from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function statusChip(s) {
  if (s==='A') return '<span class="chip chip-ok">Active</span>';
  if (s==='I') return '<span class="chip chip-muted">Inactive</span>';
  return '';
}

async function doSearch() {
  const q = document.getElementById('efSearch').value.trim();
  const status = document.getElementById('efStatus').value;
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  if (status) params.set('status', status);
  const d = await api(`/api/peoplesoft/event-mappings?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No event mappings found.</div>'; return; }
  list.innerHTML = items.map((m, i) =>
    `<div class="item" id="item-${i}" onclick="selectMapping('${esc(m.efmappingid)}', ${i})">
       <div class="item-name">${statusChip(m.status)}${esc(m.efmappingid)}</div>
       <div class="item-meta">${esc((m.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectMapping(efmappingid, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/event_mapping/${encodeURIComponent(efmappingid)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/event_mapping/${esc(efmappingid)}`;
  let html = `
    <div style="margin-bottom:12px">
      ${statusChip(ov.status)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#ddcc00">${esc(efmappingid)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>
    ${ov.description ? `<div style="color:#aac;font-size:12px;margin-bottom:10px">${esc(ov.description)}</div>` : ''}
    <div style="margin-bottom:12px">
      <div class="stat"><b>${ov.context_count||0}</b>Contexts</div>
      ${ov.owner ? `<div class="stat"><b>${esc(ov.owner)}</b>Owner</div>` : ''}
    </div>`;

  const ctxSection = (d.sections||[]).find(s => s.name === 'Contexts');
  if (ctxSection && ctxSection.items && ctxSection.items.length) {
    html += '<h2>Contexts</h2><div style="border:1px solid #1a1800">';
    html += ctxSection.items.map(c => `
      <div class="ctx-row">
        ${c.relationship ? `<span class="chip chip-info">${esc(c.relationship)}</span>` : ''}
        <span style="font-family:monospace">${esc(c.title||'')}</span>
        ${c.event ? `<span style="color:#556;font-size:10px;margin-left:8px">Event: ${esc(c.event)}</span>` : ''}
        ${c.handler ? `<span style="color:#334;font-size:10px;margin-left:6px">→ ${esc(c.handler)}</span>` : ''}
      </div>`).join('');
    html += '</div>';
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/relcontent", response_class=HTMLResponse)
def admin_relcontent():
    return _shell("Related Content Explorer", "relcontent", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#9944ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #9944ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #9944ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #9944ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #9944ff44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#9944ff}
button{background:#9944ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#fff;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(153,68,255,.07);border-left-color:#9944ff55}
.item.sel{background:rgba(153,68,255,.12);border-left-color:#9944ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#0a0018;border:1px solid #9944ff44;color:#9944ff}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right}
.kv-val{color:#d7faff;font-family:monospace}
a{color:#9944ff;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="rcSearch" type="text" placeholder="Search related content ID or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Related Content Services</h2>
    <div id="list" class="muted">Search to load related content services.</div>
  </div>
  <div class="content">
    <h2>Selected Service</h2>
    <div id="detail" class="muted">Select a service from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
const SVC_LABELS = {U:'URL',C:'Component',S:'Script',A:'App Class',P:'PS Page',I:'iScript',R:'Related Action'};
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function statusChip(s) {
  if (s==='A') return '<span class="chip chip-ok">Active</span>';
  if (s==='I') return '<span class="chip chip-muted">Inactive</span>';
  return '';
}
function svcChip(t) {
  const label = SVC_LABELS[String(t||'')] || String(t||'');
  return label ? `<span class="chip chip-info">${esc(label)}</span>` : '';
}

async function doSearch() {
  const q = document.getElementById('rcSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const d = await api(`/api/peoplesoft/related-content?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No related content services found.</div>'; return; }
  list.innerHTML = items.map((r, i) =>
    `<div class="item" id="item-${i}" onclick="selectService('${esc(r.relconid)}', ${i})">
       <div class="item-name">${statusChip(r.status)}${svcChip(r.servicetype)}${esc(r.relconid)}</div>
       <div class="item-meta">${esc((r.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectService(relconid, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/related_content/${encodeURIComponent(relconid)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/related_content/${esc(relconid)}`;
  const defnSection = (d.sections||[]).find(s => s.name === 'Definition');
  const kv = defnSection?.data || {};
  let html = `
    <div style="margin-bottom:12px">
      ${statusChip(ov.status)}
      ${svcChip(ov.servicetype)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#9944ff">${esc(relconid)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>
    ${ov.description ? `<div style="color:#aac;font-size:12px;margin-bottom:10px">${esc(ov.description)}</div>` : ''}
    <div class="kv-grid">`;
  for (const [k, v] of Object.entries(kv)) {
    if (k !== 'Description' && k !== 'Status') {
      html += `<div class="kv-key">${esc(k)}</div><div class="kv-val">${esc(String(v||''))}</div>`;
    }
  }
  html += `</div>`;
  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/navcoll", response_class=HTMLResponse)
def admin_navcoll():
    return _shell("Navigation Collections", "navcoll", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00bb66;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00bb6633;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00bb6622;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #00bb6622;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #00bb6644;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#00bb66}
button{background:#00bb66;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,187,102,.07);border-left-color:#00bb6655}
.item.sel{background:rgba(0,187,102,.12);border-left-color:#00bb66}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#001a14;border:1px solid #00bb6644;color:#00bb66}
.chip-tile{background:#001a14;border:1px solid #00ddaa44;color:#00ddaa}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00bb6633;background:#001a14;font-size:11px;margin:2px}
.stat b{color:#00bb66;font-size:16px;display:block}
.line-row{padding:6px 10px;border-bottom:1px solid #001a14;font-size:11px;display:flex;gap:8px;align-items:baseline}
.line-row:hover{background:#041208}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right;padding-top:2px}
.kv-val{color:#d7faff;font-family:monospace}
a{color:#00bb66;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="ncSearch" type="text" placeholder="Search collection ID or title..." style="width:270px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="ncPortal" style="width:120px" onchange="doSearch()">
    <option value="EMPLOYEE">EMPLOYEE</option>
    <option value="">All Portals</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Collections</h2>
    <div id="list" class="muted">Search to load navigation collections.</div>
  </div>
  <div class="content">
    <h2>Selected Collection</h2>
    <div id="detail" class="muted">Select a collection from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
const LINE_TYPE_CHIP = {
  C: ['chip-info',  'Content Ref'],
  F: ['chip-muted', 'Folder'],
  T: ['chip-tile',  'Tile'],
  S: ['chip-muted', 'Static'],
};

async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function statusChip(s) {
  if (s === 'A' || s === 'Active') return '<span class="chip chip-ok">Active</span>';
  if (s === 'I' || s === 'Inactive') return '<span class="chip chip-muted">Inactive</span>';
  return '';
}
function lineTypeChip(lt) {
  const [cls, label] = LINE_TYPE_CHIP[String(lt||'')] || ['chip-muted', lt||'?'];
  return `<span class="chip ${cls}">${esc(label)}</span>`;
}

async function doSearch() {
  const q = document.getElementById('ncSearch').value.trim();
  const portal = document.getElementById('ncPortal').value;
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  if (portal) params.set('portal', portal);
  const d = await api(`/api/peoplesoft/nav-collections?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading collections.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No navigation collections found.</div>'; return; }
  list.innerHTML = items.map((c, i) =>
    `<div class="item" id="item-${i}" onclick="selectCollection('${esc(c.coll_id)}', ${i})">
       <div class="item-name">${statusChip(c.eff_status)}${esc(c.coll_id)}</div>
       <div class="item-meta">${esc((c.coll_title||'').slice(0,60))}${c.portal_name ? ` · ${esc(c.portal_name)}` : ''}</div>
     </div>`
  ).join('');
  window._ncItems = items;
}

async function selectCollection(collId, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const portal = document.getElementById('ncPortal').value || 'EMPLOYEE';
  const d = await api(`/api/peoplesoft/object/nav_collection/${encodeURIComponent(collId)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading collection.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/nav_collection/${esc(collId)}`;
  let html = `
    <div style="margin-bottom:12px">
      ${statusChip(ov.eff_status)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#00bb66">${esc(collId)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>
    ${ov.title ? `<div style="color:#aac;font-size:13px;margin-bottom:10px">${esc(ov.title)}</div>` : ''}
    <div style="margin-bottom:12px">
      <div class="stat"><b>${ov.line_count||0}</b>Lines</div>
      ${ov.portal ? `<div class="stat"><b>${esc(ov.portal)}</b>Portal</div>` : ''}
      ${ov.owner ? `<div class="stat"><b>${esc(ov.owner)}</b>Owner</div>` : ''}
    </div>`;

  const linesSection = (d.sections||[]).find(s => s.name === 'Lines');
  if (linesSection && linesSection.items && linesSection.items.length) {
    html += '<h2>Lines</h2><div style="border:1px solid #001a14">';
    html += linesSection.items.map(ln => {
      const nbr = ln.line_nbr !== undefined ? `<span style="color:#334;font-size:10px;min-width:28px;text-align:right">${ln.line_nbr}.</span>` : '';
      const rel = String(ln.relationship || '');
      const chipCls = rel === 'Tile' ? 'chip-tile' : rel === 'Content Ref' ? 'chip-info' : 'chip-muted';
      const relChip = rel ? `<span class="chip ${chipCls}">${esc(rel)}</span>` : '';
      const urlPart = ln.url ? `<span style="font-size:10px;color:#334;margin-left:6px;font-family:monospace">${esc(ln.url.slice(0,60))}</span>` : '';
      return `<div class="line-row">${nbr}${relChip}${esc(ln.title||'')}${urlPart}</div>`;
    }).join('');
    html += '</div>';
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/xpub", response_class=HTMLResponse)
def admin_xpub():
    return _shell("XML Publisher Explorer", "xpub", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#cc44aa;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #cc44aa33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #cc44aa22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #cc44aa22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #cc44aa44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#cc44aa}
button{background:#cc44aa;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#fff;font-weight:bold}
button.sec{background:#1a0a18;border:1px solid #cc44aa44;color:#cc44aa}
button.sec.active{background:#cc44aa22;border-color:#cc44aa;color:#fff}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(204,68,170,.07);border-left-color:#cc44aa55}
.item.sel{background:rgba(204,68,170,.12);border-left-color:#cc44aa}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#1a0818;border:1px solid #cc44aa44;color:#cc44aa}
.chip-ds{background:#180814;border:1px solid #aa336644;color:#aa6688}
.stat{display:inline-block;padding:4px 12px;border:1px solid #cc44aa33;background:#1a0818;font-size:11px;margin:2px}
.stat b{color:#cc44aa;font-size:16px;display:block}
.tmpl-row{padding:6px 10px;border-bottom:1px solid #1a0818;font-size:11px;display:flex;gap:8px;align-items:center}
.tmpl-row:hover{background:#130810}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right;padding-top:2px}
.kv-val{color:#d7faff;font-family:monospace}
a{color:#cc44aa;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
.tab-strip{display:flex;gap:6px;margin-bottom:10px}
</style>
<div class="topbar">
  <div class="tab-strip" id="modeTabs">
    <button class="sec active" id="modeReports"   onclick="switchMode('reports')">Reports</button>
    <button class="sec"        id="modeDatasources" onclick="switchMode('datasources')">Data Sources</button>
  </div>
  <input id="xpubSearch" type="text" placeholder="Search report ID or description..." style="width:260px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2 id="sidebarTitle">Reports</h2>
    <div id="list" class="muted">Search to load XML Publisher objects.</div>
  </div>
  <div class="content">
    <h2>Selected Object</h2>
    <div id="detail" class="muted">Select an item from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
let _mode = 'reports';

async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function dsChip(type) {
  const labels = {XML:'XML',CQR:'Connected Query',QRY:'PS Query',XMD:'XML Data',RST:'REST'};
  const label = labels[String(type||'')] || String(type||'');
  return label ? `<span class="chip chip-ds">${esc(label)}</span>` : '';
}

function switchMode(mode) {
  _mode = mode;
  document.getElementById('modeReports').classList.toggle('active', mode==='reports');
  document.getElementById('modeDatasources').classList.toggle('active', mode==='datasources');
  document.getElementById('sidebarTitle').textContent = mode === 'reports' ? 'Reports' : 'Data Sources';
  document.getElementById('xpubSearch').placeholder = mode === 'reports'
    ? 'Search report ID or description...'
    : 'Search data source ID or description...';
  document.getElementById('detail').innerHTML = '<div class="muted">Select an item from the list.</div>';
  doSearch();
}

async function doSearch() {
  const q = document.getElementById('xpubSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const url = _mode === 'reports'
    ? `/api/peoplesoft/xpub/reports?${params}`
    : `/api/peoplesoft/xpub/datasources?${params}`;
  const d = await api(url);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No results found.</div>'; return; }
  if (_mode === 'reports') {
    list.innerHTML = items.map((r, i) =>
      `<div class="item" id="item-${i}" onclick="selectReport('${esc(r.report_defn_id)}', ${i})">
         <div class="item-name">${esc(r.report_defn_id)}</div>
         <div class="item-meta">${esc((r.descr||'').slice(0,55))}${r.ds_id ? ` · DS: ${esc(r.ds_id)}` : ''}</div>
       </div>`
    ).join('');
  } else {
    list.innerHTML = items.map((r, i) =>
      `<div class="item" id="item-${i}" onclick="selectDatasource('${esc(r.ds_id)}', ${i})">
         <div class="item-name">${dsChip(r.ds_type)}${esc(r.ds_id)}</div>
         <div class="item-meta">${esc((r.descr||'').slice(0,60))}</div>
       </div>`
    ).join('');
  }
  window._xpubItems = items;
}

async function selectReport(reportDefnId, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/xml_publisher_report/${encodeURIComponent(reportDefnId)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading report.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/xml_publisher_report/${esc(reportDefnId)}`;
  let html = `
    <div style="margin-bottom:12px">
      ${ov.status_label ? `<span class="chip ${ov.status_label === 'Active' ? 'chip-ok' : 'chip-muted'}">${esc(ov.status_label)}</span>` : ''}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#cc44aa">${esc(reportDefnId)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>`;

  if (ov.description) html += `<div style="color:#aac;font-size:12px;margin-bottom:10px">${esc(ov.description)}</div>`;

  html += `<div style="margin-bottom:12px">
    <div class="stat"><b>${ov.template_count||0}</b>Templates</div>
    <div class="stat"><b>${ov.output_format_count||0}</b>Output Formats</div>
    ${ov.owner ? `<div class="stat"><b>${esc(ov.owner)}</b>Owner</div>` : ''}
  </div>`;

  if (ov.ds_id) {
    html += `<div class="kv-grid" style="margin-bottom:12px">
      <div class="kv-key">Data Source</div><div class="kv-val">${esc(ov.ds_id)}</div>`;
    if (ov.datasrc_descr) {
      html += `<div class="kv-key">DS Description</div><div class="kv-val">${esc(ov.datasrc_descr)}</div>`;
    }
    if (ov.datasrc_type_label) {
      html += `<div class="kv-key">DS Type</div><div class="kv-val">${dsChip(ov.datasrc_type)}${esc(ov.datasrc_type_label)}</div>`;
    }
    html += `</div>`;
  }

  const tmplSection = (d.sections||[]).find(s => s.name === 'Templates');
  if (tmplSection && tmplSection.items && tmplSection.items.length) {
    html += '<h2>Templates / Layouts</h2><div style="border:1px solid #1a0818">';
    html += tmplSection.items.map(t => `
      <div class="tmpl-row">
        ${t.default ? '<span class="chip chip-ok">Default</span>' : ''}
        ${t.relationship ? `<span class="chip chip-info">${esc(t.relationship)}</span>` : ''}
        <span style="font-family:monospace;flex:1">${esc(t.title||'')}</span>
        ${t.lang ? `<span style="font-size:10px;color:#556">${esc(t.lang)}</span>` : ''}
      </div>`).join('');
    html += '</div>';
  }

  const fmtSection = (d.sections||[]).find(s => s.name === 'Output Formats');
  if (fmtSection && fmtSection.items && fmtSection.items.length) {
    html += '<h2>Output Formats</h2><div style="border:1px solid #1a0818">';
    html += fmtSection.items.map(f => `
      <div class="tmpl-row">
        ${f.default ? '<span class="chip chip-ok">Default</span>' : ''}
        <span style="font-family:monospace;flex:1">${esc(f.title||'')}</span>
      </div>`).join('');
    html += '</div>';
  }

  detail.innerHTML = html;
}

async function selectDatasource(dsId, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  const item = window._xpubItems ? window._xpubItems[idx] : null;
  if (!item) { detail.innerHTML = '<div class="muted">No data.</div>'; return; }
  detail.innerHTML = `
    <div style="margin-bottom:12px">
      ${dsChip(item.ds_type)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#aa3366">${esc(dsId)}</span>
    </div>
    <div class="kv-grid">
      <div class="kv-key">Description</div><div class="kv-val">${esc(item.descr||'—')}</div>
      <div class="kv-key">Type</div><div class="kv-val">${esc(item.ds_type_label||item.ds_type||'—')}</div>
      <div class="kv-key">Active</div><div class="kv-val">${esc(item.active_flag||'—')}</div>
    </div>`;
}

doSearch();
</script>""")


@router.get("/pcsearch", response_class=HTMLResponse)
def admin_pcsearch():
    return _shell("PeopleCode Source Search", "pcsearch", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:240px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff}
select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-ref{font-family:monospace;font-size:11px;color:#d7faff}
.item-parent{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold}
.chip-type{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-event{background:#0d1a00;border:1px solid #44aa4444;color:#66cc66}
pre{background:#030d14;border:1px solid #1e3040;padding:12px;font-family:monospace;font-size:11px;white-space:pre-wrap;word-break:break-word;line-height:1.5;overflow-x:auto;max-height:500px}
.hit{background:#2a1c00;color:#ffcc44}
.kw{color:#569cd6}.str{color:#ce9178}.cmt{color:#6a9955}.builtin{color:#dcdcaa}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="pcq" type="text" placeholder="Search in PeopleCode source... (e.g. EMPLMT_SRCH_ALL, CreateSQL, %UpdateStats)" style="width:320px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="limitSel">
    <option value="50">50 results</option>
    <option value="100" selected>100 results</option>
    <option value="200">200 results</option>
    <option value="500">500 results</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#445;margin-left:6px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Matching Programs</h2>
    <div id="list" class="muted">Enter a search term and press Search.</div>
  </div>
  <div class="content">
    <h2>Source Preview</h2>
    <div id="detail" class="muted">Select a program to view source with matches highlighted.</div>
  </div>
</div>
<script>
const ENV=localStorage.getItem('dsEnv')||'HCM';
const PC_KW=['If','Then','Else','End-If','For','End-For','While','End-While','Repeat','Until','Return','Break','Continue','Local','Global','Component','Function','End-Function','Method','End-Method','class','Extends','Implements','import','Array','String','Integer','Number','Date','DateTime','Boolean','Object','Any','Exception','Try','Catch','End-Try','Throw','CreateObject','GetLevel0','GetRecord','GetField','GetPage','GetGrid','GetRow','GetComponent','Step','DoWhile','DoUntil'];
const PC_BUILTIN=['MessageBox','SQLExec','CreateSQL','Close','Fetch','Insert','Update','Delete','IsNull','None','Null','True','False','All','And','Or','Not','As','Of','Property','Get','Set','Value','Name','Type','CreateRecord','CreateMessage','CreateRowset','CreateArray','GetRowset','GetMessage','%This','%Super','%CurrentTimeIn','%Date','%DateTime','%Time','%EmployeeId','%OperatorId','%MenuName','%Component','%Page','%Action','%Mode','%Panel','%PanelGroup','%UpdateStats','%SelectAll','%Insert','%Update','%Delete','%SelectByKey','%SelectByKeyEffdt','%DateAdd','%DateTimeAdd','%DateTimeDiff','%DateDiff','%Substring','%NumToChar','%CharToNum','%DateOut','%TimeOut','%Round','%Truncate','%Abs','%Sign','%Mod','%Upper','%Lower','%Rtrim','%Ltrim','%Replace','%Len','%Value','%like','%contains','%starts'];

function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
async function api(p){const r=await fetch(p);return r.ok?r.json():null;}

function highlightPC(src,q){
  // tokenize and highlight PeopleCode source with match highlighting
  let h='',i=0;const s=src;
  while(i<s.length){
    if(s[i]==='/' && s[i+1]==='*'){const e=s.indexOf('*/',i+2);const end=e<0?s.length:e+2;h+='<span class="cmt">'+esc(s.slice(i,end))+'</span>';i=end;continue;}
    if(s[i]==='"'){let j=i+1;while(j<s.length&&s[j]!=='"')j++;h+='<span class="str">'+esc(s.slice(i,j+1))+'</span>';i=j+1;continue;}
    // word
    if(/[A-Za-z%_]/.test(s[i])){let j=i;while(j<s.length&&/[A-Za-z0-9_.%\-]/.test(s[j]))j++;const w=s.slice(i,j);
      if(PC_KW.includes(w))h+='<span class="kw">'+esc(w)+'</span>';
      else if(PC_BUILTIN.includes(w))h+='<span class="builtin">'+esc(w)+'</span>';
      else if(q&&w.toUpperCase()===q.toUpperCase())h+='<span class="hit">'+esc(w)+'</span>';
      else h+=esc(w);i=j;continue;}
    // check for match at any position (non-word chars)
    if(q&&s.slice(i).toUpperCase().startsWith(q.toUpperCase())){h+='<span class="hit">'+esc(s.slice(i,i+q.length))+'</span>';i+=q.length;continue;}
    h+=esc(s[i]);i++;}
  return h;
}

let _results=[];
async function doSearch(){
  const q=document.getElementById('pcq').value.trim();
  const lim=document.getElementById('limitSel').value;
  if(!q){return;}
  const list=document.getElementById('list');
  list.innerHTML='<span class="muted">Searching...</span>';
  document.getElementById('detail').innerHTML='<span class="muted">Select a result.</span>';
  document.getElementById('stats').textContent='';
  const data=await api('/api/peoplesoft/peoplecode/source-search?q='+encodeURIComponent(q)+'&env='+ENV+'&limit='+lim);
  if(!data){list.innerHTML='<span class="muted">Error.</span>';return;}
  _results=data.items||[];
  document.getElementById('stats').textContent=_results.length+(data.warnings&&data.warnings.length?' ('+data.warnings[0].message+')':' programs matched');
  list.innerHTML='';
  if(!_results.length){list.innerHTML='<span class="muted">No PeopleCode programs match "'+esc(q)+'".</span>';return;}
  _results.forEach((r,idx)=>{
    const div=document.createElement('div');div.className='item';
    const ptype=r.parent_type||'';const pname=r.parent_name||'';
    div.innerHTML='<div class="item-ref">'+esc(r.reference||r.encoded_reference||'')+'</div>'
      +'<div class="item-parent">'+(ptype?'<span class="chip chip-type">'+esc(ptype.toUpperCase())+'</span> ':'')+(pname?esc(pname):'')+' <span class="chip chip-event">'+esc(r.event_name||r.objectvalue7||'')+'</span></div>';
    div.onclick=()=>showSource(r,q,div);
    list.appendChild(div);
  });
}

function showSource(r,q,el){
  document.querySelectorAll('.item').forEach(i=>i.classList.remove('sel'));
  if(el)el.classList.add('sel');
  const src=r.source||'(source not loaded)';
  const d=document.getElementById('detail');
  const ref=r.reference||r.encoded_reference||'';
  const ptype=r.parent_type||'';const pname=r.parent_name||'';
  d.innerHTML='<div style="margin-bottom:10px">'
    +'<span style="font-family:monospace;font-size:13px;color:#d7faff">'+esc(ref)+'</span>'
    +' <a href="/admin/object/peoplecode/'+encodeURIComponent(r.encoded_reference||ref)+'?env='+ENV+'" style="font-size:11px;color:#00e5ff;margin-left:10px">Open in PC Explorer &#x2197;</a>'
    +(ptype&&pname?' <a href="/admin/object/'+encodeURIComponent(ptype)+'/'+encodeURIComponent(pname)+'?env='+ENV+'" style="font-size:11px;color:#00e5ff;margin-left:10px">&#x2192; '+esc(pname)+' &#x2197;</a>':'')
    +'</div>'
    +'<pre>'+highlightPC(src,q)+'</pre>';
  // scroll first match into view
  setTimeout(()=>{const hit=d.querySelector('.hit');if(hit)hit.scrollIntoView({block:'center',behavior:'smooth'});},50);
}
</script>""")


@router.get("/srchdef", response_class=HTMLResponse)
def admin_srchdef():
    return _shell("Search Definition Explorer", "srchdef", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#2299ee;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #2299ee33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #2299ee22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #2299ee22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #2299ee44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#2299ee}
button{background:#2299ee;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(34,153,238,.07);border-left-color:#2299ee55}
.item.sel{background:rgba(34,153,238,.12);border-left-color:#2299ee}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#001020;border:1px solid #2299ee44;color:#2299ee}
.stat{display:inline-block;padding:4px 12px;border:1px solid #2299ee33;background:#001020;font-size:11px;margin:2px}
.stat b{color:#2299ee;font-size:16px;display:block}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right;padding-top:2px}
.kv-val{color:#d7faff;font-family:monospace}
.field-row{padding:5px 10px;border-bottom:1px solid #001020;font-size:11px;display:flex;gap:8px;align-items:baseline}
.field-row:hover{background:#020c14}
a{color:#2299ee;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="sdSearch" type="text" placeholder="Search source name or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Search Definitions</h2>
    <div id="list" class="muted">Search to load search definitions.</div>
  </div>
  <div class="content">
    <h2>Selected Definition</h2>
    <div id="detail" class="muted">Select a definition from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function typeChip(s) {
  return s ? `<span class="chip chip-info">${esc(s)}</span>` : '';
}

async function doSearch() {
  const q = document.getElementById('sdSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const d = await api(`/api/peoplesoft/search-definitions?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No search definitions found.</div>'; return; }
  list.innerHTML = items.map((r, i) =>
    `<div class="item" id="item-${i}" onclick="selectDef('${esc(r.ptsf_source_name)}', ${i})">
       <div class="item-name">${esc(r.ptsf_source_name)}</div>
       <div class="item-meta">${esc((r.descr100||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectDef(sourceName, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/search_definition/${encodeURIComponent(sourceName)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/search_definition/${esc(sourceName)}`;
  const sections = d.sections || [];
  const overviewSec = sections.find(s => s.id === 'overview') || {};
  const rows = overviewSec.rows || [];
  const fieldsSec = sections.find(s => s.id === 'fields');
  const pgSec = sections.find(s => s.id === 'panel_groups');

  let html = `
    <div style="margin-bottom:12px">
      ${typeChip(ov.source_type)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#2299ee">${esc(sourceName)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>`;

  if (rows.length) {
    html += `<div class="kv-grid">`;
    for (const row of rows) {
      html += `<div class="kv-key">${esc(row.label)}</div><div class="kv-val">${esc(String(row.value||''))}</div>`;
    }
    html += `</div>`;
  }

  const counts = d._uom?._raw?.counts || {};
  html += `<div style="margin:10px 0">`
    + `<span class="stat"><b>${counts.fields||0}</b>Fields</span>`
    + `<span class="stat"><b>${counts.panel_groups||0}</b>Panel Groups</span>`
    + `</div>`;

  if (fieldsSec && (fieldsSec.items||[]).length) {
    html += `<h2>${esc(fieldsSec.title)}</h2>`;
    html += fieldsSec.items.map(f =>
      `<div class="field-row">
         <span style="font-family:monospace;color:#d7faff">${esc(f.name)}</span>
         ${(f.chips||[]).map(c=>`<span class="chip chip-info">${esc(c.label)}</span>`).join('')}
         ${f.meta ? `<span style="color:#556;font-size:10px">${esc(f.meta)}</span>` : ''}
       </div>`
    ).join('');
  }

  if (pgSec && (pgSec.items||[]).length) {
    html += `<h2>${esc(pgSec.title)}</h2>`;
    html += pgSec.items.map(p =>
      `<div class="field-row">
         <span style="font-family:monospace;color:#d7faff">${esc(p.name)}</span>
         ${(p.chips||[]).map(c=>`<span class="chip chip-muted">${esc(c.label)}</span>`).join('')}
         ${p.meta ? `<span style="color:#aac;font-size:11px">${esc(p.meta)}</span>` : ''}
       </div>`
    ).join('');
  }

  if (!rows.length && !fieldsSec && !pgSec) {
    html += `<div class="muted">No detail available.</div>`;
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/srchcat", response_class=HTMLResponse)
def admin_srchcat():
    return _shell("Search Category Explorer", "srchcat", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#7744ee;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #7744ee33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #7744ee22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #7744ee22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #7744ee44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#7744ee}
button{background:#7744ee;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#fff;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(119,68,238,.07);border-left-color:#7744ee55}
.item.sel{background:rgba(119,68,238,.12);border-left-color:#7744ee}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-info{background:#10001a;border:1px solid #7744ee44;color:#7744ee}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.stat{display:inline-block;padding:4px 12px;border:1px solid #7744ee33;background:#10001a;font-size:11px;margin:2px}
.stat b{color:#7744ee;font-size:16px;display:block}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right}
.kv-val{color:#d7faff;font-family:monospace}
.field-row{padding:5px 10px;border-bottom:1px solid #10001a;font-size:11px;display:flex;gap:8px;align-items:baseline}
.field-row:hover{background:#0a0014}
a{color:#7744ee;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="scSearch" type="text" placeholder="Search category ID or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Search Categories</h2>
    <div id="list" class="muted">Search to load search categories.</div>
  </div>
  <div class="content">
    <h2>Selected Category</h2>
    <div id="detail" class="muted">Select a category from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function fieldChip(c) {
  return `<span class="chip ${esc(c.cls||'chip-info')}">${esc(c.label)}</span>`;
}

async function doSearch() {
  const q = document.getElementById('scSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const d = await api(`/api/peoplesoft/search-categories?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No search categories found.</div>'; return; }
  list.innerHTML = items.map((r, i) =>
    `<div class="item" id="item-${i}" onclick="selectCat('${esc(r.ptsf_srccat_name)}', ${i})">
       <div class="item-name">${esc(r.ptsf_srccat_name)}</div>
       <div class="item-meta">${esc((r.descr100||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectCat(srccatName, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/search_category/${encodeURIComponent(srccatName)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const adminUrl = `/admin/object/search_category/${esc(srccatName)}`;
  const sections = d.sections || [];
  const overviewSec = sections.find(s => s.id === 'overview') || {};
  const rows = overviewSec.rows || [];
  const sboSec = sections.find(s => s.id === 'sbo_links');
  const dispSec = sections.find(s => s.id === 'display_fields');
  const advSec = sections.find(s => s.id === 'advanced_fields');
  const facetSec = sections.find(s => s.id === 'facets');

  let html = `
    <div style="margin-bottom:12px">
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#7744ee">${esc(srccatName)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>`;

  if (rows.length) {
    html += `<div class="kv-grid">`;
    for (const row of rows) {
      html += `<div class="kv-key">${esc(row.label)}</div><div class="kv-val">${esc(String(row.value||''))}</div>`;
    }
    html += `</div>`;
  }

  const counts = d._uom?._raw?.counts || {};
  html += `<div style="margin:10px 0">`
    + `<span class="stat"><b>${counts.sbo_links||0}</b>SBO Links</span>`
    + `<span class="stat"><b>${counts.display_fields||0}</b>Display Fields</span>`
    + `<span class="stat"><b>${counts.advanced_fields||0}</b>Advanced Fields</span>`
    + `<span class="stat"><b>${counts.facets||0}</b>Facets</span>`
    + `</div>`;

  for (const sec of [sboSec, dispSec, advSec, facetSec]) {
    if (sec && (sec.items||[]).length) {
      html += `<h2>${esc(sec.title)}</h2>`;
      html += sec.items.map(it =>
        `<div class="field-row">
           <span style="font-family:monospace;color:#d7faff">${esc(it.name)}</span>
           ${(it.chips||[]).map(fieldChip).join('')}
           ${it.meta ? `<span style="color:#556;font-size:10px">${esc(it.meta)}</span>` : ''}
         </div>`
      ).join('');
    }
  }

  if (!rows.length && !sboSec && !dispSec && !advSec && !facetSec) {
    html += `<div class="muted">No detail available.</div>`;
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/dropzone", response_class=HTMLResponse)
def admin_dropzone():
    return _shell("Drop Zone Explorer", "dropzone", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#ee8800;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #ee880033;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #ee880022;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #ee880022;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #ee880044;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#ee8800}
button{background:#ee8800;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(238,136,0,.07);border-left-color:#ee880055}
.item.sel{background:rgba(238,136,0,.12);border-left-color:#ee8800}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.stat{display:inline-block;padding:4px 12px;border:1px solid #ee880033;background:#1a1000;font-size:11px;margin:2px}
.stat b{color:#ee8800;font-size:16px;display:block}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right}
.kv-val{color:#d7faff;font-family:monospace}
.field-row{padding:5px 10px;border-bottom:1px solid #1a1000;font-size:11px}
a{color:#ee8800;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="dzSearch" type="text" placeholder="Search drop zone name or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Drop Zones</h2>
    <div id="list" class="muted">Search to load drop zones.</div>
  </div>
  <div class="content">
    <h2>Selected Drop Zone</h2>
    <div id="detail" class="muted">Select a drop zone from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function doSearch() {
  const q = document.getElementById('dzSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const d = await api(`/api/peoplesoft/drop-zones?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No drop zones found.</div>'; return; }
  list.innerHTML = items.map((r, i) =>
    `<div class="item" id="item-${i}" onclick="selectDz('${esc(r.dzname)}', ${i})">
       <div class="item-name">${esc(r.dzname)}</div>
       <div class="item-meta">${esc((r.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectDz(dzname, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/drop_zone/${encodeURIComponent(dzname)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const adminUrl = `/admin/object/drop_zone/${esc(dzname)}`;
  const sections = d.sections || [];
  const overviewSec = sections.find(s => s.id === 'overview') || {};
  const rows = overviewSec.rows || [];
  const compSec = sections.find(s => s.id === 'components');
  const pageSec = sections.find(s => s.id === 'pages');
  const itemSec = sections.find(s => s.id === 'items');

  let html = `
    <div style="margin-bottom:12px">
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#ee8800">${esc(dzname)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>`;

  if (rows.length) {
    html += `<div class="kv-grid">`;
    for (const row of rows) {
      html += `<div class="kv-key">${esc(row.label)}</div><div class="kv-val">${esc(String(row.value||''))}</div>`;
    }
    html += `</div>`;
  }

  html += `<div style="margin:10px 0">`
    + `<span class="stat"><b>${(compSec?.items||[]).length}</b>Components</span>`
    + `<span class="stat"><b>${(pageSec?.items||[]).length}</b>Pages</span>`
    + `<span class="stat"><b>${(itemSec?.items||[]).length}</b>Items</span>`
    + `</div>`;

  for (const sec of [compSec, pageSec, itemSec]) {
    if (sec && (sec.items||[]).length) {
      html += `<h2>${esc(sec.title)}</h2>`;
      html += sec.items.map(it =>
        `<div class="field-row">
           <span style="font-family:monospace;color:#d7faff">${esc(it.name)}</span>
           ${it.meta ? `<span style="color:#556;font-size:10px;margin-left:8px">${esc(it.meta)}</span>` : ''}
         </div>`
      ).join('');
    }
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")

@router.get("/pivotgrid", response_class=HTMLResponse)
def admin_pivotgrid():
    return _shell("PivotGrid Explorer", "pivotgrid", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#22cc66;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #22cc6633;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #22cc6622;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #22cc6622;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #22cc6644;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#22cc66}
button{background:#22cc66;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(34,204,102,.07);border-left-color:#22cc6655}
.item.sel{background:rgba(34,204,102,.12);border-left-color:#22cc66}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #22cc6644;color:#22cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#0a1a10;border:1px solid #22cc6644;color:#22cc66}
.stat{display:inline-block;padding:4px 12px;border:1px solid #22cc6633;background:#0a1a10;font-size:11px;margin:2px}
.stat b{color:#22cc66;font-size:16px;display:block}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right;padding-top:2px}
.kv-val{color:#d7faff;font-family:monospace}
.field-row{padding:5px 10px;border-bottom:1px solid #0a1a10;font-size:11px;display:flex;gap:8px;align-items:baseline}
.field-row:hover{background:#061410}
a{color:#22cc66;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="pgSearch" type="text" placeholder="Search PivotGrid name or title..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>PivotGrids</h2>
    <div id="list" class="muted">Search to load PivotGrids.</div>
  </div>
  <div class="content">
    <h2>Selected PivotGrid</h2>
    <div id="detail" class="muted">Select a PivotGrid from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function chip(cls, label) { return `<span class="chip ${esc(cls)}">${esc(label)}</span>`; }
function typeChip(dstype) { return dstype ? chip('chip-info', dstype) : ''; }

async function doSearch() {
  const q = document.getElementById('pgSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const d = await api(`/api/peoplesoft/pivot-grids?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No PivotGrids found.</div>'; return; }
  list.innerHTML = items.map((r, i) =>
    `<div class="item" id="item-${i}" onclick="selectPG('${esc(r.ptpg_pgridname)}', ${i})">
       <div class="item-name">${esc(r.ptpg_pgridname)}</div>
       <div class="item-meta">${esc((r.ptpg_pgridtitle||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectPG(pgridname, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/pivot_grid/${encodeURIComponent(pgridname)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/pivot_grid/${esc(pgridname)}`;
  const sections = d.sections || [];
  const overviewSec = sections.find(s => s.id === 'overview') || {};
  const rows = overviewSec.rows || [];
  const colsSec = sections.find(s => s.id === 'columns');

  let html = `
    <div style="margin-bottom:12px">
      ${typeChip(ov.ds_type)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#22cc66">${esc(pgridname)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>`;

  if (rows.length) {
    html += `<div class="kv-grid">`;
    for (const row of rows) {
      html += `<div class="kv-key">${esc(row.label)}</div><div class="kv-val">${esc(String(row.value||''))}</div>`;
    }
    html += `</div>`;
  }

  const counts = d._uom?._raw?.counts || {};
  html += `<div style="margin:10px 0">`
    + `<span class="stat"><b>${counts.columns||0}</b>Columns</span>`
    + `</div>`;

  if (colsSec && (colsSec.items||[]).length) {
    html += `<h2>${esc(colsSec.title)}</h2>`;
    html += colsSec.items.map(it =>
      `<div class="field-row">
         <span style="font-family:monospace;color:#d7faff">${esc(it.name)}</span>
         ${(it.chips||[]).map(c => chip(c.cls||'chip-info', c.label)).join('')}
         ${it.meta ? `<span style="color:#556;font-size:10px">${esc(it.meta)}</span>` : ''}
       </div>`
    ).join('');
  }

  if (!rows.length && !colsSec) {
    html += `<div class="muted">No detail available.</div>`;
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")

@router.get("/stylesheet", response_class=HTMLResponse)
def admin_stylesheet(request: Request, env: str = "HCM"):
    nav = _nav_html("stylesheet", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Style Sheets</title>
<meta charset="utf-8">
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:340px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:6px;display:flex;gap:6px">
    <input id="q" placeholder="Search stylesheet name or description…" oninput="doSearch()"
      style="flex:1;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
    <select id="tp" onchange="doSearch()"
      style="width:100px;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 6px;border-radius:4px;font-size:12px">
      <option value="">All</option>
      <option value="0">Classic</option>
      <option value="1">Fluid</option>
      <option value="2">Component</option>
    </select>
  </div>
  <div id="list" style="font-size:12px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select a Style Sheet to view its CSS class inventory.</div>
</div>
</div>
<script>
{_ESC_JS}
const ENV = {repr(env)};
let selected = null;

const TYPE_LABEL = {{0:'Classic', 1:'Fluid Theme', 2:'Component Style'}};
const TYPE_COLOR = {{0:'#aa88ff', 1:'#ffcc44', 2:'#44aaff'}};

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const tp = document.getElementById('tp').value;
  const url = `/api/peoplesoft/style-sheets?env=${{encodeURIComponent(ENV)}}&q=${{encodeURIComponent(q)}}&ss_type=${{encodeURIComponent(tp)}}&limit=200`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const name = r.stylesheetname || '';
    const descr = (r.descr || '').trim().slice(0, 50);
    const tp2 = r.stylesheettype;
    const tc = TYPE_COLOR[tp2] || '#778';
    const tl = TYPE_LABEL[tp2] || String(tp2);
    const classes = r.class_count || 0;
    return `<div class="list-item${{selected===name?' selected':''}}" onclick="loadDetail('${{esc(name)}}')"
      style="padding:6px 10px;border-radius:4px;cursor:pointer;margin-bottom:2px;border-bottom:1px solid #0d1520">
      <div style="font-weight:bold;color:#ffcc44;font-family:monospace;font-size:11px">${{esc(name)}}</div>
      <div style="display:flex;gap:8px;margin-top:2px;align-items:center">
        <span style="font-size:10px;font-weight:bold;color:${{tc}}">${{esc(tl)}}</span>
        ${{classes ? `<span style="font-size:10px;color:#445">${{classes}} classes</span>` : ''}}
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
  const url = `/api/peoplesoft/object/style_sheet/${{encodeURIComponent(name)}}?env=${{encodeURIComponent(ENV)}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));
  const chipSec = secs.find(s=>s.type==='chips');

  function kvTable(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">` +
      sec.items.map(i=>`<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap">${{esc(i.label)}}</td>
        <td style="padding:4px 0;color:#c8d8e8">${{esc(String(i.value||''))}}</td></tr>`).join('') +
      `</table>`;
  }}

  const ov = uom.overview || {{}};
  const chips = chipSec ? chipSec.items.map(c => `<span style="display:inline-block;padding:2px 8px;border-radius:3px;font-size:11px;font-family:monospace;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;margin:2px">${{esc(c.label||c)}}</span>`).join('') : '';

  detail.innerHTML = `
    <h2 style="font-family:monospace;color:#ffcc44;font-size:14px;margin:0 0 4px">${{esc(name)}}</h2>
    <div style="font-size:12px;color:#556;margin-bottom:16px">${{esc(uom.display_name||'')}}</div>
    <div style="margin-bottom:16px;font-size:12px;color:#778">
      Type: <b style="color:#aac">${{esc(ov.type||'')}}</b>
      &nbsp;&nbsp;CSS classes: <b style="color:#aac">${{ov.class_count||0}}</b>
    </div>
    ${{uom.warnings?.length ? `<div style="color:#f90;font-size:11px;margin-bottom:12px">${{uom.warnings.map(w=>esc(w)).join('<br>')}}</div>` : ''}}
    ${{ovSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>${{kvTable(ovSec)}}` : ''}}
    ${{chips ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">${{esc(chipSec?.title||'CSS Classes')}}</h3><div style="line-height:1.8">${{chips}}</div>` : ''}}
  `;
}}

doSearch();
</script>
</body></html>""")


