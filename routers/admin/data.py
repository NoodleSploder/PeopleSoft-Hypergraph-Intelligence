import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

@router.get("/sqlws", response_class=HTMLResponse)
def admin_sqlws():
    return _shell("SQL Workspace", "sqlws", noscroll=True, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;height:100vh;display:flex;flex-direction:column;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;
   border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px;}
nav{font-size:12px;color:#445;}
nav a{color:#00e5ff;text-decoration:none;} nav a:hover{text-decoration:underline;}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:16px;flex-wrap:wrap;}
.main{display:flex;flex:1;overflow:hidden;}
.sidebar{width:280px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0;}
.editor-area{flex:1;display:flex;flex-direction:column;overflow:hidden;}
.editor-panel{padding:12px;border-bottom:1px solid #00e5ff22;}
.results-panel{flex:1;overflow:auto;padding:12px;}
select,input[type=text],input[type=number]{background:#0b1b24;color:#d7faff;
  border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
select:focus,input:focus{outline:none;border-color:#00e5ff;}
textarea{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;
  font-family:monospace;font-size:12px;padding:8px;width:100%;resize:vertical;}
textarea:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button:hover{background:#33eeff;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
button.sec:hover{border-color:#00e5ff;background:#00e5ff11;}
button.danger{background:#ff4444;color:#fff;}
button.danger:hover{background:#ff6666;}
button.warn{background:#ffaa00;color:#000;}
.btn-row{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:8px;}
.ctrl-row{display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;margin-top:8px;}
.lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:3px;}
.chip{display:inline-block;padding:2px 8px;border-radius:2px;font-size:11px;font-weight:bold;}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.chip-err{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.chip-block{background:#3a0000;border:1px solid #ff6600;color:#ff6600;}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
table{border-collapse:collapse;width:100%;font-size:11px;margin-top:4px;}
th{border-bottom:1px solid #00e5ff33;padding:4px 8px;text-align:left;color:#00e5ff;
   font-size:10px;text-transform:uppercase;letter-spacing:1px;white-space:nowrap;position:sticky;top:0;background:#050b12;}
td{border-bottom:1px solid #0e2030;padding:4px 8px;vertical-align:top;max-width:320px;
   overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
td.wrap{white-space:normal;word-break:break-all;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;font-size:11px;}
.empty{color:#445;font-style:italic;font-size:12px;padding:8px 0;}
.warn-msg{color:#ffaa00;font-size:11px;margin:2px 0;}
.err-msg{color:#ff6666;font-size:11px;margin:2px 0;}
.ok-msg{color:#00cc66;font-size:11px;margin:2px 0;}
.ts{font-size:10px;color:#446;}
.timing{font-size:11px;color:#667;margin:4px 0;}
.section-toggle{cursor:pointer;user-select:none;}
.section-toggle:hover{color:#00e5ff;}
.sql-preview{font-family:monospace;font-size:10px;color:#6ab;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;display:block;}
.pin-btn{font-size:10px;padding:1px 5px;}
.pagination{display:flex;gap:6px;align-items:center;margin-top:8px;}
.col-type{color:#445;font-size:10px;}
.schema-item{padding:4px 6px;cursor:pointer;border-radius:2px;font-size:11px;
  display:flex;justify-content:space-between;align-items:center;}
.schema-item:hover{background:#0b2030;}
.schema-item .obj-type{font-size:9px;color:#445;text-transform:uppercase;}
.schema-cols{display:none;padding:4px 0 4px 16px;}
.schema-cols.open{display:block;}
.schema-col{font-size:10px;color:#778;padding:1px 4px;font-family:monospace;}
.tab-row{display:flex;gap:0;border-bottom:1px solid #00e5ff22;margin:8px 0 0;}
.tab{padding:5px 12px;cursor:pointer;font-size:11px;color:#556;
     border-bottom:2px solid transparent;margin-bottom:-1px;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.pane{display:none;} .pane.on{display:block;}
.bind-row{display:flex;gap:3px;align-items:center;margin-bottom:3px;}
.bnd-name{width:72px;font-family:monospace;font-size:11px;padding:2px 4px;
  background:#050b12;color:#9ab;border:1px solid #00e5ff33;}
.bnd-val{flex:1;min-width:0;font-family:monospace;font-size:11px;padding:2px 4px;
  background:#050b12;color:#d7faff;border:1px solid #00e5ff33;}
.bnd-rm{background:transparent;border:none;color:#445;cursor:pointer;padding:0 3px;font-size:13px;line-height:1;}
.bnd-rm:hover{color:#ff4444;}
#sqlAC{position:fixed;z-index:9999;background:#0b1b24;border:1px solid #00e5ff55;
  min-width:260px;max-width:480px;max-height:220px;overflow-y:auto;display:none;
  box-shadow:0 4px 16px #000a;}
.ac-item{padding:4px 10px;cursor:pointer;display:flex;justify-content:space-between;
  align-items:center;gap:8px;font-size:11px;}
.ac-item:hover,.ac-item.ac-sel{background:#0e2a3a;}
.ac-label{font-family:monospace;color:#d7faff;}
.ac-detail{color:#445;font-size:10px;text-align:right;}
.ac-type-col{color:#00e5ff44;font-size:9px;text-transform:uppercase;}
</style>

<div class="main">

<!-- ═══════════════════════════════════════════════════════ SIDEBAR ═══ -->
<div class="sidebar">

  <div class="tab-row">
    <div class="tab on" onclick="showTab('schema')">Schema</div>
    <div class="tab"    onclick="showTab('history')">History</div>
    <div class="tab"    onclick="showTab('pinned')">Pinned</div>
  </div>

  <!-- Schema browser -->
  <div id="pane-schema" class="pane on">
    <h2>Schema Browser</h2>
    <div style="display:flex;gap:4px;margin-bottom:4px;">
      <input id="schemaQ" type="text" placeholder="Search tables/records…" style="flex:1;" onkeydown="if(event.key==='Enter')searchSchema()">
      <button onclick="searchSchema()">Go</button>
    </div>
    <div style="display:flex;gap:4px;margin-bottom:8px;">
      <button class="sec" style="font-size:9px;padding:2px 6px;" onclick="schemaPrefix('')">All</button>
      <button class="sec" style="font-size:9px;padding:2px 6px;" onclick="schemaPrefix('PS_')">PS_</button>
      <button class="sec" style="font-size:9px;padding:2px 6px;" onclick="schemaPrefix('SYSADM.')">SYSADM.</button>
    </div>
    <div id="schemaResults"><span class="empty">Type to search</span></div>
  </div>

  <!-- History -->
  <div id="pane-history" class="pane">
    <div style="display:flex;align-items:center;gap:4px;margin-bottom:6px;">
      <h2 style="margin:0;flex:1;">Query History</h2>
      <button class="sec" style="font-size:9px;padding:2px 6px;" onclick="loadHistory()">Refresh</button>
    </div>
    <input id="historyQ" type="text" placeholder="Filter by SQL or env…" style="width:100%;margin-bottom:6px;" oninput="applyHistoryFilter()">
    <div id="historyList"><span class="empty">Loading…</span></div>
  </div>

  <!-- Pinned -->
  <div id="pane-pinned" class="pane">
    <h2>Pinned Queries <button class="sec" style="font-size:9px;padding:2px 6px;" onclick="loadPinned()">Refresh</button></h2>
    <div id="pinnedList"><span class="empty">No pinned queries</span></div>
  </div>

</div>
<!-- ══════════════════════════════════════════════════ EDITOR AREA ════ -->
<div class="editor-area">

  <div class="editor-panel">
    <div style="display:flex;gap:8px;align-items:flex-start;">
      <div style="flex:1;">
        <label class="lbl">SQL Query <span style="color:#445;font-size:9px;font-weight:normal;">Ctrl+Space to autocomplete</span></label>
        <textarea id="sqlInput" rows="8" placeholder="SELECT * FROM SYSADM.PSOPRDEFN FETCH FIRST 10 ROWS ONLY"></textarea>
      </div>
      <div id="sqlAC"></div>
      <div style="width:200px;display:flex;flex-direction:column;">
        <label class="lbl">Bind Parameters
          <button class="sec" onclick="addBind()" style="font-size:9px;padding:1px 5px;margin-left:4px;">+ Add</button>
          <button class="sec" onclick="clearBinds()" style="font-size:9px;padding:1px 5px;margin-left:2px;">Clear</button>
        </label>
        <div id="bindsEditor" style="flex:1;overflow-y:auto;min-height:60px;max-height:160px;
          border:1px solid #00e5ff44;padding:4px 6px;background:#0b1b24;"></div>
        <div class="muted" id="bindsHint" style="font-size:9px;color:#445;padding:2px 0;">
          Bind vars from SQL e.g. :oprid → "oprid"
        </div>
      </div>
    </div>

    <div class="ctrl-row">
      <div>
        <label class="lbl">Page</label>
        <input id="pageInput" type="number" value="1" min="1" style="width:60px;">
      </div>
      <div>
        <label class="lbl">Page Size</label>
        <input id="pageSizeInput" type="number" value="100" min="1" max="1000" style="width:70px;">
      </div>
      <div>
        <label class="lbl">Timeout (s)</label>
        <input id="timeoutInput" type="number" value="30" min="0" max="600" style="width:78px;">
      </div>
    </div>

    <div class="btn-row">
      <button id="validateBtn" onclick="validateSQL()">Validate</button>
      <button id="execBtn" onclick="executeSQL()">Execute</button>
      <button id="cancelBtn" class="sec" onclick="cancelSQL()" style="display:none;">&#9632; Cancel</button>
      <button id="explainBtn" class="sec" onclick="explainSQL()">Explain Plan</button>
      <button id="exportCsvBtn" class="sec" onclick="exportCSV()">Export CSV</button>
      <button id="exportJsonBtn" class="sec" onclick="exportJSON()">Export JSON</button>
      <button id="clearBtn" class="sec" onclick="clearResults()">Clear</button>
    </div>

    <div id="validationBox" style="margin-top:8px;display:none;"></div>
  </div>

  <div class="results-panel">
    <div id="timingBox" style="display:none;" class="timing"></div>
    <div id="warningBox"></div>
    <div id="resultsBox"></div>
    <div id="paginationBox" class="pagination" style="display:none;">
      <button class="sec" onclick="prevPage()" id="prevBtn">&#8592; Prev</button>
      <span id="pageLabel" style="font-size:11px;color:#667;"></span>
      <button class="sec" onclick="nextPage()" id="nextBtn">Next &#8594;</button>
    </div>
  </div>

</div>
</div>

<script>
// ── state ──────────────────────────────────────────────────────────────
let lastSQL   = '';
let lastBinds = {};
let currentPage = 1;
let lastPageSize = 100;
let lastResult = null;

// ── helpers ────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

function env()      { return (window.dsGetEnv && window.dsGetEnv()) || 'HCM'; }
function sqlText()  { return $('sqlInput').value.trim(); }
function bindsObj() {
  const obj = {};
  document.querySelectorAll('#bindsEditor .bind-row').forEach(row => {
    const name = row.querySelector('.bnd-name').value.trim().replace(/^:/, '');
    const val  = row.querySelector('.bnd-val').value;
    if (name) obj[name] = val;
  });
  return obj;
}

function addBind(name, val) {
  const ed  = $('bindsEditor');
  const row = document.createElement('div');
  row.className = 'bind-row';
  row.innerHTML = `<input class="bnd-name" placeholder="name" value="${esc(name||'')}">` +
                  `<input class="bnd-val"  placeholder="value" value="${esc(val!=null?val:'')}">` +
                  `<button class="bnd-rm" onclick="this.parentElement.remove()" title="Remove">×</button>`;
  ed.appendChild(row);
  row.querySelector('.bnd-name').focus();
}

function clearBinds() {
  $('bindsEditor').innerHTML = '';
}

function setBinds(obj) {
  clearBinds();
  Object.entries(obj || {}).forEach(([k,v]) => addBind(k, v));
}

function showTab(name) {
  ['schema','history','pinned'].forEach(t => {
    document.querySelectorAll('.tab').forEach((el,i) => {
      if (['schema','history','pinned'][i] === t)
        el.classList.toggle('on', t === name);
    });
    $(`pane-${t}`).classList.toggle('on', t === name);
  });
  if (name === 'history') loadHistory();
  if (name === 'pinned')  loadPinned();
}

// tab selection uses index — re-wire correctly
document.querySelectorAll('.tab').forEach((el, i) => {
  const names = ['schema','history','pinned'];
  el.onclick = () => showTab(names[i]);
});

async function api(path, options={}) {
  const res = await fetch(path, options);
  if (res.status === 401) { window.location.reload(); return; }
  return res;
}

function setValidationBox(result) {
  const box = $('validationBox');
  box.style.display = 'block';
  if (result.allowed) {
    box.innerHTML = `<span class="chip chip-ok">&#10003; Allowed — ${esc(result.statement_type)}</span>`;
  } else {
    box.innerHTML = `<span class="chip chip-block">&#10007; Blocked — ${esc(result.blocked_reason)}</span>`;
  }
  (result.warnings || []).forEach(w => {
    box.innerHTML += `<div class="warn-msg">&#9888; ${esc(w)}</div>`;
  });
}

function setWarnings(warnings, errors) {
  const box = $('warningBox');
  box.innerHTML = '';
  (warnings || []).forEach(w => {
    box.innerHTML += `<div class="warn-msg">&#9888; ${esc(w)}</div>`;
  });
  (errors || []).forEach(e => {
    box.innerHTML += `<div class="err-msg">&#10007; ${esc(e)}</div>`;
  });
}

function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

function clearResults() {
  $('resultsBox').innerHTML = '';
  $('timingBox').style.display = 'none';
  $('warningBox').innerHTML = '';
  $('validationBox').style.display = 'none';
  $('paginationBox').style.display = 'none';
}

// ── validate ───────────────────────────────────────────────────────────
async function validateSQL() {
  const sql = sqlText();
  if (!sql) { alert('Enter a SQL query first.'); return; }
  const res = await api('/api/sqlws/validate', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({sql}),
  });
  const data = await res.json();
  setValidationBox(data);
  $('warningBox').innerHTML = '';
}

// ── execute ────────────────────────────────────────────────────────────
let currentAbortController = null;

function _setExecRunning(running) {
  const buttons = ['validateBtn','execBtn','explainBtn','exportCsvBtn','exportJsonBtn','clearBtn'];
  buttons.forEach(id => { const el = $(id); if (el) el.disabled = running; });
  $('execBtn').disabled = running;
  $('cancelBtn').style.display = running ? 'inline-block' : 'none';
}

function getTimeoutSecs() {
  const raw = parseInt($('timeoutInput').value, 10);
  if (!Number.isFinite(raw)) return 0;
  return Math.max(0, Math.min(raw, 600));
}

function cancelSQL() {
  if (currentAbortController) {
    currentAbortController.abort();
    currentAbortController = null;
  }
}

async function executeSQL(page) {
  const sql = sqlText();
  if (!sql) { alert('Enter a SQL query first.'); return; }
  const binds      = bindsObj();
  const pageSize   = parseInt($('pageSizeInput').value) || 100;
  const timeoutSecs = getTimeoutSecs();
  page = page || parseInt($('pageInput').value) || 1;

  lastSQL = sql; lastBinds = binds; lastPageSize = pageSize; currentPage = page;
  $('pageInput').value = page;

  currentAbortController = new AbortController();
  _setExecRunning(true);

  let data;
  try {
    const res = await api('/api/sqlws/execute', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({env:env(), sql, binds, page, page_size:pageSize, timeout_secs:timeoutSecs}),
      signal: currentAbortController.signal,
    });
    if (!res.ok) {
      const text = await res.text();
      let msg = text;
      try {
        const errData = JSON.parse(text);
        msg = errData.error || (errData.warnings || []).join('; ') || text;
      } catch(e) {}
      throw new Error(msg || `HTTP ${res.status}`);
    }
    data = await res.json();
  } catch (e) {
    _setExecRunning(false);
    if (e.name === 'AbortError') {
      $('timingBox').style.display = 'block';
      $('timingBox').textContent = 'Query cancelled by user.';
      setWarnings([], ['Query cancelled by user.']);
      $('resultsBox').innerHTML = '<div class="empty">Execution cancelled.</div>';
      $('paginationBox').style.display = 'none';
    } else {
      setWarnings([], [`Request failed: ${e.message}`]);
    }
    return;
  } finally {
    currentAbortController = null;
  }
  _setExecRunning(false);
  lastResult = data;

  setValidationBox({
    allowed: !data.blocked,
    statement_type: data.statement_type,
    warnings: data.warnings || [],
    blocked_reason: data.blocked_reason,
  });

  const warns = (data.warnings || []).filter(w => !w.startsWith('Execution'));
  const errs  = data.error ? [data.error] : [];
  setWarnings(warns, errs);

  const timing = $('timingBox');
  timing.style.display = 'block';
  const statusSuffix = data.timed_out ? ' — TIMED OUT' : (data.cancelled ? ' — CANCELLED' : '');
  timing.textContent = `${data.row_count} rows · ${data.elapsed_ms} ms · Page ${data.page}${data.truncated ? ' (more rows available)' : ''}${statusSuffix}`;

  renderTable(data);
  renderPagination(data);
  loadHistory();
}

function renderTable(data) {
  const box = $('resultsBox');
  if (data.blocked) {
    box.innerHTML = `<div class="err-msg">&#10007; ${esc(data.blocked_reason)}</div>`;
    return;
  }
  if (!data.columns || data.columns.length === 0) {
    box.innerHTML = '<div class="empty">No columns returned.</div>';
    return;
  }
  if (data.rows.length === 0) {
    box.innerHTML = '<div class="empty">No rows returned.</div>';
    return;
  }

  let html = '<div style="overflow-x:auto;"><table><thead><tr>';
  data.columns.forEach(c => {
    html += `<th>${esc(c.name)}<br><span class="col-type">${esc(c.type)}</span></th>`;
  });
  html += '</tr></thead><tbody>';

  data.rows.forEach(row => {
    html += '<tr>';
    data.columns.forEach(c => {
      const v = row[c.name];
      const display = v === null ? '<span style="color:#334">NULL</span>' : esc(String(v));
      html += `<td class="mono">${display}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  box.innerHTML = html;
}

function renderPagination(data) {
  const box = $('paginationBox');
  if (!data.columns || data.columns.length === 0 || data.row_count === 0) {
    box.style.display = 'none';
    return;
  }
  box.style.display = 'flex';
  $('pageLabel').textContent = `Page ${data.page}${data.truncated ? '+' : ''}`;
  $('prevBtn').disabled = data.page <= 1;
  $('nextBtn').disabled = !data.truncated;
}

function prevPage() {
  if (currentPage > 1) executeSQL(currentPage - 1);
}
function nextPage() {
  executeSQL(currentPage + 1);
}

// ── explain ─────────────────────────────────────────────────────────────
async function explainSQL() {
  const sql = sqlText();
  if (!sql) { alert('Enter a SQL query first.'); return; }
  const binds = bindsObj();

  const res = await api('/api/sqlws/explain', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({env:env(), sql, binds}),
  });
  const data = await res.json();

  const warns = data.warnings || [];
  setWarnings(warns, []);

  const box = $('resultsBox');
  if (!data.allowed) {
    box.innerHTML = `<div class="err-msg">&#10007; ${esc(data.blocked_reason)}</div>`;
    return;
  }
  if (!data.plan || data.plan.length === 0) {
    box.innerHTML = '<div class="empty">No plan returned. ' + esc(warns.join(' ')) + '</div>';
    return;
  }

  let html = '<pre style="font-family:monospace;font-size:11px;color:#9ab;background:#0b1b24;padding:12px;overflow-x:auto;">';
  data.plan.forEach(line => { html += esc(line) + '\\n'; });
  html += '</pre>';
  $('timingBox').style.display = 'block';
  $('timingBox').textContent = `EXPLAIN PLAN · ${data.elapsed_ms} ms`;
  box.innerHTML = html;
  $('paginationBox').style.display = 'none';
}

// ── export ──────────────────────────────────────────────────────────────
async function exportCSV() {
  const sql = sqlText();
  if (!sql) { alert('Enter a SQL query first.'); return; }
  const body = JSON.stringify({env:env(), sql, binds:bindsObj(), page_size:1000});
  const res = await api('/api/sqlws/export/csv', {
    method:'POST', headers:{'Content-Type':'application/json'}, body
  });
  if (!res || !res.ok) { alert('Export failed'); return; }
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'sqlws_export.csv';
  a.click();
}

async function exportJSON() {
  const sql = sqlText();
  if (!sql) { alert('Enter a SQL query first.'); return; }
  const body = JSON.stringify({env:env(), sql, binds:bindsObj(), page_size:1000});
  const res = await api('/api/sqlws/export/json', {
    method:'POST', headers:{'Content-Type':'application/json'}, body
  });
  if (!res || !res.ok) { alert('Export failed'); return; }
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'sqlws_export.json';
  a.click();
}

// ── schema browser ─────────────────────────────────────────────────────
function schemaPrefix(p) {
  $('schemaQ').value = p;
  if (p) searchSchema();
  else $('schemaResults').innerHTML = '<span class="empty">Type to search</span>';
}

async function searchSchema() {
  const q = $('schemaQ').value.trim();
  if (!q) return;
  $('schemaResults').innerHTML = '<span class="empty">Searching…</span>';
  const res  = await api(`/api/sqlws/schema/search?env=${encodeURIComponent(env())}&q=${encodeURIComponent(q)}`);
  const data = await res.json();
  renderSchemaResults(data.results || [], data.warnings || []);
}

function renderSchemaResults(results, warnings) {
  const box = $('schemaResults');
  if (!results.length) { box.innerHTML = '<span class="empty">No results.</span>'; return; }

  let html = '';
  warnings.forEach(w => { html += `<div class="warn-msg">${esc(w)}</div>`; });

  results.forEach(obj => {
    const id = `sc_${btoa(obj.owner + '.' + obj.object_name).replace(/[^a-zA-Z0-9]/g,'')}`;
    const badge = obj.source === 'peoplesoft'
      ? `<span class="obj-type" style="color:#00cc66;">PS</span>`
      : `<span class="obj-type">${esc(obj.object_type)}</span>`;
    const link = obj.ps_recname
      ? `<a href="/admin/object/record/${esc(obj.ps_recname)}" style="color:#00e5ff;font-size:9px;" target="_blank">&#8599;</a>`
      : '';
    html += `
      <div class="schema-item" onclick="toggleSchemaItem('${id}','${esc(obj.owner)}','${esc(obj.object_name)}')">
        <span>
          <span style="font-family:monospace;">${esc(obj.owner)}.${esc(obj.object_name)}</span>
          ${link}
          ${obj.description ? `<br><span style="font-size:9px;color:#556;">${esc(obj.description)}</span>` : ''}
        </span>
        ${badge}
      </div>
      <div id="${id}" class="schema-cols"></div>`;
  });
  box.innerHTML = html;
}

async function toggleSchemaItem(id, owner, objName) {
  const el = document.getElementById(id);
  if (el.classList.contains('open')) { el.classList.remove('open'); return; }
  el.classList.add('open');
  el.innerHTML = '<span class="schema-col">Loading columns…</span>';
  const res  = await api(`/api/sqlws/schema/${encodeURIComponent(owner)}/${encodeURIComponent(objName)}/columns?env=${encodeURIComponent(env())}`);
  const data = await res.json();
  if (!data.columns || !data.columns.length) {
    el.innerHTML = '<span class="schema-col empty">No columns found.</span>';
    return;
  }
  el.innerHTML = data.columns.map(c =>
    `<div class="schema-col" onclick="insertColumnRef('${esc(owner)}.${esc(objName)}','${esc(c.column_name)}')" style="cursor:pointer;" title="Click to insert">
       <span style="color:#9ab;">${esc(c.column_name)}</span>
       <span style="color:#445;"> ${esc(c.data_type)}</span>
     </div>`
  ).join('');
}

function insertColumnRef(table, col) {
  const ta = $('sqlInput');
  const sel = ta.selectionStart;
  const txt = ta.value;
  ta.value = txt.slice(0, sel) + col + txt.slice(ta.selectionEnd);
  ta.focus();
  ta.selectionStart = ta.selectionEnd = sel + col.length;
}

// ── SQL Autocomplete ────────────────────────────────────────────────────
let _acItems = [];
let _acSel   = -1;
let _acTimer = null;
const _acColCache = {};

function _tokenBeforeCursor() {
  const ta  = $('sqlInput');
  const txt = ta.value.slice(0, ta.selectionStart);
  const m   = txt.match(/[\\w.]+$/);
  return m ? m[0] : '';
}

function _extractAliases(sql) {
  const map = {};
  const re = /(?:FROM|JOIN)\\s+(?:SYSADM\\.)?(\\w+)\\s+(?:AS\\s+)?(\\w+)/gi;
  let m;
  const KEYWORDS = new Set(['WHERE','ON','INNER','LEFT','RIGHT','OUTER','CROSS','FULL','FETCH','ORDER','GROUP','HAVING','SET','AND','OR']);
  while ((m = re.exec(sql)) !== null) {
    const tbl   = m[1].toUpperCase();
    const alias = m[2].toUpperCase();
    if (!KEYWORDS.has(alias)) {
      map[alias] = tbl;
      map[tbl]   = tbl;
    }
  }
  return map;
}

function _acContext() {
  const tok = _tokenBeforeCursor();
  if (!tok) return null;
  if (tok.includes('.')) {
    const dot  = tok.lastIndexOf('.');
    const pre  = tok.slice(0, dot);
    const suf  = tok.slice(dot + 1);
    const owner = pre.includes('.') ? pre.split('.').pop() : pre;
    return { type: 'column', qualifier: owner, prefix: suf, replaceLen: suf.length };
  }
  if (tok.length >= 2) return { type: 'table', prefix: tok, replaceLen: tok.length };
  return null;
}

async function _fetchAC(ctx) {
  if (!ctx) return [];
  if (ctx.type === 'table') {
    try {
      const res  = await fetch(`/api/sqlws/schema/search?env=${encodeURIComponent(env())}&q=${encodeURIComponent(ctx.prefix)}`);
      const data = await res.json();
      return (data.results || []).slice(0, 12).map(r => ({
        label: r.object_name,
        insert: r.object_name,
        detail: r.description || (r.source === 'peoplesoft' ? 'PS' : (r.object_type || '')),
      }));
    } catch(e) { return []; }
  }
  if (ctx.type === 'column') {
    const aliases = _extractAliases($('sqlInput').value);
    const tblName = aliases[ctx.qualifier.toUpperCase()] || ctx.qualifier.toUpperCase();
    const cacheKey = `${env()}|${tblName}`;
    if (!_acColCache[cacheKey]) {
      try {
        const res  = await fetch(`/api/sqlws/schema/SYSADM/${encodeURIComponent(tblName)}/columns?env=${encodeURIComponent(env())}`);
        const data = await res.json();
        _acColCache[cacheKey] = data.columns || [];
      } catch(e) { _acColCache[cacheKey] = []; }
    }
    const cols = _acColCache[cacheKey];
    const pfx  = ctx.prefix.toUpperCase();
    return cols
      .filter(c => !pfx || c.column_name.toUpperCase().startsWith(pfx))
      .slice(0, 16)
      .map(c => ({ label: c.column_name, insert: c.column_name, detail: c.data_type || '' }));
  }
  return [];
}

function _showAC(items, replaceLen) {
  const box = $('sqlAC');
  if (!items.length) { _hideAC(); return; }
  _acItems = items;
  _acSel   = -1;
  box.innerHTML = items.map((it, i) =>
    `<div class="ac-item" data-i="${i}" onmousedown="event.preventDefault();_acCommit(${i})">
      <span class="ac-label">${esc(it.label)}</span>
      <span class="ac-detail">${esc(it.detail)}</span>
    </div>`
  ).join('');
  const ta  = $('sqlInput');
  const r   = ta.getBoundingClientRect();
  box.style.left = r.left + 'px';
  box.style.top  = (r.bottom + 2) + 'px';
  box.style.display = 'block';
  box._replaceLen = replaceLen;
}

function _hideAC() {
  $('sqlAC').style.display = 'none';
  _acItems = [];
  _acSel   = -1;
}

function _acRenderSel() {
  document.querySelectorAll('#sqlAC .ac-item').forEach((el, i) => {
    el.classList.toggle('ac-sel', i === _acSel);
  });
}

function _acCommit(i) {
  const item = _acItems[i];
  if (!item) return;
  const ta  = $('sqlInput');
  const pos = ta.selectionStart;
  const txt = ta.value;
  const rl  = $('sqlAC')._replaceLen || 0;
  ta.value  = txt.slice(0, pos - rl) + item.insert + txt.slice(pos);
  ta.selectionStart = ta.selectionEnd = pos - rl + item.insert.length;
  ta.focus();
  _hideAC();
}

function _acTrigger() {
  clearTimeout(_acTimer);
  _acTimer = setTimeout(async () => {
    const ctx   = _acContext();
    const items = await _fetchAC(ctx);
    _showAC(items, ctx ? ctx.replaceLen : 0);
  }, 200);
}

(function _wireAC() {
  const ta = $('sqlInput');
  if (!ta) return;

  ta.addEventListener('keydown', e => {
    const box = $('sqlAC');
    if (box.style.display === 'none') {
      if (e.ctrlKey && e.key === ' ') { e.preventDefault(); _acTrigger(); }
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      _acSel = Math.min(_acSel + 1, _acItems.length - 1);
      _acRenderSel();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      _acSel = Math.max(_acSel - 1, -1);
      _acRenderSel();
    } else if ((e.key === 'Enter' || e.key === 'Tab') && _acSel >= 0) {
      e.preventDefault();
      _acCommit(_acSel);
    } else if (e.key === 'Escape') {
      _hideAC();
    } else if (e.ctrlKey && e.key === ' ') {
      e.preventDefault();
      _acTrigger();
    }
  });

  ta.addEventListener('input', () => {
    const tok = _tokenBeforeCursor();
    if (!tok || tok.length < 2) { _hideAC(); return; }
    _acTrigger();
  });

  ta.addEventListener('blur', () => setTimeout(_hideAC, 150));
})();

// ── history ─────────────────────────────────────────────────────────────
let _historyItems = [];
let _pinnedItems  = [];
const _renderedHistoryItems = {};

async function loadHistory() {
  const res  = await api('/api/sqlws/history?limit=50');
  const data = await res.json();
  _historyItems = data.history || [];
  applyHistoryFilter();
}

function applyHistoryFilter() {
  const q = ($('historyQ') ? $('historyQ').value : '').toLowerCase().trim();
  const items = q
    ? _historyItems.filter(h =>
        (h.sql || '').toLowerCase().includes(q) ||
        (h.env || '').toLowerCase().includes(q))
    : _historyItems;
  renderHistoryList(items, 'historyList', false);
}

async function loadPinned() {
  const res  = await api('/api/sqlws/history?pinned=true&limit=50');
  const data = await res.json();
  _pinnedItems = data.history || [];
  renderHistoryList(_pinnedItems, 'pinnedList', true);
}

function renderHistoryList(items, targetId, pinnedView) {
  const box = $(targetId);
  if (!items.length) { box.innerHTML = '<span class="empty">None.</span>'; return; }
  _renderedHistoryItems[targetId] = items;
  box.innerHTML = items.map((item, idx) => {
    const ts    = (item.timestamp || '').replace('T',' ').slice(0,19);
    const status = item.status === 'success' ? '&#10003;'
                 : item.status === 'blocked' ? '&#9940;' : '&#10007;';
    const statusColor = item.status === 'success' ? '#00cc66'
                      : item.status === 'blocked' ? '#ff6600' : '#ff4444';
    const pinLabel = item.pinned ? '&#9733; Unpin' : '&#9734; Pin';
    const idArg = esc(item.id || '');
    const targetArg = esc(targetId);
    return `
      <div style="border-bottom:1px solid #0e2030;padding:5px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span class="ts">${esc(ts)}</span>
          <span style="color:${statusColor};font-size:10px;">${status} ${esc(item.env)}</span>
        </div>
        <div class="sql-preview" onclick="loadHistoryItem('${targetArg}',${idx})"
             title="${esc(item.sql)}" style="cursor:pointer;">${esc(item.sql)}</div>
        <div style="display:flex;gap:4px;margin-top:3px;flex-wrap:wrap;">
          <button class="sec pin-btn" onclick="togglePin('${idArg}',${!item.pinned})">${pinLabel}</button>
          <button class="sec pin-btn" onclick="deleteHistory('${idArg}')">Delete</button>
          <button class="sec pin-btn" onclick="loadHistoryItem('${targetArg}',${idx})">Load</button>
          ${item.elapsed_ms ? `<span class="ts">${item.elapsed_ms}ms</span>` : ''}
          ${item.row_count  ? `<span class="ts">${item.row_count}r</span>`   : ''}
        </div>
      </div>`;
  }).join('');
}

function loadHistoryItem(targetId, idx) {
  const item = (_renderedHistoryItems[targetId] || [])[idx];
  if (!item) return;
  loadQueryFromHistory(item.sql || '', item.binds || {});
}

function loadQueryFromHistory(sql, binds) {
  $('sqlInput').value = sql || '';
  setBinds(binds || {});
  _detectBinds(sql || '');
  $('sqlInput').focus();
}

function _detectBinds(sql) {
  const existing = new Set(
    [...document.querySelectorAll('#bindsEditor .bnd-name')].map(el => el.value.trim().replace(/^:/, ''))
  );
  const matches = (sql || '').match(/:([a-zA-Z_][a-zA-Z0-9_]*)/g) || [];
  matches.forEach(m => {
    const name = m.slice(1);
    if (!existing.has(name)) { addBind(name, ''); existing.add(name); }
  });
}

async function togglePin(id, pin) {
  await api(`/api/sqlws/history/${id}/pin?pinned=${pin}`, {method:'POST'});
  loadHistory();
  loadPinned();
}

async function deleteHistory(id) {
  if (!confirm('Delete this history entry?')) return;
  await api(`/api/sqlws/history/${id}`, {method:'DELETE'});
  loadHistory();
  loadPinned();
}

// ── init ────────────────────────────────────────────────────────────────
(async () => {
  const res = await api('/api/sqlws/config').catch(() => null);
  if (res && res.ok) {
    const cfg = await res.json();
    $('pageSizeInput').value = cfg.default_page_size || 100;
  }
  loadHistory();

  // Auto-detect bind vars when SQL changes (debounced)
  let _bindDetectTimer = null;
  $('sqlInput').addEventListener('input', () => {
    clearTimeout(_bindDetectTimer);
    _bindDetectTimer = setTimeout(() => _detectBinds($('sqlInput').value), 400);
  });
})();
</script>""")


@router.get("/query", response_class=HTMLResponse)
def admin_query():
    return _shell("PS Query Explorer", "query", noscroll=True, content="""\
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
  <input id="qSearch" type="text" placeholder="Search query name or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="qFolder" style="width:160px"><option value="">All Folders</option></select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Queries</h2>
    <div id="list" class="muted">Search to load queries.</div>
  </div>
  <div class="content">
    <h2>Selected Query</h2>
    <div id="detail" class="muted">Select a query from the list.</div>
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

async function loadFolders() {
  const folders = await api(`/api/peoplesoft/query-folders?env=${ENV}`);
  if (!folders) return;
  const sel = document.getElementById('qFolder');
  folders.forEach(f => {
    const opt = document.createElement('option');
    opt.value = f; opt.textContent = f;
    sel.appendChild(opt);
  });
}

async function doSearch() {
  const q = document.getElementById('qSearch').value.trim();
  const folder = document.getElementById('qFolder').value;
  const list = document.getElementById('list');
  list.innerHTML = '<span class="muted">Loading...</span>';
  document.getElementById('detail').innerHTML = '<span class="muted">Select a query.</span>';

  const rows = await api(`/api/peoplesoft/queries?env=${ENV}&q=${encodeURIComponent(q)}&folder=${encodeURIComponent(folder)}&limit=200`);
  if (!rows) { list.innerHTML = '<span class="muted">Error loading queries.</span>'; return; }

  document.getElementById('stats').textContent = `${rows.length} result${rows.length===1?'':'s'}`;
  list.innerHTML = '';

  if (!rows.length) { list.innerHTML = '<span class="muted">No queries found.</span>'; return; }

  rows.forEach(r => {
    const div = document.createElement('div');
    div.className = 'item';
    const folder_label = r.qryfolder && r.qryfolder.trim() ? r.qryfolder.trim() : '';
    const disabled = r.qrydisabled && r.qrydisabled !== '0' && r.qrydisabled !== 0;
    div.innerHTML = `
      <div class="item-name">${esc(r.qryname)} ${disabled ? '<span class="chip chip-warn">DISABLED</span>' : ''}</div>
      <div class="item-meta">${folder_label ? '<span class="chip chip-muted">'+esc(folder_label)+'</span> ' : ''}${r.descr ? esc(r.descr) : ''}</div>
      <div class="item-meta" style="margin-top:3px">
        ${r.selcount !== undefined ? '<span class="chip chip-info">'+r.selcount+' cols</span> ' : ''}
        ${r.bndcount !== undefined ? '<span class="chip chip-muted">'+r.bndcount+' binds</span>' : ''}
      </div>`;
    div.onclick = () => { selectQuery(r, div); };
    list.appendChild(div);
  });
}

function selectQuery(r, el) {
  document.querySelectorAll('.item').forEach(i => i.classList.remove('sel'));
  if (el) el.classList.add('sel');
  const d = document.getElementById('detail');
  const disabled = r.qrydisabled && r.qrydisabled !== '0' && r.qrydisabled !== 0;
  const folder = r.qryfolder && r.qryfolder.trim() ? r.qryfolder.trim() : '—';
  d.innerHTML = `
    <div style="margin-bottom:12px">
      <span style="font-size:16px;font-family:monospace;color:#d7faff">${esc(r.qryname)}</span>
      ${disabled ? ' <span class="chip chip-warn">DISABLED</span>' : ' <span class="chip chip-ok">ENABLED</span>'}
      <a href="/admin/object/query/${encodeURIComponent(r.qryname)}?env=${ENV}" style="margin-left:12px;font-size:11px;color:#00e5ff">Open in Object Explorer &#x2197;</a>
    </div>
    ${r.descr ? `<div style="color:#8ab;font-size:12px;margin-bottom:10px">${esc(r.descr)}</div>` : ''}
    <div style="margin-bottom:10px">
      <span class="stat"><b>${esc(folder)}</b>Folder</span>
      ${r.selcount !== undefined ? `<span class="stat"><b>${r.selcount}</b>Output Cols</span>` : ''}
      ${r.bndcount !== undefined ? `<span class="stat"><b>${r.bndcount}</b>Bind Params</span>` : ''}
      ${r.expcount !== undefined ? `<span class="stat"><b>${r.expcount}</b>Expressions</span>` : ''}
    </div>
    ${r.lastupdoprid ? `<div style="font-size:11px;color:#445">Last updated by ${esc(r.lastupdoprid)}</div>` : ''}`;
}

(async function() {
  await loadFolders();
  await doSearch();
})();
</script>""")


@router.get("/conqrs", response_class=HTMLResponse)
def admin_conqrs():
    return _shell("Connected Query Explorer", "conqrs", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00ccee;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00ccee33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00ccee22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #00ccee22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #00ccee44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#00ccee}
button{background:#00ccee;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,204,238,.07);border-left-color:#00ccee55}
.item.sel{background:rgba(0,204,238,.12);border-left-color:#00ccee}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc6644;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#001018;border:1px solid #00ccee44;color:#00ccee}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00ccee33;background:#001018;font-size:11px;margin:2px}
.stat b{color:#00ccee;font-size:16px;display:block}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right;padding-top:2px}
.kv-val{color:#d7faff;font-family:monospace}
.field-row{padding:5px 10px;border-bottom:1px solid #001018;font-size:11px;display:flex;gap:8px;align-items:baseline}
.field-row:hover{background:#020c14}
a{color:#00ccee;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="cqSearch" type="text" placeholder="Search Connected Query name or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Connected Queries</h2>
    <div id="list" class="muted">Search to load Connected Queries.</div>
  </div>
  <div class="content">
    <h2>Selected Connected Query</h2>
    <div id="detail" class="muted">Select a query from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function chip(cls, label) { return `<span class="chip ${esc(cls)}">${esc(label)}</span>`; }
function statusChip(label) {
  if (!label) return '';
  return chip(label === 'Active' ? 'chip-ok' : 'chip-muted', label);
}

async function doSearch() {
  const q = document.getElementById('cqSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const d = await api(`/api/peoplesoft/connected-queries?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No Connected Queries found.</div>'; return; }
  list.innerHTML = items.map((r, i) =>
    `<div class="item" id="item-${i}" onclick="selectCQ('${esc(r.conqrsname)}', ${i})">
       <div class="item-name">${esc(r.conqrsname)}</div>
       <div class="item-meta">${esc((r.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectCQ(conqrsname, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/connected_query/${encodeURIComponent(conqrsname)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/connected_query/${esc(conqrsname)}`;
  const sections = d.sections || [];
  const overviewSec = sections.find(s => s.id === 'overview') || {};
  const rows = overviewSec.rows || [];
  const qmapSec = sections.find(s => s.id === 'query_map');
  const fjSec = sections.find(s => s.id === 'field_joins');

  let html = `
    <div style="margin-bottom:12px">
      ${statusChip(ov.status)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#00ccee">${esc(conqrsname)}</span>
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
    + `<span class="stat"><b>${counts.sub_queries||0}</b>Queries</span>`
    + `<span class="stat"><b>${counts.field_joins||0}</b>Field Joins</span>`
    + `</div>`;

  for (const sec of [qmapSec, fjSec]) {
    if (sec && (sec.items||[]).length) {
      html += `<h2>${esc(sec.title)}</h2>`;
      html += sec.items.map(it =>
        `<div class="field-row">
           <span style="font-family:monospace;color:#d7faff">${esc(it.name)}</span>
           ${(it.chips||[]).map(c => chip(c.cls||'chip-info', c.label)).join('')}
           ${it.meta ? `<span style="color:#556;font-size:10px">${esc(it.meta)}</span>` : ''}
         </div>`
      ).join('');
    }
  }

  if (!rows.length && !qmapSec) {
    html += `<div class="muted">No detail available.</div>`;
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


