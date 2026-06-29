"""
Transaction Tracing connector.
"""

from connectors import oracle as oracle_connector
from connectors import psdb, ptmetadata
from connectors.execution import _clean, _db_by_name, RUNSTATUS_LABELS, ACTIVE_STATUSES, ERROR_STATUSES


EVENT_TYPES = {
    "login":    {"label": "Sign On",        "color": "#00cc66",  "icon": "&#9654;"},
    "logout":   {"label": "Sign Off",       "color": "#556677",  "icon": "&#9664;"},
    "process":  {"label": "Process Run",    "color": "#00e5ff",  "icon": "&#9881;"},
    "oracle":   {"label": "Oracle Session", "color": "#bb88ff",  "icon": "&#9670;"},
    "ib":       {"label": "IB Transaction", "color": "#ffaa00",  "icon": "&#8644;"},
}


def _status_class(runstatus):
    s = str(runstatus or "")
    if s in ACTIVE_STATUSES:
        return "warn"
    if s in ERROR_STATUSES:
        return "error"
    return "ok"


def operator_search(env, q="", limit=20):
    warnings = []
    if not ptmetadata.has_table(env, "PSOPRDEFN"):
        warnings.append(ptmetadata.warning("NO_PSOPRDEFN", "PSOPRDEFN not accessible"))
        return {"items": [], "warnings": warnings}

    columns = psdb.select_existing_columns(
        env, "PSOPRDEFN",
        ["OPRDEFNDESC", "EMPLID", "EMAILID"],
        required=["OPRID"],
    )
    predicates = ["UPPER(OPRID) LIKE :pattern"]
    if "OPRDEFNDESC" in columns:
        predicates.append("UPPER(OPRDEFNDESC) LIKE :pattern")
    if "EMAILID" in columns:
        predicates.append("UPPER(EMAILID) LIKE :pattern")

    sql = f"""
        SELECT {", ".join(columns)}
        FROM SYSADM.PSOPRDEFN
        WHERE {" OR ".join(predicates)}
        ORDER BY OPRID
        FETCH FIRST :limit ROWS ONLY
    """
    try:
        return {
            "items": _clean(psdb.query(env, sql, {
                "pattern": f"%{q.upper()}%",
                "limit": int(limit),
            })),
            "warnings": warnings,
        }
    except Exception as exc:
        warnings.append(ptmetadata.warning("PSOPRDEFN_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def access_history(env, oprid, hours_back=24):
    warnings = []
    if not ptmetadata.has_table(env, "PSACCESSLOG"):
        warnings.append(ptmetadata.warning("NO_PSACCESSLOG", "PSACCESSLOG not accessible"))
        return {"items": [], "warnings": warnings}

    sql = """
        SELECT OPRID, LOGIPADDRESS, LOGINDTTM, LOGOUTDTTM,
               PT_TRACING_ID, PT_SIGNON_TYPE, PT_SIGNOUT_REASON
        FROM SYSADM.PSACCESSLOG
        WHERE UPPER(OPRID) = :oprid
          AND LOGINDTTM >= SYSTIMESTAMP - NUMTODSINTERVAL(:hours_back, 'HOUR')
        ORDER BY LOGINDTTM DESC
        FETCH FIRST 100 ROWS ONLY
    """
    try:
        rows = _clean(psdb.query(env, sql, {
            "oprid": oprid.upper(),
            "hours_back": int(hours_back),
        }))
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("PSACCESSLOG_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def process_history(env, oprid, hours_back=24):
    warnings = []
    if not ptmetadata.has_table(env, "PSPRCSRQST"):
        warnings.append(ptmetadata.warning("NO_PSPRCSRQST", "PSPRCSRQST not accessible"))
        return {"items": [], "warnings": warnings}

    sql = """
        SELECT PRCSINSTANCE, PRCSTYPE, PRCSNAME, OPRID, RUNCNTLID,
               RUNSTATUS, BEGINDTTM, ENDDTTM, RQSTDTTM, SERVERNAMERUN
        FROM SYSADM.PSPRCSRQST
        WHERE UPPER(OPRID) = :oprid
          AND NVL(BEGINDTTM, RQSTDTTM) >= SYSDATE - (:hours_back / 24)
        ORDER BY NVL(BEGINDTTM, RQSTDTTM) DESC
        FETCH FIRST 100 ROWS ONLY
    """
    try:
        rows = _clean(psdb.query(env, sql, {
            "oprid": oprid.upper(),
            "hours_back": int(hours_back),
        }))
        for r in rows:
            rs = str(r.get("runstatus") or "")
            r["runstatus_label"] = RUNSTATUS_LABELS.get(rs, f"Status {rs}")
            r["status_class"] = _status_class(rs)
            r["serverbatch"] = r.get("servernamerun", "")
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("PSPRCSRQST_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def oracle_sessions_for_oprid(db_name, oprid=None):
    warnings = []
    try:
        db = _db_by_name(db_name)
    except ValueError as exc:
        return {"items": [], "db": db_name, "warnings": [ptmetadata.warning("DB_NOT_FOUND", str(exc))]}

    where = ""
    if oprid:
        safe_oprid = oprid.upper().replace("'", "''")
        where = f"AND UPPER(s.CLIENT_IDENTIFIER) = '{safe_oprid}'"

    sql = f"""
        SELECT
            s.SID,
            s.SERIAL# AS SERIAL_NUM,
            s.USERNAME,
            s.STATUS,
            s.PROGRAM,
            s.MODULE,
            s.ACTION,
            s.MACHINE,
            s.CLIENT_IDENTIFIER,
            s.CLIENT_INFO,
            s.SQL_ID,
            s.EVENT,
            s.WAIT_CLASS,
            s.SECONDS_IN_WAIT,
            TO_CHAR(s.LOGON_TIME, 'YYYY-MM-DD HH24:MI:SS') AS LOGON_TIME,
            SUBSTR(q.SQL_TEXT, 1, 400) AS SQL_TEXT
        FROM V$SESSION s
        LEFT JOIN V$SQL q
          ON q.SQL_ID = s.SQL_ID
         AND q.CHILD_NUMBER = s.SQL_CHILD_NUMBER
        WHERE s.TYPE = 'USER'
          {where}
        ORDER BY s.LOGON_TIME DESC
        FETCH FIRST 50 ROWS ONLY
    """
    try:
        rows = _clean(oracle_connector.query_db(db, sql))
        return {"items": rows, "db": db_name, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("ORACLE_SESSIONS_ERR", str(exc), severity="error"))
        return {"items": [], "db": db_name, "warnings": warnings}


def ib_transactions_for_oprid(env, oprid, hours_back=24, limit=50):
    warnings = []
    if not ptmetadata.has_table(env, "PSAPMSGPUBHDR"):
        warnings.append(ptmetadata.warning("NO_PSAPMSGPUBHDR", "PSAPMSGPUBHDR not accessible — IB data unavailable"))
        return {"items": [], "warnings": warnings}

    sql = """
        SELECT IBTRANSACTIONID, IB_OPERATIONNAME, PUBNODE, QUEUENAME,
               PUBSTATUS, CREATEDTTM, PUBLISHER
        FROM SYSADM.PSAPMSGPUBHDR
        WHERE UPPER(PUBLISHER) = :oprid
          AND CREATEDTTM >= SYSDATE - :hours_frac
        ORDER BY CREATEDTTM DESC
        FETCH FIRST :limit ROWS ONLY
    """
    try:
        rows = _clean(psdb.query(env, sql, {
            "oprid": oprid.upper(),
            "hours_frac": float(hours_back) / 24.0,
            "limit": int(limit),
        }))
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("PSAPMSGPUBHDR_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def _to_timeline_event(event_type, ts, title, subtitle=None, status="info", detail=None, links=None):
    return {
        "type": event_type,
        "ts": ts or "",
        "title": title,
        "subtitle": subtitle or "",
        "status": status,
        "detail": detail or {},
        "links": links or [],
        "meta": EVENT_TYPES.get(event_type, {}),
    }



def recent_active_operators(env, limit=30):
    warnings = []
    if not ptmetadata.has_table(env, "PSACCESSLOG"):
        warnings.append(ptmetadata.warning("NO_PSACCESSLOG", "PSACCESSLOG not accessible"))
        return {"items": [], "warnings": warnings}

    sql = """
        SELECT OPRID,
               MAX(LOGINDTTM) AS LAST_ACTIVITY,
               COUNT(*) AS ACTIVITY_COUNT
        FROM SYSADM.PSACCESSLOG
        WHERE LOGINDTTM >= SYSTIMESTAMP - INTERVAL '24' HOUR
        GROUP BY OPRID
        ORDER BY MAX(LOGINDTTM) DESC
        FETCH FIRST :limit ROWS ONLY
    """
    try:
        rows = _clean(psdb.query(env, sql, {"limit": int(limit)}))
        for row in rows:
            row["last_login"] = row.get("last_activity")
            row["session_count"] = row.get("activity_count")
            row["is_active"] = False
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("RECENT_ACTIVE_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}

def trace(env, db_name, oprid, hours_back=24):
    all_warnings = []
    events = []

    al = access_history(env, oprid, hours_back=hours_back)
    all_warnings.extend(al.get("warnings", []))
    for row in al.get("items", []):
        ts_in = row.get("logindttm") or ""
        ts_out = row.get("logoutdttm")
        events.append(_to_timeline_event("login", ts_in, "Signed in", "", "ok" if ts_out else "info", row))
        if ts_out:
            events.append(_to_timeline_event("logout", ts_out, "Signed out", "", "ok", row))

    ph = process_history(env, oprid, hours_back=hours_back)
    all_warnings.extend(ph.get("warnings", []))
    for row in ph.get("items", []):
        ts = row.get("begindttm") or row.get("rqstdttm") or row.get("enddttm") or ""
        events.append(_to_timeline_event(
            "process",
            ts,
            f"{row.get('prcstype','')} {row.get('prcsname','')}".strip(),
            f"#{row.get('prcsinstance','')} · {row.get('runstatus_label','')} · {row.get('servernamerun','')}",
            row.get("status_class") or "info",
            row,
            [{"label": "View in Runtime", "url": "/admin/runtime"}],
        ))

    if db_name:
        os_ = oracle_sessions_for_oprid(db_name, oprid=oprid)
        all_warnings.extend(os_.get("warnings", []))
        for row in os_.get("items", []):
            events.append(_to_timeline_event(
                "oracle",
                row.get("logon_time") or "",
                f"SID {row.get('sid')} / {row.get('serial_num')}",
                f"{row.get('username','')} · {row.get('status','')} · {row.get('program','')}",
                "info",
                row,
            ))

    ib = ib_transactions_for_oprid(env, oprid, hours_back=hours_back)
    all_warnings.extend(ib.get("warnings", []))
    for row in ib.get("items", []):
        events.append(_to_timeline_event(
            "ib",
            row.get("createdttm") or "",
            row.get("ib_operationname") or "IB Transaction",
            f"{row.get('pubnode','')} · {row.get('queuename','')} · {row.get('pubstatus','')}",
            "info",
            row,
        ))

    events.sort(key=lambda e: e["ts"] if e["ts"] else "0000", reverse=True)

    summary = {
        "login_count": sum(1 for e in events if e["type"] == "login"),
        "process_count": sum(1 for e in events if e["type"] == "process"),
        "error_count": sum(1 for e in events if e["type"] == "process" and e["status"] == "error"),
        "oracle_count": sum(1 for e in events if e["type"] == "oracle"),
        "ib_count": sum(1 for e in events if e["type"] == "ib"),
        "total": len(events),
    }

    return {
        "oprid": oprid.upper(),
        "env": env,
        "db": db_name,
        "hours_back": hours_back,
        "summary": summary,
        "timeline": events,
        "warnings": all_warnings,
    }
