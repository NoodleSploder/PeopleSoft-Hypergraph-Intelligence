from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell

_RUNSTATUS = {
    "0":"Cancel","1":"Cancel Pending","2":"Queued","3":"Error","4":"No Success",
    "5":"Hold","6":"Queued","7":"Processing","8":"Cancelled","9":"Not Successful",
    "10":"Restarted","11":"Posting","12":"Posted","13":"Delete","14":"Done",
    "15":"Delete","16":"Pending","17":"Timed Out",
}


@router.get("/rca", response_class=HTMLResponse)
def admin_rca(request: Request):
    return _shell("Incident RCA", "rca", content="""
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0}
.topbar{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
input[type=datetime-local]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px;border-radius:3px;color-scheme:dark}
input[type=datetime-local]:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 14px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;border-radius:3px}
button:hover{background:#33eeff}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;margin-right:2px}
button.sec:hover{border-color:#00e5ff;background:rgba(0,229,255,.08)}
select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px;border-radius:3px}
#result{padding:16px;max-width:1200px}
.sum-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;margin-bottom:18px}
.sum-card{background:#0a161e;border:1px solid #00e5ff22;border-radius:4px;padding:10px 14px}
.sum-num{font-size:22px;font-weight:bold;color:#00e5ff;font-family:monospace}
.sum-lbl{font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-top:2px}
.sum-card.warn .sum-num{color:#ffaa00}
.sum-card.err .sum-num{color:#ff4466}
.sum-card.ok .sum-num{color:#00cc66}
.section{margin-bottom:22px}
.section-hdr{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#00e5ff;
  padding:5px 0;border-bottom:1px solid #00e5ff22;margin-bottom:8px;
  display:flex;align-items:center;justify-content:space-between}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:10px;font-weight:bold}
.badge-err{background:#330010;border:1px solid #ff446633;color:#ff4466}
.badge-warn{background:#1a0e00;border:1px solid #ffaa0033;color:#ffaa00}
.badge-ok{background:#00280a;border:1px solid #00cc6633;color:#00cc66}
.badge-info{background:#001830;border:1px solid #00e5ff33;color:#00e5ff}
table{width:100%;border-collapse:collapse;font-size:11px}
th{text-align:left;padding:4px 8px;color:#445;font-size:10px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #0d1b24}
td{padding:4px 8px;border-bottom:1px solid #0a1520;vertical-align:top}
tr:hover td{background:rgba(0,229,255,.02)}
.mono{font-family:monospace}
.tl-item{display:flex;gap:10px;padding:5px 0;border-bottom:1px solid #080f16;align-items:flex-start}
.tl-ts{font-size:10px;color:#445;font-family:monospace;min-width:130px;flex-shrink:0;padding-top:1px}
.tl-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:4px}
.tl-dot-err{background:#ff4466}
.tl-dot-warn{background:#ffaa00}
.tl-label{font-size:11px;color:#acd;flex:1;word-break:break-word}
.empty{color:#445;font-size:12px;padding:24px;text-align:center}
.warn-box{color:#ffaa00;font-size:11px;padding:6px 10px;border:1px solid #ffaa0022;background:#1a0e00;border-radius:3px;margin:4px 0}
.pct-bar{display:inline-block;width:70px;height:7px;background:#0d1b24;border-radius:2px;vertical-align:middle;margin-right:5px}
.pct-fill{height:100%;border-radius:2px}
.db-sel-wrap{display:flex;align-items:center;gap:6px;font-size:11px;color:#556}
</style>

<div class="topbar">
  <div>
    <span style="font-size:10px;color:#445;margin-right:4px">From</span>
    <input type="datetime-local" id="startDt" style="width:185px">
  </div>
  <div>
    <span style="font-size:10px;color:#445;margin-right:4px">To</span>
    <input type="datetime-local" id="endDt" style="width:185px">
  </div>
  <div style="display:flex;gap:4px">
    <button class="sec" onclick="setWindow(15)">15m</button>
    <button class="sec" onclick="setWindow(60)">1h</button>
    <button class="sec" onclick="setWindow(240)">4h</button>
    <button class="sec" onclick="setWindow(1440)">24h</button>
  </div>
  <div class="db-sel-wrap">
    Oracle DB: <select id="dbSel"><option value="">— none —</option></select>
  </div>
  <button onclick="investigate()">&#128269; Investigate</button>
  <button class="sec" id="saveBtn" onclick="saveAsIncident()" style="display:none">&#128203; Save as Incident</button>
  <span id="status" style="font-size:10px;color:#445"></span>
</div>

<div id="result"><div class="empty">Select a time window and click Investigate.</div></div>

<script>
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

// Pre-fill time inputs — from URL params or default to last 1h
(function(){
  const p=new URLSearchParams(location.search);
  const s=p.get('start'), e=p.get('end');
  if(s&&e){
    // params are UTC ISO — convert to local for datetime-local input
    const st=new Date(s.replace(' ','T')+'Z'), en=new Date(e.replace(' ','T')+'Z');
    document.getElementById('startDt').value=fmtLocal(isNaN(st)?new Date(Date.now()-3600000):st);
    document.getElementById('endDt').value=fmtLocal(isNaN(en)?new Date():en);
    // auto-run investigation if params provided
    setTimeout(()=>investigate(),200);
  }else{
    const now=new Date();
    document.getElementById('endDt').value=fmtLocal(now);
    document.getElementById('startDt').value=fmtLocal(new Date(now-3600000));
  }
})();

function fmtLocal(d){
  const pad=n=>String(n).padStart(2,'0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function setWindow(mins){
  const now=new Date();
  document.getElementById('endDt').value=fmtLocal(now);
  document.getElementById('startDt').value=fmtLocal(new Date(now-mins*60000));
}

// Populate DB selector from runtime config
fetch('/api/runtime/config').then(r=>r.json()).then(d=>{
  const sel=document.getElementById('dbSel');
  (d.dbs||[]).forEach(db=>{
    const o=document.createElement('option');
    o.value=o.textContent=db;
    sel.appendChild(o);
  });
  if(d.dbs&&d.dbs.length)sel.value=d.dbs[0];
}).catch(()=>{});

async function investigate(){
  const env=window.dsGetEnv?window.dsGetEnv():'HCM';
  const startRaw=document.getElementById('startDt').value;
  const endRaw=document.getElementById('endDt').value;
  const db=document.getElementById('dbSel').value;
  if(!startRaw||!endRaw){alert('Select a time window');return;}
  // Convert local datetime-local value to UTC ISO string
  const start=new Date(startRaw).toISOString().replace('T',' ').substring(0,19);
  const end=new Date(endRaw).toISOString().replace('T',' ').substring(0,19);
  document.getElementById('status').textContent='Investigating…';
  document.getElementById('result').innerHTML='<div class="empty" style="color:#334">Correlating data sources…</div>';
  try{
    const url=`/api/runtime/rca?env=${encodeURIComponent(env)}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}${db?'&db='+encodeURIComponent(db):''}`;
    const d=await fetch(url).then(r=>r.json());
    document.getElementById('status').textContent='';
    document.getElementById('saveBtn').style.display='';
    render(d,startRaw,endRaw);
  }catch(e){
    document.getElementById('status').textContent='';
    document.getElementById('result').innerHTML=`<div class="warn-box">Error: ${esc(String(e))}</div>`;
  }
}

const RUNSTATUS={
  '3':'Error','4':'No Success','8':'Cancelled','9':'Not Successful',
  '10':'Restarted','17':'Timed Out',
};
const WAIT_COLOR={CPU:'#00cc66',Idle:'#334',Other:'#778',
  'User I/O':'#00e5ff','System I/O':'#88bbff','Concurrency':'#ffcc44',
  Configuration:'#ff8800','Application':'#ff4466','Cluster':'#aa88ff',
  'Commit':'#88ff44','Scheduler':'#aa88ff'};

function render(d,startRaw,endRaw){
  const s=d.summary||{};
  const wins=`${startRaw.replace('T',' ')} → ${endRaw.replace('T',' ')}`;
  let html=`<div style="font-size:10px;color:#445;margin-bottom:12px">Window: ${esc(wins)} &nbsp;·&nbsp; Env: ${esc(d.env||'')}</div>`;

  // Summary cards
  const pf=s.process_failures||0,le=s.log_errors||0,ib=s.ib_errors||0;
  const total=pf+le+ib;
  html+=`<div class="sum-grid">
    <div class="sum-card ${total?'err':'ok'}">
      <div class="sum-num">${total}</div>
      <div class="sum-lbl">Total Events</div>
    </div>
    <div class="sum-card ${pf?'err':'ok'}">
      <div class="sum-num">${pf}</div>
      <div class="sum-lbl">Process Failures</div>
    </div>
    <div class="sum-card ${le?'warn':'ok'}">
      <div class="sum-num">${le}</div>
      <div class="sum-lbl">Log Errors</div>
    </div>
    <div class="sum-card ${ib?'err':'ok'}">
      <div class="sum-num">${ib}</div>
      <div class="sum-lbl">IB Errors</div>
    </div>
    ${d.ash?`<div class="sum-card ${d.ash.total_samples>500?'warn':'ok'}">
      <div class="sum-num">${d.ash.total_samples}</div>
      <div class="sum-lbl">ASH Samples</div>
    </div>`:''}
  </div>`;

  // Warnings
  (d.warnings||[]).forEach(w=>{html+=`<div class="warn-box">&#9888; ${esc(w)}</div>`;});

  if(!total && !d.ash?.total_samples){
    html+='<div class="empty" style="margin-top:20px">&#10003; No failures or errors found in this window.</div>';
    document.getElementById('result').innerHTML=html;return;
  }

  // Timeline
  if((d.timeline||[]).length){
    html+=`<div class="section"><div class="section-hdr"><span>Timeline</span><span class="badge badge-info">${d.timeline.length}</span></div>`;
    d.timeline.slice(0,100).forEach(item=>{
      const sev=item.severity==='error'?'err':'warn';
      html+=`<div class="tl-item">
        <span class="tl-ts">${esc((item.ts||'').substring(0,19).replace('T',' '))}</span>
        <div class="tl-dot tl-dot-${sev}"></div>
        <span class="tl-label">${esc(item.label)}</span>
      </div>`;
    });
    html+='</div></div>';
  }

  // Process failures
  if((d.process_failures||[]).length){
    html+=`<div class="section"><div class="section-hdr"><span>Process Failures</span><span class="badge badge-err">${d.process_failures.length}</span></div>
    <table><thead><tr><th>Instance</th><th>Type</th><th>Program</th><th>Operator</th><th>Status</th><th>Requested</th><th>Server</th></tr></thead><tbody>`;
    d.process_failures.forEach(r=>{
      const inst=r.prcsinstance||'';
      const status=RUNSTATUS[String(r.runstatus)]||r.runstatus||'?';
      html+=`<tr>
        <td><a href="/admin/runtime?instance=${esc(String(inst))}" target="_blank" style="color:#00e5ff;text-decoration:none">${esc(String(inst))}</a></td>
        <td class="mono">${esc(r.prcstype||'')}</td>
        <td class="mono">${esc(r.prcsname||'')}</td>
        <td class="mono">${esc(r.oprid||'')}</td>
        <td><span class="badge badge-err">${esc(status)}</span></td>
        <td class="mono" style="font-size:10px;color:#556">${esc(String(r.rqstdttm||'').substring(0,19))}</td>
        <td style="font-size:10px;color:#445">${esc(r.servernamerun||'')}</td>
      </tr>`;
    });
    html+='</tbody></table></div>';
  }

  // Log errors
  if((d.log_errors||[]).length){
    html+=`<div class="section"><div class="section-hdr"><span>Log Errors</span><span class="badge badge-warn">${d.log_errors.length}</span></div>
    <table><thead><tr><th>Time</th><th>Source</th><th>Code</th><th>Operator</th><th>Message</th></tr></thead><tbody>`;
    d.log_errors.slice(0,50).forEach(r=>{
      html+=`<tr>
        <td class="mono" style="font-size:10px;color:#556;white-space:nowrap">${esc((r.ts||'').substring(0,19))}</td>
        <td style="font-size:10px">${esc(r.source||r.log_type||'')}</td>
        <td class="mono" style="font-size:10px;color:#ffaa00">${esc(r.error_code||'—')}</td>
        <td class="mono" style="font-size:10px">${esc(r.oprid||'—')}</td>
        <td style="font-size:10px;color:#9ab;word-break:break-word">${esc((r.message||'').substring(0,150))}</td>
      </tr>`;
    });
    html+='</tbody></table></div>';
  }

  // Oracle ASH
  if(d.ash?.total_samples){
    html+=`<div class="section"><div class="section-hdr"><span>Oracle Activity (ASH) · ${esc(String(d.ash.db||''))}</span><span class="badge badge-info">${d.ash.total_samples} samples</span></div>`;
    const evts=d.ash.top_events||[];
    if(evts.length){
      evts.slice(0,8).forEach(ev=>{
        const col=WAIT_COLOR[ev.wait_class]||'#778';
        const barW=Math.min(ev.pct,100).toFixed(0);
        html+=`<div style="display:flex;align-items:center;gap:8px;margin:3px 0;font-size:11px">
          <div class="pct-bar"><div class="pct-fill" style="width:${barW}%;background:${col}"></div></div>
          <span style="color:${col};min-width:32px;font-size:10px">${ev.pct}%</span>
          <span style="color:#9ab">${esc(ev.event)}</span>
          <span style="color:#445;font-size:10px">${esc(ev.wait_class)}</span>
        </div>`;
      });
    }else{
      html+='<div style="color:#334;font-size:11px">No foreground activity.</div>';
    }
    html+='</div>';
  }

  // IB errors
  if((d.ib_errors||[]).length){
    html+=`<div class="section"><div class="section-hdr"><span>Integration Broker Errors</span><span class="badge badge-err">${d.ib_errors.length}</span></div>
    <table><thead><tr><th>Pub ID</th><th>Operation</th><th>Node</th><th>Status</th><th>Time</th></tr></thead><tbody>`;
    d.ib_errors.forEach(r=>{
      html+=`<tr>
        <td class="mono" style="font-size:10px;color:#445">${esc(String(r.ibtransactionid||'').substring(0,12))}</td>
        <td class="mono" style="font-size:10px;color:#00e5ff">${esc(r.ib_operationname||'')}</td>
        <td style="font-size:10px">${esc(r.origpubnode||'→')} → ${esc(r.pubnode||'')}</td>
        <td><span class="badge badge-err">${esc(String(r.pubstatus||''))}</span></td>
        <td class="mono" style="font-size:10px;color:#445">${esc(String(r.createdttm||'').substring(0,19))}</td>
      </tr>`;
    });
    html+='</tbody></table></div>';
  }

  document.getElementById('result').innerHTML=html;
}

window.onEnvChange=()=>{/* env change clears nothing — user re-investigates */};

async function saveAsIncident(){
  const env=window.dsGetEnv?window.dsGetEnv():'HCM';
  const startRaw=document.getElementById('startDt').value;
  const endRaw=document.getElementById('endDt').value;
  const start=new Date(startRaw).toISOString().replace('T',' ').substring(0,19);
  const end=new Date(endRaw).toISOString().replace('T',' ').substring(0,19);
  const title=prompt('Incident title:','Incident '+new Date().toISOString().substring(0,16));
  if(!title) return;
  const sev=prompt('Severity (P1/P2/P3/P4):','P3')||'P3';
  const btn=document.getElementById('saveBtn');
  btn.disabled=true; btn.textContent='Saving…';
  try{
    const res=await fetch('/api/incidents',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title,env,severity:sev,window_start:start,window_end:end,capture_rca:true})
    });
    const d=await res.json();
    if(!res.ok) throw new Error(d.detail||'Failed');
    window.location.href='/admin/incidents/'+d.id;
  }catch(e){alert('Error: '+e);btn.disabled=false;btn.textContent='📋 Save as Incident';}
}
</script>
""")
