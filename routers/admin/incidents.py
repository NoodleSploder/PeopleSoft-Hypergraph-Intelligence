"""
Admin UI — Incident Management.

Routes
------
GET /admin/incidents            — incident list dashboard
GET /admin/incidents/{id}       — incident detail / replay page
"""

from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _ESC_JS

_SEV_COLOR = {"P1": "#ff4466", "P2": "#ff8800", "P3": "#ffcc44", "P4": "#00cc66"}
_SEV_LABEL = {"P1": "P1 – Critical", "P2": "P2 – High", "P3": "P3 – Medium", "P4": "P4 – Low"}

# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/incidents", response_class=HTMLResponse)
def admin_incidents(request: Request):
    return _shell("Incidents", "incidents", content=f"""
<style>
*{{box-sizing:border-box}}
.toolbar{{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
input,select{{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px;border-radius:3px}}
input:focus,select:focus{{outline:none;border-color:#00e5ff}}
button{{background:#00e5ff;border:none;padding:5px 14px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;border-radius:3px}}
button:hover{{background:#33eeff}}
button.sec{{background:transparent;border:1px solid #00e5ff44;color:#00e5ff}}
button.sec:hover{{border-color:#00e5ff;background:rgba(0,229,255,.08)}}
button.danger{{background:transparent;border:1px solid #ff446644;color:#ff4466}}
button.danger:hover{{background:rgba(255,68,102,.1)}}
.stat-row{{display:flex;gap:10px;padding:14px 16px;flex-wrap:wrap}}
.stat-card{{background:#0a161e;border:1px solid #00e5ff22;border-radius:4px;padding:10px 16px;min-width:110px}}
.stat-num{{font-size:22px;font-weight:bold;color:#00e5ff;font-family:monospace}}
.stat-lbl{{font-size:10px;color:#445;margin-top:2px}}
.stat-card.p1 .stat-num{{color:#ff4466}}
.stat-card.open .stat-num{{color:#ffcc44}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;padding:7px 10px;border-bottom:1px solid #00e5ff22;color:#445;font-size:11px;text-transform:uppercase;letter-spacing:.05em}}
td{{padding:7px 10px;border-bottom:1px solid #0a1c28;vertical-align:top}}
tr:hover td{{background:#0a161e}}
.badge{{display:inline-block;padding:1px 7px;border-radius:3px;font-size:10px;font-weight:bold;font-family:monospace}}
.sev-P1{{color:#ff4466;border:1px solid #ff446688}}
.sev-P2{{color:#ff8800;border:1px solid #ff880088}}
.sev-P3{{color:#ffcc44;border:1px solid #ffcc4488}}
.sev-P4{{color:#00cc66;border:1px solid #00cc6688}}
.state-open{{color:#ffcc44}}
.state-resolved{{color:#445}}
.empty{{padding:40px;text-align:center;color:#334;font-size:14px}}
.dialog-bg{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;align-items:center;justify-content:center}}
.dialog-bg.show{{display:flex}}
.dialog{{background:#0b1b24;border:1px solid #00e5ff44;border-radius:6px;padding:24px;width:460px;max-width:96vw}}
.dialog h3{{margin:0 0 16px;font-size:14px;color:#00e5ff}}
.dialog label{{display:block;font-size:11px;color:#889;margin-bottom:2px;margin-top:10px}}
.dialog input,.dialog select,.dialog textarea{{width:100%;padding:6px 8px;background:#050b12;color:#d7faff;border:1px solid #00e5ff44;border-radius:3px;font-size:12px;box-sizing:border-box}}
.dialog textarea{{height:70px;resize:vertical;font-family:inherit}}
.dialog-btns{{display:flex;gap:8px;justify-content:flex-end;margin-top:16px}}
#toast{{position:fixed;bottom:20px;right:20px;background:#00e5ff;color:#000;padding:8px 16px;border-radius:4px;font-size:12px;font-weight:bold;display:none;z-index:200}}
</style>

<div class="toolbar">
  <select id="stateFilter" onchange="load()">
    <option value="">All States</option>
    <option value="open" selected>Open</option>
    <option value="resolved">Resolved</option>
  </select>
  <select id="envFilter" onchange="load()">
    <option value="">All Envs</option>
  </select>
  <button onclick="showCreate()">+ New Incident</button>
  <span id="status" style="font-size:11px;color:#445;margin-left:auto"></span>
</div>

<div class="stat-row" id="statRow"></div>

<div style="padding:0 16px 80px">
  <table>
    <thead><tr>
      <th>Sev</th><th>ID</th><th>Title</th><th>Env</th>
      <th>State</th><th>Created</th><th>Window</th><th>Actions</th>
    </tr></thead>
    <tbody id="tbody"><tr><td colspan="8" class="empty">Loading…</td></tr></tbody>
  </table>
</div>

<!-- Create dialog -->
<div class="dialog-bg" id="createDlg">
  <div class="dialog">
    <h3>New Incident</h3>
    <label>Title *</label>
    <input id="dlgTitle" placeholder="Brief description of the incident">
    <label>Environment</label>
    <select id="dlgEnv"><option>HCM</option><option>FSCM</option></select>
    <label>Severity</label>
    <select id="dlgSev">
      <option value="P1">P1 – Critical</option>
      <option value="P2">P2 – High</option>
      <option value="P3" selected>P3 – Medium</option>
      <option value="P4">P4 – Low</option>
    </select>
    <label>RCA Window Start (UTC)</label>
    <input type="datetime-local" id="dlgStart" style="color-scheme:dark">
    <label>RCA Window End (UTC)</label>
    <input type="datetime-local" id="dlgEnd" style="color-scheme:dark">
    <label>Notes</label>
    <textarea id="dlgNotes" placeholder="Optional initial notes…"></textarea>
    <div style="font-size:10px;color:#556;margin-top:8px">
      ✓ RCA snapshot will be captured automatically on creation
    </div>
    <div class="dialog-btns">
      <button class="sec" onclick="hideDlg()">Cancel</button>
      <button onclick="createIncident()">Create &amp; Capture</button>
    </div>
  </div>
</div>

<div id="toast"></div>

<script>
{_ESC_JS}
const $ = id => document.getElementById(id);

function toast(msg, err){{
  const t=$('toast'); t.textContent=msg;
  t.style.background=err?'#ff4466':'#00e5ff';
  t.style.color=err?'#fff':'#000';
  t.style.display='block';
  setTimeout(()=>t.style.display='none',2600);
}}

async function loadStats(){{
  const d=await fetch('/api/incidents/stats').then(r=>r.json()).catch(()=>({{}}));
  $('statRow').innerHTML=`
    <div class="stat-card"><div class="stat-num">${{d.total||0}}</div><div class="stat-lbl">Total</div></div>
    <div class="stat-card open"><div class="stat-num">${{d.open||0}}</div><div class="stat-lbl">Open</div></div>
    <div class="stat-card"><div class="stat-num">${{d.resolved||0}}</div><div class="stat-lbl">Resolved</div></div>
    <div class="stat-card p1"><div class="stat-num">${{d.p1_open||0}}</div><div class="stat-lbl">P1 Open</div></div>
  `;
}}

async function load(){{
  $('status').textContent='Loading…';
  const state=$('stateFilter').value;
  const env=$('envFilter').value;
  let url='/api/incidents?limit=500';
  if(state) url+=`&state=${{encodeURIComponent(state)}}`;
  if(env)   url+=`&env=${{encodeURIComponent(env)}}`;
  const rows=await fetch(url).then(r=>r.json()).catch(()=>[]);
  $('status').textContent='';
  if(!rows.length){{
    $('tbody').innerHTML='<tr><td colspan="8" class="empty">No incidents found</td></tr>';
    return;
  }}
  $('tbody').innerHTML=rows.map(r=>{{
    const sev=r.severity||'P3';
    const created=(r.created_at||'').substring(0,16);
    const ws=(r.window_start||'').substring(0,16);
    const we=(r.window_end||'').substring(0,16);
    const win=ws&&we?`${{ws.replace('T',' ')}} → ${{we.replace('T',' ')}}`:'-';
    return `<tr>
      <td><span class="badge sev-${{sev}}">${{esc(sev)}}</span></td>
      <td style="color:#445;font-family:monospace">#${{r.id}}</td>
      <td><a href="/admin/incidents/${{r.id}}" style="color:#00e5ff;text-decoration:none">${{esc(r.title)}}</a></td>
      <td style="color:#889">${{esc(r.env)}}</td>
      <td class="state-${{r.state}}">${{esc(r.state)}}</td>
      <td style="color:#556;font-family:monospace;font-size:11px">${{created}}</td>
      <td style="color:#445;font-size:10px;font-family:monospace">${{win}}</td>
      <td>
        ${{r.state==='open'?`<button class="sec" onclick="resolve(${{r.id}})">Resolve</button>`:`<button class="sec" onclick="reopen(${{r.id}})">Re-open</button>`}}
        <button class="danger" onclick="del(${{r.id}},this)">✕</button>
      </td>
    </tr>`;
  }}).join('');
}}

async function loadEnvs(){{
  const envs=await fetch('/api/sqr/sources').then(r=>r.ok?r.json():null).then(d=>d?.envs||[]).catch(()=>[]);
  const sel=$('envFilter');
  envs.forEach(e=>sel.insertAdjacentHTML('beforeend',`<option value="${{esc(e)}}">${{esc(e)}}</option>`));
  const dlgEnv=$('dlgEnv');
  dlgEnv.innerHTML='';
  envs.forEach(e=>dlgEnv.insertAdjacentHTML('beforeend',`<option value="${{esc(e)}}">${{esc(e)}}</option>`));
}}

async function resolve(id){{
  await fetch(`/api/incidents/${{id}}`,{{method:'PATCH',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{state:'resolved'}})}});
  toast('Incident resolved'); load(); loadStats();
}}
async function reopen(id){{
  await fetch(`/api/incidents/${{id}}`,{{method:'PATCH',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{state:'open',resolved_at:null}})}});
  toast('Incident re-opened'); load(); loadStats();
}}
async function del(id,btn){{
  if(!confirm('Delete incident #'+id+'? This cannot be undone.')) return;
  const res=await fetch(`/api/incidents/${{id}}`,{{method:'DELETE'}});
  if(res.ok){{ toast('Deleted'); load(); loadStats(); }}
  else toast('Delete failed',true);
}}

function showCreate(){{
  // default window: last 1 hour
  const now=new Date(); const h1=new Date(now-3600000);
  const fmt=d=>d.toISOString().substring(0,16);
  $('dlgStart').value=fmt(h1); $('dlgEnd').value=fmt(now);
  $('dlgTitle').value=''; $('dlgNotes').value='';
  $('createDlg').classList.add('show');
  setTimeout(()=>$('dlgTitle').focus(),50);
}}
function hideDlg(){{ $('createDlg').classList.remove('show'); }}

async function createIncident(){{
  const title=$('dlgTitle').value.trim();
  if(!title){{alert('Title is required'); return;}}
  const start=new Date($('dlgStart').value).toISOString().replace('T',' ').substring(0,19);
  const end  =new Date($('dlgEnd').value).toISOString().replace('T',' ').substring(0,19);
  const btn=document.querySelector('#createDlg button:last-child');
  btn.disabled=true; btn.textContent='Capturing…';
  try{{
    const res=await fetch('/api/incidents',{{
      method:'POST',headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{
        title,env:$('dlgEnv').value,severity:$('dlgSev').value,
        window_start:start,window_end:end,
        notes:$('dlgNotes').value,capture_rca:true
      }})
    }});
    const d=await res.json();
    if(!res.ok) throw new Error(d.detail||'Create failed');
    hideDlg(); toast('Incident #'+d.id+' created');
    window.location.href='/admin/incidents/'+d.id;
  }}catch(e){{ toast(String(e),true); btn.disabled=false; btn.textContent='Create & Capture'; }}
}}

document.addEventListener('keydown',e=>{{if(e.key==='Escape')hideDlg();}});
loadEnvs(); load(); loadStats();
</script>
""")


# ── Detail / Replay ───────────────────────────────────────────────────────────

@router.get("/incidents/{incident_id}", response_class=HTMLResponse)
def admin_incident_detail(incident_id: int, request: Request):
    from connectors import incidentdb as _idb
    inc = _idb.get_incident(incident_id)
    if not inc:
        return _shell("Incident Not Found", "incidents", content=
            '<div style="padding:40px;color:#ff4466">Incident not found.</div>')

    sev    = inc.get("severity", "P3")
    state  = inc.get("state", "open")
    sev_color = _SEV_COLOR.get(sev, "#ffcc44")

    return _shell(f"Incident #{incident_id}", "incidents", content=f"""
<style>
*{{box-sizing:border-box}}
.topbar{{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
button{{background:#00e5ff;border:none;padding:5px 14px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;border-radius:3px}}
button:hover{{background:#33eeff}}
button.sec{{background:transparent;border:1px solid #00e5ff44;color:#00e5ff}}
button.sec:hover{{border-color:#00e5ff;background:rgba(0,229,255,.08)}}
button.warn{{background:transparent;border:1px solid #ff880044;color:#ff8800}}
button.warn:hover{{border-color:#ff8800;background:rgba(255,136,0,.08)}}
button.danger{{background:transparent;border:1px solid #ff446644;color:#ff4466}}
button.danger:hover{{background:rgba(255,68,102,.1)}}
.meta-card{{background:#0a161e;border:1px solid #00e5ff22;border-radius:4px;padding:12px 16px;margin:12px 16px 0}}
.meta-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin-top:8px}}
.meta-item label{{font-size:10px;color:#445;display:block;margin-bottom:2px}}
.meta-item span{{font-size:13px;color:#d7faff}}
.badge{{display:inline-block;padding:1px 7px;border-radius:3px;font-size:11px;font-weight:bold;font-family:monospace}}
.sev-P1{{color:#ff4466;border:1px solid #ff446688}}
.sev-P2{{color:#ff8800;border:1px solid #ff880088}}
.sev-P3{{color:#ffcc44;border:1px solid #ffcc4488}}
.sev-P4{{color:#00cc66;border:1px solid #00cc6688}}
.state-open{{color:#ffcc44}}
.state-resolved{{color:#00cc66}}
textarea{{background:#050b12;color:#d7faff;border:1px solid #00e5ff44;border-radius:3px;width:100%;padding:8px;font-family:inherit;font-size:12px;resize:vertical}}
textarea:focus{{outline:none;border-color:#00e5ff}}
.tabs{{display:flex;gap:0;border-bottom:1px solid #00e5ff22;padding:0 16px;margin-top:14px}}
.tab{{padding:7px 16px;cursor:pointer;font-size:12px;color:#445;border-bottom:2px solid transparent}}
.tab:hover{{color:#d7faff}}
.tab.active{{color:#00e5ff;border-bottom-color:#00e5ff}}
.tab-content{{display:none;padding:16px}}
.tab-content.active{{display:block}}
.section{{background:#0a161e;border:1px solid #00e5ff22;border-radius:4px;padding:12px 16px;margin-bottom:12px}}
.section-hdr{{display:flex;align-items:center;gap:8px;margin-bottom:10px;font-size:13px;font-weight:bold}}
.badge-info{{background:#00e5ff22;color:#00e5ff;padding:1px 7px;border-radius:3px;font-size:10px}}
.badge-err{{background:#ff446622;color:#ff4466;padding:1px 7px;border-radius:3px;font-size:10px}}
.badge-warn{{background:#ff880022;color:#ff8800;padding:1px 7px;border-radius:3px;font-size:10px}}
.tl-item{{display:flex;align-items:flex-start;gap:8px;padding:4px 0;border-bottom:1px solid #0a1c28;font-size:12px}}
.tl-ts{{color:#445;font-family:monospace;font-size:11px;min-width:115px}}
.tl-dot{{width:8px;height:8px;border-radius:50%;margin-top:3px;flex-shrink:0}}
.tl-dot-err{{background:#ff4466}}
.tl-dot-warn{{background:#ff8800}}
.tl-dot-info{{background:#00e5ff}}
.tl-label{{color:#d7faff}}
.sum-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;margin-bottom:14px}}
.sum-card{{background:#0a161e;border:1px solid #00e5ff22;border-radius:4px;padding:8px 12px}}
.sum-num{{font-size:20px;font-weight:bold;color:#00e5ff;font-family:monospace}}
.sum-lbl{{font-size:10px;color:#445}}
.sum-card.err .sum-num{{color:#ff4466}}
.sum-card.warn .sum-num{{color:#ff8800}}
.sum-card.ok .sum-num{{color:#00cc66}}
.warn-box{{background:#1a0d00;border:1px solid #ff880044;border-radius:4px;padding:8px 12px;margin-bottom:8px;font-size:12px;color:#ff8800}}
.empty{{padding:30px;text-align:center;color:#334;font-size:13px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;padding:5px 8px;border-bottom:1px solid #00e5ff22;color:#445;font-size:10px;text-transform:uppercase}}
td{{padding:5px 8px;border-bottom:1px solid #0a1c28;vertical-align:top}}
tr:hover td{{background:#0a1c28}}
pre{{background:#050b12;border:1px solid #00e5ff22;border-radius:3px;padding:10px;font-size:11px;overflow-x:auto;color:#d7faff;margin:0}}
.ash-bar{{height:12px;border-radius:2px;display:inline-block;vertical-align:middle}}
#toast{{position:fixed;bottom:20px;right:20px;background:#00e5ff;color:#000;padding:8px 16px;border-radius:4px;font-size:12px;font-weight:bold;display:none;z-index:200}}
.edit-field{{display:none}}
.edit-field.show{{display:inline}}
.view-field.hide{{display:none}}
</style>

<div class="topbar">
  <a href="/admin/incidents" style="color:#00e5ff;text-decoration:none;font-size:11px">← All Incidents</a>
  <span style="color:#445">|</span>
  <span style="font-size:13px;font-weight:bold">Incident #{incident_id}</span>
  <span class="badge sev-{sev}" style="margin-left:4px">{sev}</span>
  <span class="badge {state}" style="margin-left:2px;color:{sev_color};border:1px solid {sev_color}88">{state}</span>
  <div style="margin-left:auto;display:flex;gap:6px">
    <button class="sec" onclick="refreshSnapshot()">↻ Re-capture RCA</button>
    {'<button class="sec" onclick="resolveInc()">✓ Resolve</button>' if state == 'open' else '<button class="sec" onclick="reopenInc()">Re-open</button>'}
    <button class="danger" onclick="deleteInc()">Delete</button>
  </div>
</div>

<div class="meta-card">
  <div style="display:flex;align-items:center;justify-content:space-between">
    <div style="font-size:14px;font-weight:bold" id="titleDisp">{inc['title']}</div>
    <button class="sec" onclick="toggleEditTitle()" style="font-size:10px">Edit</button>
  </div>
  <div style="margin-top:6px;display:none" id="titleEdit">
    <input id="titleInput" value="{inc['title']}" style="background:#050b12;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:13px;width:60%;border-radius:3px">
    <button onclick="saveTitle()" style="margin-left:6px">Save</button>
    <button class="sec" onclick="toggleEditTitle()" style="margin-left:4px">Cancel</button>
  </div>
  <div class="meta-grid" style="margin-top:10px">
    <div class="meta-item"><label>Env</label><span>{inc['env']}</span></div>
    <div class="meta-item"><label>Severity</label>
      <select id="sevSel" onchange="saveSev()" style="background:#050b12;color:#d7faff;border:1px solid #00e5ff44;padding:2px 6px;font-size:12px;border-radius:3px">
        <option {'selected' if sev=='P1' else ''} value="P1">P1 – Critical</option>
        <option {'selected' if sev=='P2' else ''} value="P2">P2 – High</option>
        <option {'selected' if sev=='P3' else ''} value="P3">P3 – Medium</option>
        <option {'selected' if sev=='P4' else ''} value="P4">P4 – Low</option>
      </select>
    </div>
    <div class="meta-item"><label>Created</label><span style="font-family:monospace;font-size:11px">{inc['created_at']}</span></div>
    <div class="meta-item"><label>RCA Window</label><span style="font-family:monospace;font-size:11px">{(inc.get('window_start') or '')[:16]} → {(inc.get('window_end') or '')[:16]}</span></div>
    {'<div class="meta-item"><label>Resolved</label><span style="font-family:monospace;font-size:11px">' + str(inc.get('resolved_at') or '-') + '</span></div>' if inc.get('resolved_at') else ''}
  </div>
  <div style="margin-top:10px">
    <div style="font-size:10px;color:#445;margin-bottom:4px">Notes</div>
    <textarea id="notesArea" rows="2" onblur="saveNotes()" placeholder="Add investigation notes…">{inc.get('notes') or ''}</textarea>
  </div>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('rca',this)">RCA Snapshot</div>
  <div class="tab" onclick="switchTab('timeline',this)">Timeline</div>
  <div class="tab" onclick="switchTab('processes',this)">Processes</div>
  <div class="tab" onclick="switchTab('logs',this)">Log Errors</div>
  <div class="tab" onclick="switchTab('ib',this)">IB Errors</div>
  <div class="tab" onclick="switchTab('ash',this)">ASH</div>
  <div class="tab" onclick="switchTab('history',this)">Snapshot History</div>
</div>

<div id="tab-rca" class="tab-content active"><div class="empty" style="color:#334">Loading RCA snapshot…</div></div>
<div id="tab-timeline" class="tab-content"><div class="empty" style="color:#334">Loading…</div></div>
<div id="tab-processes" class="tab-content"><div class="empty" style="color:#334">Loading…</div></div>
<div id="tab-logs" class="tab-content"><div class="empty" style="color:#334">Loading…</div></div>
<div id="tab-ib" class="tab-content"><div class="empty" style="color:#334">Loading…</div></div>
<div id="tab-ash" class="tab-content"><div class="empty" style="color:#334">Loading…</div></div>
<div id="tab-history" class="tab-content"><div class="empty" style="color:#334">Loading…</div></div>

<div id="toast"></div>

<script>
{_ESC_JS}
const $ = id => document.getElementById(id);
const INC_ID = {incident_id};

function toast(msg, err){{
  const t=$('toast'); t.textContent=msg;
  t.style.background=err?'#ff4466':'#00e5ff';
  t.style.color=err?'#fff':'#000';
  t.style.display='block';
  setTimeout(()=>t.style.display='none',2600);
}}

function switchTab(name, el){{
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  $('tab-'+name).classList.add('active');
}}

// ── Metadata edits ──────────────────────────────────────────────────────────
function toggleEditTitle(){{
  const disp=$('titleDisp'), edit=$('titleEdit');
  const show=edit.style.display==='none'||!edit.style.display;
  disp.style.display=show?'none':'';
  edit.style.display=show?'block':'none';
  if(show)$('titleInput').focus();
}}
async function saveTitle(){{
  const v=$('titleInput').value.trim(); if(!v) return;
  await fetch(`/api/incidents/${{INC_ID}}`,{{method:'PATCH',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{title:v}})}});
  $('titleDisp').textContent=v; toggleEditTitle(); toast('Title updated');
}}
async function saveSev(){{
  await fetch(`/api/incidents/${{INC_ID}}`,{{method:'PATCH',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{severity:$('sevSel').value}})}});
  toast('Severity updated');
}}
let _notesTimer=null;
function saveNotes(){{
  clearTimeout(_notesTimer);
  _notesTimer=setTimeout(async()=>{{
    await fetch(`/api/incidents/${{INC_ID}}`,{{method:'PATCH',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{notes:$('notesArea').value}})}});
    toast('Notes saved');
  }},800);
}}

// ── State changes ────────────────────────────────────────────────────────────
async function resolveInc(){{
  await fetch(`/api/incidents/${{INC_ID}}`,{{method:'PATCH',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{state:'resolved'}})}});
  toast('Incident resolved'); setTimeout(()=>location.reload(),1000);
}}
async function reopenInc(){{
  await fetch(`/api/incidents/${{INC_ID}}`,{{method:'PATCH',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{state:'open',resolved_at:null}})}});
  toast('Incident re-opened'); setTimeout(()=>location.reload(),1000);
}}
async function deleteInc(){{
  if(!confirm('Delete incident #'+INC_ID+'? This cannot be undone.')) return;
  const res=await fetch(`/api/incidents/${{INC_ID}}`,{{method:'DELETE'}});
  if(res.ok){{ window.location.href='/admin/incidents'; }}
  else toast('Delete failed',true);
}}

// ── Snapshot refresh ─────────────────────────────────────────────────────────
async function refreshSnapshot(){{
  const btn=document.querySelector('button.sec');
  btn.disabled=true; btn.textContent='Capturing…';
  try{{
    const res=await fetch(`/api/incidents/${{INC_ID}}/snapshot`);
    const d=await res.json();
    if(!res.ok) throw new Error(d.detail||'Failed');
    toast('Snapshot captured'); loadSnapshot();
  }}catch(e){{toast(String(e),true);}}
  finally{{btn.disabled=false; btn.textContent='↻ Re-capture RCA';}}
}}

// ── RCA rendering (shared with rca.py render logic) ──────────────────────────
const RUNSTATUS={{'3':'Error','4':'No Success','8':'Cancelled','9':'Not Successful','10':'Restarted','17':'Timed Out'}};
const WAIT_COLOR={{CPU:'#00cc66',Idle:'#334',Other:'#778','User I/O':'#00e5ff','System I/O':'#88bbff',Concurrency:'#ffcc44',Configuration:'#ff8800',Application:'#ff4466',Cluster:'#aa88ff',Commit:'#88ff44',Scheduler:'#aa88ff'}};

function renderRCA(d){{
  const s=d.summary||{{}};
  let html='';
  // Summary cards
  const pf=s.process_failures||0,le=s.log_errors||0,ib=s.ib_errors||0,total=pf+le+ib;
  html+=`<div class="sum-grid">
    <div class="sum-card ${{total?'err':'ok'}}"><div class="sum-num">${{total}}</div><div class="sum-lbl">Total Events</div></div>
    <div class="sum-card ${{pf?'err':'ok'}}"><div class="sum-num">${{pf}}</div><div class="sum-lbl">Process Failures</div></div>
    <div class="sum-card ${{le?'warn':'ok'}}"><div class="sum-num">${{le}}</div><div class="sum-lbl">Log Errors</div></div>
    <div class="sum-card ${{ib?'err':'ok'}}"><div class="sum-num">${{ib}}</div><div class="sum-lbl">IB Errors</div></div>
    ${{d.ash?`<div class="sum-card ${{d.ash.total_samples>500?'warn':'ok'}}"><div class="sum-num">${{d.ash.total_samples}}</div><div class="sum-lbl">ASH Samples</div></div>`:''}}
  </div>`;
  (d.warnings||[]).forEach(w=>{{html+=`<div class="warn-box">&#9888; ${{esc(w)}}</div>`;}});
  if(!total&&!d.ash?.total_samples){{html+='<div class="empty">&#10003; No failures or errors found in this window.</div>';}}
  $('tab-rca').innerHTML=`<div style="padding:16px">${{html}}</div>`;
  renderTimeline(d);
  renderProcesses(d);
  renderLogs(d);
  renderIB(d);
  renderASH(d);
}}

function renderTimeline(d){{
  const items=d.timeline||[];
  if(!items.length){{$('tab-timeline').innerHTML='<div class="empty">No timeline events</div>';return;}}
  let html=`<div class="section"><div class="section-hdr"><span>Timeline</span><span class="badge-info">${{items.length}}</span></div>`;
  items.slice(0,200).forEach(item=>{{
    const sev=item.severity==='error'?'err':item.severity==='warning'?'warn':'info';
    html+=`<div class="tl-item"><span class="tl-ts">${{esc((item.ts||'').substring(0,19).replace('T',' '))}}</span><div class="tl-dot tl-dot-${{sev}}"></div><span class="tl-label">${{esc(item.label)}}</span></div>`;
  }});
  html+='</div>';
  $('tab-timeline').innerHTML=`<div style="padding:16px">${{html}}</div>`;
}}

function renderProcesses(d){{
  const procs=d.processes||[];
  if(!procs.length){{$('tab-processes').innerHTML='<div class="empty">No process failures</div>';return;}}
  let html=`<div class="section"><div class="section-hdr"><span>Process Failures</span><span class="badge-err">${{procs.length}}</span></div>
    <table><thead><tr><th>PID</th><th>Name</th><th>Type</th><th>Status</th><th>DB</th><th>Start</th><th>End</th></tr></thead><tbody>`;
  procs.forEach(p=>{{
    html+=`<tr><td style="font-family:monospace;color:#445">${{p.prcsinstance||''}}</td>
      <td><a href="/admin/runtime?prcsinstance=${{p.prcsinstance||''}}" style="color:#00e5ff;text-decoration:none">${{esc(p.prcsname||'')}}</a></td>
      <td style="color:#889">${{esc(p.prcstype||'')}}</td>
      <td style="color:#ff4466">${{esc(RUNSTATUS[String(p.runstatus)]||p.runstatus||'')}}</td>
      <td style="color:#445">${{esc(p.dbname||'')}}</td>
      <td style="font-family:monospace;font-size:10px;color:#445">${{(p.begindttm||'').substring(0,19)}}</td>
      <td style="font-family:monospace;font-size:10px;color:#445">${{(p.enddttm||'').substring(0,19)}}</td>
    </tr>`;
  }});
  html+='</tbody></table></div>';
  $('tab-processes').innerHTML=`<div style="padding:16px">${{html}}</div>`;
}}

function renderLogs(d){{
  const errs=d.log_errors||[];
  if(!errs.length){{$('tab-logs').innerHTML='<div class="empty">No log errors in window</div>';return;}}
  let html=`<div class="section"><div class="section-hdr"><span>Log Errors</span><span class="badge-err">${{errs.length}}</span></div>
    <table><thead><tr><th>Time</th><th>Source</th><th>Code</th><th>Message</th></tr></thead><tbody>`;
  errs.slice(0,200).forEach(e=>{{
    html+=`<tr>
      <td style="font-family:monospace;font-size:10px;color:#445;white-space:nowrap">${{(e.ts||'').substring(0,19)}}</td>
      <td style="color:#889;font-size:11px">${{esc(e.source_name||'')}}</td>
      <td style="color:#ff8800;font-family:monospace;font-size:10px">${{esc(e.error_code||'')}}</td>
      <td style="font-size:11px">${{esc((e.message||e.raw||'').substring(0,180))}}</td>
    </tr>`;
  }});
  html+='</tbody></table></div>';
  $('tab-logs').innerHTML=`<div style="padding:16px">${{html}}</div>`;
}}

function renderIB(d){{
  const errs=d.ib_errors||[];
  if(!errs.length){{$('tab-ib').innerHTML='<div class="empty">No IB errors in window</div>';return;}}
  let html=`<div class="section"><div class="section-hdr"><span>IB Errors</span><span class="badge-err">${{errs.length}}</span></div>
    <table><thead><tr><th>Time</th><th>Operation</th><th>Node</th><th>Message</th></tr></thead><tbody>`;
  errs.slice(0,100).forEach(e=>{{
    html+=`<tr>
      <td style="font-family:monospace;font-size:10px;color:#445;white-space:nowrap">${{(e.ts||'').substring(0,19)}}</td>
      <td style="color:#00e5ff;font-size:11px">${{esc(e.ib_operation||'')}}</td>
      <td style="color:#889;font-size:11px">${{esc(e.requesting_node||'')}}</td>
      <td style="font-size:11px">${{esc((e.description||e.raw||'').substring(0,200))}}</td>
    </tr>`;
  }});
  html+='</tbody></table></div>';
  $('tab-ib').innerHTML=`<div style="padding:16px">${{html}}</div>`;
}}

function renderASH(d){{
  const ash=d.ash;
  if(!ash||!ash.total_samples){{$('tab-ash').innerHTML='<div class="empty">No ASH data for this window</div>';return;}}
  let html=`<div class="section"><div class="section-hdr"><span>Oracle ASH</span><span class="badge-warn">${{ash.total_samples}} samples</span></div>`;
  if(ash.top_waits?.length){{
    html+='<div style="margin-bottom:10px;font-size:11px;color:#889">Top Wait Events</div>';
    const maxSamp=Math.max(...ash.top_waits.map(w=>w.sample_count||0),1);
    ash.top_waits.slice(0,15).forEach(w=>{{
      const pct=Math.round((w.sample_count||0)/maxSamp*100);
      const col=WAIT_COLOR[w.wait_class]||WAIT_COLOR[w.event_name]||'#556';
      html+=`<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;font-size:11px">
        <span style="color:#889;min-width:180px;text-overflow:ellipsis;overflow:hidden;white-space:nowrap" title="${{esc(w.event_name||'')}}">${{esc((w.event_name||'').substring(0,28))}}</span>
        <div class="ash-bar" style="width:${{pct}}%;max-width:200px;background:${{col}}"></div>
        <span style="color:#445;font-family:monospace">${{w.sample_count}}</span>
      </div>`;
    }});
  }}
  html+='</div>';
  $('tab-ash').innerHTML=`<div style="padding:16px">${{html}}</div>`;
}}

function renderHistory(snaps){{
  if(!snaps.length){{$('tab-history').innerHTML='<div class="empty">No snapshots yet</div>';return;}}
  let html='<div style="padding:16px"><table><thead><tr><th>#</th><th>Source</th><th>Captured At</th><th>Size</th></tr></thead><tbody>';
  snaps.forEach(s=>{{
    const size=JSON.stringify(s.data||{{}}).length;
    html+=`<tr>
      <td style="font-family:monospace;color:#445">${{s.id}}</td>
      <td><span class="badge-info">${{esc(s.source)}}</span></td>
      <td style="font-family:monospace;font-size:11px;color:#445">${{(s.snapshot_at||'').substring(0,19)}}</td>
      <td style="font-family:monospace;color:#445">${{(size/1024).toFixed(1)}} KB</td>
    </tr>`;
  }});
  html+='</tbody></table></div>';
  $('tab-history').innerHTML=html;
}}

// ── Load data ────────────────────────────────────────────────────────────────
async function loadSnapshot(){{
  $('tab-rca').innerHTML='<div class="empty" style="color:#334">Loading…</div>';
  const inc=await fetch(`/api/incidents/${{INC_ID}}`).then(r=>r.json()).catch(()=>({{}}));
  const snaps=inc.snapshots||[];
  renderHistory(snaps);
  const rcaSnap=snaps.filter(s=>s.source==='rca').pop();
  if(!rcaSnap){{
    $('tab-rca').innerHTML='<div class="empty">No RCA snapshot yet. Click "↻ Re-capture RCA" to capture one.</div>';
    $('tab-timeline').innerHTML='<div class="empty">No data</div>';
    $('tab-processes').innerHTML='<div class="empty">No data</div>';
    $('tab-logs').innerHTML='<div class="empty">No data</div>';
    $('tab-ib').innerHTML='<div class="empty">No data</div>';
    $('tab-ash').innerHTML='<div class="empty">No data</div>';
    return;
  }}
  renderRCA(rcaSnap.data||{{}});
}}

loadSnapshot();
</script>
""")
