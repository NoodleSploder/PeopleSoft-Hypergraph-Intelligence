"""
PeopleSoft App Server / Process Scheduler process-level tracking.

Existing runtime intelligence (connectors/psdb.app_server_domains) only sees
domain-level topology from PSPMDOMAIN_VW — an Oracle view, not the live OS.
This connector goes one level deeper via SSH `ps` to list the actual Tuxedo
worker processes (PSAPPSRV, PSAESRV, PSSAMSRV, WSL, BBL, PSMONITORSRV, ...),
their PID/CPU/MEM/uptime, and the domain/database/server-group metadata
Tuxedo encodes in each process's command line.

Read-only (`ps -eo ...`), no domain control actions (start/stop/kill) are
exposed — this is observability only, matching the platform's read-only rule.
"""

import re

# Tuxedo server process names PeopleSoft app server / process scheduler
# domains run. Anything not in this list is left out of the "known process"
# view (the OS also runs plenty of non-PeopleSoft processes we don't care
# about) but callers can still see raw counts via list_all_tuxedo().
_KNOWN_SERVERS = {
    "BBL":            "Bulletin Board Liaison (domain controller)",
    "WSL":            "Workstation Listener (client connection listener)",
    "WSH":            "Workstation Handler",
    "PSAPPSRV":       "Application Server (COBOL/PeopleCode request processor)",
    "PSSAMSRV":       "Service Agent Monitor Server",
    "PSMONITORSRV":   "PeopleSoft Monitor Server",
    "PSQCKSRV":       "Quick Server (lightweight PeopleCode requests)",
    "PSQRYSRV":       "Query Server",
    "PSANLSRV":       "Analytic Server",
    "PSAESRV":        "Application Engine Server (batch AE processing)",
    "PSMSTPRC":       "Process Scheduler Master Process",
    "PSDSTSRV":       "Distribution Server (report/output distribution)",
    "PSSCHDLR":       "Process Scheduler Server",
    "PSBRKHND":       "Integration Broker Handler",
    "JSL":            "Jolt Station Listener",
    "JSH":            "Jolt Station Handler",
    "JREPSVR":        "Jolt Repository Server",
}

# Tuxedo infrastructure/gateway processes where "-S" means something other
# than a server-name variant (shared-memory key, buffer size, worker count,
# etc.) — unlike the actual PeopleSoft app-level servers (PSAPPSRV, PSAESRV,
# PSBRKHND, ...) where "-S NAME" is a legitimate, more specific server-group
# name (e.g. "PSBRKHND_dflt"). Only apply the -S override outside this set.
_NO_S_OVERRIDE = {"BBL", "WSL", "WSH", "JSL", "JSH", "JREPSVR"}

_RE_DOM  = re.compile(r'-C\s+dom=(\S+)')
_RE_GRP  = re.compile(r'-g\s+(\d+)')
_RE_SRVID = re.compile(r'-i\s+(\d+)')
_RE_DBNAME = re.compile(r'-D\s+(\S+)')
_RE_CDNAME = re.compile(r'-CD\s+(\S+)')
_RE_PSNAME = re.compile(r'-PS\s+(\S+)')
_RE_SNAME  = re.compile(r'-S\s+(\S+)')

_PS_PATTERN = "|".join(re.escape(name) for name in _KNOWN_SERVERS)
_RE_PS_LINE_NAME = re.compile(rf'\b({_PS_PATTERN})\b')


def _parse_ps_line(line: str) -> dict | None:
    """Parse one `ps -eo pid,ppid,pcpu,pmem,etime,cmd` line into a process dict."""
    parts = line.strip().split(None, 5)
    if len(parts) < 6:
        return None
    pid, ppid, pcpu, pmem, etime, cmd = parts

    m = _RE_PS_LINE_NAME.search(cmd)
    if not m:
        return None
    server_name = m.group(1)

    dom = _RE_DOM.search(cmd)
    grp = _RE_GRP.search(cmd)
    srvid = _RE_SRVID.search(cmd)
    db = _RE_DBNAME.search(cmd) or _RE_CDNAME.search(cmd)
    ps_name = _RE_PSNAME.search(cmd)
    s_flag = _RE_SNAME.search(cmd)

    domain_name = dom.group(1) if dom else ""
    is_process_scheduler = "/prcs/" in cmd or bool(ps_name)
    use_s_override = s_flag and server_name not in _NO_S_OVERRIDE

    return {
        "pid": int(pid) if pid.isdigit() else pid,
        "ppid": int(ppid) if ppid.isdigit() else ppid,
        "cpu_pct": float(pcpu) if _is_float(pcpu) else 0.0,
        "mem_pct": float(pmem) if _is_float(pmem) else 0.0,
        "etime": etime,
        "server_name": s_flag.group(1) if use_s_override else server_name,
        "server_role": _KNOWN_SERVERS.get(server_name, "Unknown Tuxedo server"),
        "domain_name": domain_name,
        "group_id": grp.group(1) if grp else None,
        "server_id": srvid.group(1) if srvid else None,
        "database": db.group(1) if db else (ps_name.group(1) if ps_name else None),
        "tier": "process_scheduler" if is_process_scheduler else "app_server",
    }


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def list_processes(ssh_host: str) -> dict:
    """
    Return live Tuxedo/PeopleSoft server processes on the given SSH host.

    Returns {"processes": [...], "warnings": [...]}. Never raises — a
    connection/command failure is reported as a warning, not an exception,
    per the platform's grant-aware / degrade-gracefully rule.
    """
    from connectors import sshclient

    cmd = "ps -eo pid,ppid,pcpu,pmem,etime,cmd --sort=-pcpu 2>/dev/null"
    try:
        out, err, status = sshclient.run_command(ssh_host, cmd, timeout=15)
    except Exception as exc:
        return {
            "processes": [],
            "warnings": [{
                "code": "ssh_command_failed",
                "message": f"Could not run `ps` on {ssh_host}: {exc}",
                "severity": "warning",
            }],
        }

    processes = []
    for line in out.splitlines()[1:] if out else []:
        parsed = _parse_ps_line(line)
        if parsed:
            processes.append(parsed)

    warnings = []
    if status != 0 and not processes:
        warnings.append({
            "code": "ps_command_nonzero",
            "message": f"`ps` exited {status} on {ssh_host}: {err.strip()[:200]}",
            "severity": "warning",
        })

    processes.sort(key=lambda p: (p["domain_name"], p["server_name"], p["server_id"] or ""))
    return {"processes": processes, "warnings": warnings}


def summarize(processes: list[dict]) -> dict:
    """Roll up process list into per-domain and per-server-type counts."""
    by_domain: dict[str, dict] = {}
    by_server: dict[str, int] = {}
    for p in processes:
        dom = p["domain_name"] or "(unknown)"
        d = by_domain.setdefault(dom, {"domain_name": dom, "tier": p["tier"],
                                        "process_count": 0, "total_cpu_pct": 0.0,
                                        "total_mem_pct": 0.0, "database": p.get("database")})
        d["process_count"] += 1
        d["total_cpu_pct"] += p["cpu_pct"]
        d["total_mem_pct"] += p["mem_pct"]
        by_server[p["server_name"]] = by_server.get(p["server_name"], 0) + 1

    return {
        "domains": sorted(by_domain.values(), key=lambda d: d["domain_name"]),
        "by_server_type": dict(sorted(by_server.items())),
        "total_processes": len(processes),
    }
