import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

@router.get("/pmmetric", response_class=HTMLResponse)
def admin_pmmetric():
    return _shell("PM Metrics Explorer", "pmmetric", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#9988ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #9988ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #9988ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #9988ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0d0d1a;color:#d7faff;border:1px solid #9988ff44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#9988ff}
button{background:#9988ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(153,136,255,.07);border-left-color:#9988ff55}
.item.sel{background:rgba(153,136,255,.12);border-left-color:#9988ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.muted{color:#556;font-style:italic}
.badge{display:inline-block;padding:1px 5px;border-radius:2px;font-size:10px;font-family:monospace;
       background:#1a1a2a;border:1px solid #9988ff44;color:#9988ff;margin-left:4px}
</style>
<div class="topbar">
  <input id="q" type="text" placeholder="Search metric label, description, or numeric ID..." style="width:300px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>PM Metrics</h2>
    <div id="list" class="muted">Search to load metrics.</div>
  </div>
  <div class="content">
    <h2>Selected Metric</h2>
    <div id="detail" class="muted">Select a metric from the list.</div>
  </div>
</div>
<script>
function ENV_VAL() { return window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HCM'); }
let _rows = [];
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
const TYPE_LABELS = {'1':'Config','2':'Metric','3':'Flag/Enum','4':'String','5':'Count','6':'Duration','7':'ID'};

async function doSearch() {
  const q = document.getElementById('q').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV_VAL(), limit: 206});
  if (q) params.set('q', q);
  const d = await api('/api/peoplesoft/pm-metrics?' + params);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  _rows = Array.isArray(d) ? d : (d.items || []);
  document.getElementById('stats').textContent = _rows.length + ' result' + (_rows.length !== 1 ? 's' : '');
  if (!_rows.length) { list.innerHTML = '<div class="muted">No metrics found.</div>'; return; }
  list.innerHTML = _rows.map(function(r, i) {
    const tl = TYPE_LABELS[String(r.pm_metrictype)] || ('T' + r.pm_metrictype);
    return '<div class="item" id="pm-' + i + '" data-idx="' + i + '">' +
      '<div class="item-name">' + esc(r.pm_metriclabel) +
        '<span class="badge">' + esc(tl) + '</span></div>' +
      '<div class="item-meta">ID ' + esc(String(r.pm_metricid)) +
        (r.descr60 && r.descr60 !== r.pm_metriclabel ? ' \u00b7 ' + esc((r.descr60||'').slice(0,50)) : '') + '</div>' +
      '</div>';
  }).join('');
  list.querySelectorAll('.item').forEach(function(el) {
    el.addEventListener('click', function() { selectMetric(+el.dataset.idx); });
  });
}

async function selectMetric(idx) {
  const r = _rows[idx];
  if (!r) return;
  document.querySelectorAll('.item').forEach(function(el) { el.classList.remove('sel'); });
  const el = document.getElementById('pm-' + idx);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api('/api/peoplesoft/object/pm_metric/' + encodeURIComponent(String(r.pm_metricid)) + '?env=' + ENV_VAL());
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const sections = d.sections || [];
  const ovSec    = sections.find(function(s) { return s.title && s.title.indexOf('Overview') >= 0; });
  const enumSec  = sections.find(function(s) { return s.title && s.title.indexOf('Enum') >= 0; });
  const transSec = sections.find(function(s) { return s.title && s.title.indexOf('Transaction') >= 0; });
  const evtSec   = sections.find(function(s) { return s.title && s.title.indexOf('Event') >= 0; });

  function kvTable(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">' +
      sec.items.map(function(item) {
        return '<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap">' + esc(item.label) + '</td>' +
          '<td style="padding:4px 0;color:#c8d8e8;font-family:monospace">' + esc(String(item.value||'')) + '</td></tr>';
      }).join('') + '</table>';
  }

  function chipList(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px">' +
      sec.items.map(function(c) {
        return '<span style="padding:2px 8px;border-radius:3px;font-size:11px;font-family:monospace;background:#1a1a2a;border:1px solid #9988ff44;color:#9ab">' + esc(c.label||c) + '</span>';
      }).join('') + '</div>';
  }

  function itemList(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<div style="margin-bottom:16px">' +
      sec.items.map(function(it) {
        return '<div style="padding:4px 0;border-bottom:1px solid #1a1a2a;font-size:12px">' +
          '<span style="font-family:monospace;color:#c8d8e8">' + esc(it.label||'') + '</span>' +
          (it.value ? '<span style="color:#556;font-size:10px;margin-left:8px">' + esc(it.value) + '</span>' : '') +
          '</div>';
      }).join('') + '</div>';
  }

  const ov = d.overview || {};
  let html = '<h2 style="font-family:monospace;color:#9988ff;font-size:14px;margin:0 0 4px">' + esc(r.pm_metriclabel) + '</h2>' +
    '<div style="font-size:12px;color:#556;margin-bottom:16px">Metric ID: ' + esc(String(r.pm_metricid)) +
    (ov.type_label ? ' \u00b7 ' + esc(ov.type_label) : '') + '</div>';
  if (d.warnings && d.warnings.length) {
    html += '<div style="color:#f90;font-size:11px;margin-bottom:12px">' + d.warnings.map(esc).join('<br>') + '</div>';
  }
  if (ovSec)    html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>' + kvTable(ovSec);
  if (enumSec)  html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">' + esc(enumSec.title) + '</h3>' + chipList(enumSec);
  if (transSec) html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">' + esc(transSec.title) + '</h3>' + itemList(transSec);
  if (evtSec)   html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">' + esc(evtSec.title) + '</h3>' + itemList(evtSec);
  detail.innerHTML = html;
}

// The global shell's ENV selector (app.js) calls window.onEnvChange(v) when
// present and always dispatches a 'deathstar:envchange' event -- this page
// only read ENV_VAL() lazily per-request but never re-ran the load, so
// switching environments silently left the prior env's data on screen.
window.onEnvChange = doSearch;
document.addEventListener('deathstar:envchange', doSearch);

doSearch();
</script>""")


@router.get("/pmtrans", response_class=HTMLResponse)
def admin_pmtrans():
    return _shell("PM Transactions Explorer", "pmtrans", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#bb99ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #bb99ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #bb99ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #bb99ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#100d1a;color:#d7faff;border:1px solid #bb99ff44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#bb99ff}
button{background:#bb99ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(187,153,255,.07);border-left-color:#bb99ff55}
.item.sel{background:rgba(187,153,255,.12);border-left-color:#bb99ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.muted{color:#556;font-style:italic}
.badge{display:inline-block;padding:1px 5px;border-radius:2px;font-size:10px;font-family:monospace;
       background:#1a0d2a;border:1px solid #bb99ff44;color:#bb99ff;margin-left:4px}
</style>
<div class="topbar">
  <input id="q" type="text" placeholder="Search transaction label or description..." style="width:300px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>PM Transactions</h2>
    <div id="list" class="muted">Search to load transactions.</div>
  </div>
  <div class="content">
    <h2>Selected Transaction</h2>
    <div id="detail" class="muted">Select a transaction from the list.</div>
  </div>
</div>
<script>
function ENV_VAL() { return window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HCM'); }
let _rows = [];
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
const FILTER_LABELS = {'01':'Minimal','04':'Standard','05':'Detailed','06':'Diagnostic'};

async function doSearch() {
  const q = document.getElementById('q').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV_VAL(), limit: 100});
  if (q) params.set('q', q);
  const d = await api('/api/peoplesoft/pm-transactions?' + params);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  _rows = Array.isArray(d) ? d : (d.items || []);
  document.getElementById('stats').textContent = _rows.length + ' result' + (_rows.length !== 1 ? 's' : '');
  if (!_rows.length) { list.innerHTML = '<div class="muted">No transactions found.</div>'; return; }
  list.innerHTML = _rows.map(function(r, i) {
    const fl = FILTER_LABELS[String(r.pm_filter_level)] || r.pm_filter_level;
    return '<div class="item" id="tr-' + i + '" data-idx="' + i + '">' +
      '<div class="item-name">' + esc(r.pm_trans_label) +
        '<span class="badge">' + esc(fl) + '</span></div>' +
      '<div class="item-meta">ID ' + esc(String(r.pm_trans_defn_id)) +
        (r.descr60 && r.descr60 !== r.pm_trans_label ? ' \u00b7 ' + esc((r.descr60||'').slice(0,50)) : '') + '</div>' +
      '</div>';
  }).join('');
  list.querySelectorAll('.item').forEach(function(el) {
    el.addEventListener('click', function() { selectTrans(+el.dataset.idx); });
  });
}

async function selectTrans(idx) {
  const r = _rows[idx];
  if (!r) return;
  document.querySelectorAll('.item').forEach(function(el) { el.classList.remove('sel'); });
  const el = document.getElementById('tr-' + idx);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api('/api/peoplesoft/object/pm_transaction/' + encodeURIComponent(String(r.pm_trans_defn_id)) + '?env=' + ENV_VAL());
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const sections = d.sections || [];
  const ovSec   = sections.find(function(s) { return s.title && s.title.indexOf('Overview') >= 0; });
  const ctxSec  = sections.find(function(s) { return s.title && s.title.indexOf('Context') >= 0; });
  const metSec  = sections.find(function(s) { return s.title && s.title.indexOf('Metric') >= 0; });

  function kvTable(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">' +
      sec.items.map(function(item) {
        return '<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap">' + esc(item.label) + '</td>' +
          '<td style="padding:4px 0;color:#c8d8e8;font-family:monospace">' + esc(String(item.value||'')) + '</td></tr>';
      }).join('') + '</table>';
  }

  function slotList(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<div style="margin-bottom:16px">' +
      sec.items.map(function(it) {
        return '<div style="padding:4px 0;border-bottom:1px solid #1a0d2a;font-size:12px;display:flex;gap:8px">' +
          '<span style="color:#776;min-width:24px;font-family:monospace">' + esc(it.label) + '</span>' +
          '<span style="color:#c8d8e8">' + esc(it.value||'') + '</span>' +
          (it.id ? '<span style="color:#445;font-size:10px">ID:' + esc(it.id) + '</span>' : '') +
          '</div>';
      }).join('') + '</div>';
  }

  const ov = d.overview || {};
  let html = '<h2 style="font-family:monospace;color:#bb99ff;font-size:14px;margin:0 0 4px">' + esc(r.pm_trans_label) + '</h2>' +
    '<div style="font-size:12px;color:#556;margin-bottom:16px">Transaction ID: ' + esc(String(r.pm_trans_defn_id)) +
    (ov.filter_label ? ' \u00b7 ' + esc(ov.filter_label) : '') +
    (ov.sampling ? ' \u00b7 Sampling' : '') + '</div>';
  if (d.warnings && d.warnings.length) {
    html += '<div style="color:#f90;font-size:11px;margin-bottom:12px">' + d.warnings.map(esc).join('<br>') + '</div>';
  }
  if (ovSec)  html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>' + kvTable(ovSec);
  if (ctxSec) html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">' + esc(ctxSec.title) + '</h3>' + slotList(ctxSec);
  if (metSec) html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">' + esc(metSec.title) + '</h3>' + slotList(metSec);
  detail.innerHTML = html;
}

// The global shell's ENV selector (app.js) calls window.onEnvChange(v) when
// present and always dispatches a 'deathstar:envchange' event -- this page
// only read ENV_VAL() lazily per-request but never re-ran the load, so
// switching environments silently left the prior env's data on screen.
window.onEnvChange = doSearch;
document.addEventListener('deathstar:envchange', doSearch);

doSearch();
</script>""")


@router.get("/pmevent", response_class=HTMLResponse)
def admin_pmevent():
    return _shell("PM Events Explorer", "pmevent", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#8877ee;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #8877ee33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #8877ee22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #8877ee22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0d0d18;color:#d7faff;border:1px solid #8877ee44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#8877ee}
button{background:#8877ee;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#fff;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(136,119,238,.07);border-left-color:#8877ee55}
.item.sel{background:rgba(136,119,238,.12);border-left-color:#8877ee}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.muted{color:#556;font-style:italic}
.badge{display:inline-block;padding:1px 5px;border-radius:2px;font-size:10px;font-family:monospace;
       background:#0d0d1a;border:1px solid #8877ee44;color:#8877ee;margin-left:4px}
</style>
<div class="topbar">
  <input id="q" type="text" placeholder="Search event label or description..." style="width:300px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>PM Events</h2>
    <div id="list" class="muted">Search to load events.</div>
  </div>
  <div class="content">
    <h2>Selected Event</h2>
    <div id="detail" class="muted">Select an event from the list.</div>
  </div>
</div>
<script>
function ENV_VAL() { return window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HCM'); }
let _rows = [];
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
const FILTER_LABELS = {'01':'Minimal','04':'Standard','05':'Detailed','06':'Diagnostic'};

async function doSearch() {
  const q = document.getElementById('q').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV_VAL(), limit: 50});
  if (q) params.set('q', q);
  const d = await api('/api/peoplesoft/pm-events?' + params);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  _rows = Array.isArray(d) ? d : (d.items || []);
  document.getElementById('stats').textContent = _rows.length + ' result' + (_rows.length !== 1 ? 's' : '');
  if (!_rows.length) { list.innerHTML = '<div class="muted">No events found.</div>'; return; }
  list.innerHTML = _rows.map(function(r, i) {
    const fl = FILTER_LABELS[String(r.pm_filter_level)] || r.pm_filter_level;
    return '<div class="item" id="ev-' + i + '" data-idx="' + i + '">' +
      '<div class="item-name">' + esc(r.pm_event_label) +
        '<span class="badge">' + esc(fl) + '</span></div>' +
      '<div class="item-meta">ID ' + esc(String(r.pm_event_defn_id)) +
        (r.descr60 && r.descr60 !== r.pm_event_label ? ' \u00b7 ' + esc((r.descr60||'').slice(0,50)) : '') + '</div>' +
      '</div>';
  }).join('');
  list.querySelectorAll('.item').forEach(function(el) {
    el.addEventListener('click', function() { selectEvent(+el.dataset.idx); });
  });
}

async function selectEvent(idx) {
  const r = _rows[idx];
  if (!r) return;
  document.querySelectorAll('.item').forEach(function(el) { el.classList.remove('sel'); });
  const el = document.getElementById('ev-' + idx);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api('/api/peoplesoft/object/pm_event/' + encodeURIComponent(String(r.pm_event_defn_id)) + '?env=' + ENV_VAL());
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const sections = d.sections || [];
  const ovSec  = sections.find(function(s) { return s.title && s.title.indexOf('Overview') >= 0; });
  const metSec = sections.find(function(s) { return s.title && s.title.indexOf('Metric') >= 0; });

  function kvTable(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">' +
      sec.items.map(function(item) {
        return '<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap">' + esc(item.label) + '</td>' +
          '<td style="padding:4px 0;color:#c8d8e8;font-family:monospace">' + esc(String(item.value||'')) + '</td></tr>';
      }).join('') + '</table>';
  }

  function slotList(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<div style="margin-bottom:16px">' +
      sec.items.map(function(it) {
        return '<div style="padding:4px 0;border-bottom:1px solid #0d0d1a;font-size:12px;display:flex;gap:8px">' +
          '<span style="color:#776;min-width:24px;font-family:monospace">' + esc(it.label) + '</span>' +
          '<span style="color:#c8d8e8">' + esc(it.value||'') + '</span>' +
          (it.id ? '<span style="color:#445;font-size:10px">ID:' + esc(it.id) + '</span>' : '') +
          '</div>';
      }).join('') + '</div>';
  }

  const ov = d.overview || {};
  let html = '<h2 style="font-family:monospace;color:#8877ee;font-size:14px;margin:0 0 4px">' + esc(r.pm_event_label) + '</h2>' +
    '<div style="font-size:12px;color:#556;margin-bottom:16px">Event ID: ' + esc(String(r.pm_event_defn_id)) +
    (ov.filter_label ? ' \u00b7 ' + esc(ov.filter_label) : '') + '</div>';
  if (d.warnings && d.warnings.length) {
    html += '<div style="color:#f90;font-size:11px;margin-bottom:12px">' + d.warnings.map(esc).join('<br>') + '</div>';
  }
  if (ovSec)  html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>' + kvTable(ovSec);
  if (metSec) html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">' + esc(metSec.title) + '</h3>' + slotList(metSec);
  detail.innerHTML = html;
}

// The global shell's ENV selector (app.js) calls window.onEnvChange(v) when
// present and always dispatches a 'deathstar:envchange' event -- this page
// only read ENV_VAL() lazily per-request but never re-ran the load, so
// switching environments silently left the prior env's data on screen.
window.onEnvChange = doSearch;
document.addEventListener('deathstar:envchange', doSearch);

doSearch();
</script>""")




