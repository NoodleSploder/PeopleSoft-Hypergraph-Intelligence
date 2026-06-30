"""
Integration Broker connector — grant-aware reader for PeopleSoft IB metadata and runtime tables.

Table map (SYSADM schema):
  PSIBAPPLDEFN   — Application/Service definitions     (PTIBAPPLNAME)
  PSIBAPPLOPR    — Service operations within a service  (PTIBAPPLNAME, PTIBAPPLOPR)
  PSIBRTNGDEFN   — Routing definitions                 (ROUTINGDEFNNAME)
  PSIBRTNGSUBDEFN— Routing sub-definitions
  PSMSGNODEDEFN  — Node definitions                    (MSGNODENAME)
  PSQUEUEDEFN    — Queue definitions                   (QUEUENAME)
  PSIBGROUPDEFN  — Integration group definitions
  PSAPMSGPUBHDR  — IB transaction headers (runtime)   (IBTRANSACTIONID)
  PSAPMSGPUBCON  — Publication contracts (runtime)
  PSAPMSGSUBCON  — Subscription contracts (runtime)
  PSAPMSGDOMSTAT — Domain status (runtime)

All functions use has_table() before touching any table; missing-grant scenarios
return structured warnings instead of raising exceptions.
"""

from connectors import psdb, ptmetadata

# ──────────────────────────────────────────────────────────────────────────────
# Status / type decoders
# ──────────────────────────────────────────────────────────────────────────────

PUBSTATUS_LABELS = {
    "1": "New",
    "2": "Started",
    "3": "Done",
    "4": "Cancelled",
    "5": "Error",
    "6": "Retry",
    "7": "Timeout",
}

SUBCONSTATUS_LABELS = {
    "1": "New",
    "2": "Started",
    "3": "Done",
    "4": "Cancelled",
    "5": "Error",
    "6": "Retry",
}

PUBCONSTATUS_LABELS = SUBCONSTATUS_LABELS

QUEUESTATUS_LABELS = {
    "0": "Paused",
    "1": "Running",
    "2": "Halted",
}

NODE_TYPE_LABELS = {
    "0": "PeopleSoft",
    "1": "External (Rel 8+)",
    "2": "External (Pre-Rel 8)",
    "3": "Hub",
}

RTNGTYPE_LABELS = {
    "0": "Any to Local",
    "1": "Local to Any",
    "2": "Explicit (Named)",
    "3": "Any to Any",
    "4": "Subscription",
}

THRUPUT_LABELS = {
    "0": "Serial",
    "1": "Parallel",
}

APPLTYPE_LABELS = {
    "0": "REST",
    "1": "SOAP",
    "2": "Generic",
    "M": "REST",
}


def _eff(row):
    """Decode EFF_STATUS / STATUS / ACTIVE_NODE field to human-readable."""
    for key in ("eff_status", "status", "active_node"):
        val = str(row.get(key) or "").strip().upper()
        if val in ("A", "1"):
            return "Active"
        if val in ("I", "0"):
            return "Inactive"
    return "Unknown"


def _warn(code, msg, severity="warning"):
    return ptmetadata.warning(code, msg, severity=severity)


def _service_kind(row: dict) -> str:
    """Best-effort service family label used by the IB explorer."""
    if (row.get("ib_restmethod") or row.get("ib_restbase_url")):
        return "REST"
    raw = str(row.get("ptibappltype") or row.get("ib_rest_service") or "").strip().upper()
    if raw in ("0", "2", "M", "Y", "REST"):
        return "REST"
    if raw in ("1", "N", "SOAP"):
        return "Standard"
    return APPLTYPE_LABELS.get(raw, "Standard" if raw else "Unknown")


# ──────────────────────────────────────────────────────────────────────────────
# Application Service Definitions
# ──────────────────────────────────────────────────────────────────────────────

def services(env_name: str, q: str = "", limit: int = 100) -> dict:
    """Search application/service definitions from PSIBAPPLDEFN."""
    warnings = []
    limit = max(1, min(int(limit), 500))

    if not ptmetadata.has_table(env_name, "PSIBAPPLDEFN"):
        warnings.append(_warn("NO_PSIBAPPLDEFN",
            "SYSADM.PSIBAPPLDEFN not accessible — Integration Broker may not be configured"))
        return {"items": [], "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSIBAPPLDEFN",
        ["VERSION", "PTIBAPPLTYPE", "IB_SERVICENAME", "STATUS",
         "PTIB_CONSUMER", "PTIB_EXPORT", "OBJECTOWNERID",
         "LASTUPDDTTM", "LASTUPDOPRID", "DESCR", "DESCRLONG"],
        required=["PTIBAPPLNAME"],
    )

    pattern = f"%{q.upper()}%"
    predicates = ["upper(PTIBAPPLNAME) LIKE :pat"]
    if "DESCR" in columns:
        predicates.append("upper(DESCR) LIKE :pat")
    if "IB_SERVICENAME" in columns:
        predicates.append("upper(IB_SERVICENAME) LIKE :pat")

    sql = f"""
        SELECT {", ".join(columns)}
          FROM sysadm.PSIBAPPLDEFN
         WHERE {" OR ".join(predicates)}
         ORDER BY PTIBAPPLNAME
         FETCH FIRST {limit} ROWS ONLY
    """

    try:
        rows = psdb.query(env_name, sql, {"pat": pattern})
        for row in rows:
            row["status_label"] = _eff(row)
            row["appltype_label"] = APPLTYPE_LABELS.get(
                str(row.get("ptibappltype") or "").strip(), "Unknown")
            row["service_kind"] = _service_kind(row)
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("PSIBAPPLDEFN_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def service(env_name: str, applname: str) -> dict:
    """Return a single application service definition."""
    warnings = []

    if not ptmetadata.has_table(env_name, "PSIBAPPLDEFN"):
        warnings.append(_warn("NO_PSIBAPPLDEFN",
            "SYSADM.PSIBAPPLDEFN not accessible"))
        return {"item": None, "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSIBAPPLDEFN",
        ["VERSION", "PTIBAPPLTYPE", "IB_SERVICENAME", "STATUS",
         "PTIB_CONSUMER", "PTIB_EXPORT", "PTIB_EXPORT_CB",
         "PTIB_AUTHOPTION", "PTIB_APPSRVGRP", "IB_SSL",
         "OBJECTOWNERID", "LASTUPDDTTM", "LASTUPDOPRID", "DESCR", "DESCRLONG"],
        required=["PTIBAPPLNAME"],
    )

    try:
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSIBAPPLDEFN
             WHERE PTIBAPPLNAME = upper(:name)
        """, {"name": applname})

        if not rows:
            return {"item": None, "warnings": warnings}

        row = rows[0]
        row["status_label"] = _eff(row)
        row["appltype_label"] = APPLTYPE_LABELS.get(
            str(row.get("ptibappltype") or "").strip(), "Unknown")
        row["service_kind"] = _service_kind(row)

        # Load operations.
        row["operations"] = service_operations(env_name, applname).get("items", [])
        row["service_operations"] = _operations_for_service(
            env_name, applname, row.get("ib_servicename"))

        # Load routings that reference this service.
        row["routings"] = _routings_for_service(env_name, applname)

        return {"item": row, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("PSIBAPPLDEFN_ERR", str(exc), severity="error"))
        return {"item": None, "warnings": warnings}


def service_operations(env_name: str, applname: str) -> dict:
    """Return operations (PSIBAPPLOPR) for a service definition."""
    warnings = []

    if not ptmetadata.has_table(env_name, "PSIBAPPLOPR"):
        warnings.append(_warn("NO_PSIBAPPLOPR", "SYSADM.PSIBAPPLOPR not accessible"))
        return {"items": [], "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSIBAPPLOPR",
        ["IBTRANSACTIONID", "PTIBURLPARAMNAME", "STATUS",
         "PTIB_NOEXPORT", "PTIB_SRC_TYPE", "APPCLASSID",
         "IB_ACTION", "URL_ID", "IB_URI_TEMPLATE"],
        required=["PTIBAPPLNAME", "PTIBAPPLOPR"],
    )

    try:
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSIBAPPLOPR
             WHERE PTIBAPPLNAME = upper(:name)
             ORDER BY PTIBAPPLOPR
        """, {"name": applname})

        for row in rows:
            row["status_label"] = _eff(row)
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("PSIBAPPLOPR_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def _operations_for_service(env_name: str, applname: str, service_name: str = None) -> list:
    """Fetch first-class service operations associated with an application service."""
    names = [n for n in {str(applname or "").upper(), str(service_name or "").upper()} if n]
    items = []
    seen = set()
    by_op = {}

    if service_name and ptmetadata.has_table(env_name, "PSSERVICEOPR"):
        try:
            rows = psdb.query(env_name, """
                SELECT IB_SERVICENAME, IB_OPERATIONNAME
                  FROM sysadm.PSSERVICEOPR
                 WHERE upper(IB_SERVICENAME) = :service_name
                 ORDER BY IB_OPERATIONNAME
            """, {"service_name": str(service_name).upper()})
            for row in rows:
                op = row.get("ib_operationname")
                if op and op not in seen:
                    row["service_kind"] = _service_kind(row)
                    items.append(row)
                    seen.add(op)
                    by_op[op] = row
        except Exception:
            pass

    if ptmetadata.has_table(env_name, "PSOPERATION") and names:
        try:
            predicates = []
            params = {}
            for i, name in enumerate(names):
                params[f"n{i}"] = name
                predicates.append(f"upper(PTIBAPPLNAME) = :n{i}")
                predicates.append(f"upper(IB_SERVICENAME) = :n{i}")
            rows = psdb.query(env_name, f"""
                SELECT IB_OPERATIONNAME, IB_SERVICENAME, PTIBAPPLNAME, DEFAULTVER,
                       IB_RESTMETHOD, IB_REST_SERVICE, IB_ALIASNAME, DESCR
                  FROM sysadm.PSOPERATION
                 WHERE {" OR ".join(predicates)}
                 ORDER BY IB_OPERATIONNAME
                 FETCH FIRST 200 ROWS ONLY
            """, params)
            for row in rows:
                op = row.get("ib_operationname")
                if not op:
                    continue
                row["service_kind"] = _service_kind(row)
                if op in by_op:
                    by_op[op].update({k: v for k, v in row.items() if v not in (None, "")})
                else:
                    items.append(row)
                    seen.add(op)
                    by_op[op] = row
        except Exception:
            pass

    return items


# ──────────────────────────────────────────────────────────────────────────────
# Service Operations
# ──────────────────────────────────────────────────────────────────────────────

def operations(env_name: str, q: str = "", limit: int = 100) -> dict:
    """Search first-class Integration Broker service operations."""
    warnings = []
    limit = max(1, min(int(limit), 500))
    pattern = f"%{q.upper()}%"

    if ptmetadata.has_table(env_name, "PSOPERATION"):
        columns = psdb.select_existing_columns(
            env_name, "PSOPERATION",
            ["VERSION", "DEFAULTVER", "RTNGTYPE", "IB_RESTMETHOD", "IB_REST_SERVICE",
             "IB_SERVICENAME", "PTIBAPPLNAME", "IB_ALIASNAME", "MSGNAME", "IB_MSGVERSION",
             "OBJECTOWNERID", "LASTUPDDTTM", "LASTUPDOPRID", "DESCR"],
            required=["IB_OPERATIONNAME"],
        )
        predicates = ["upper(IB_OPERATIONNAME) LIKE :pat"]
        for col in ("IB_SERVICENAME", "PTIBAPPLNAME", "IB_ALIASNAME", "DESCR"):
            if col in columns:
                predicates.append(f"upper({col}) LIKE :pat")

        try:
            rows = psdb.query(env_name, f"""
                SELECT {", ".join(columns)}
                  FROM sysadm.PSOPERATION
                 WHERE {" OR ".join(predicates)}
                 ORDER BY IB_OPERATIONNAME
                 FETCH FIRST {limit} ROWS ONLY
            """, {"pat": pattern})
            for row in rows:
                row["service_kind"] = _service_kind(row)
                row["rtngtype_label"] = RTNGTYPE_LABELS.get(
                    str(row.get("rtngtype") or "").strip(), "Unknown")
                row["version_count"] = _operation_version_count(env_name, row.get("ib_operationname"))
                row["routing_count"] = _operation_routing_count(env_name, row.get("ib_operationname"))
            return {"items": rows, "warnings": warnings}
        except Exception as exc:
            warnings.append(_warn("PSOPERATION_ERR", str(exc), severity="error"))

    if not ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        warnings.append(_warn("NO_OPERATION_SOURCE",
            "No accessible service-operation source tables found"))
        return {"items": [], "warnings": warnings}

    try:
        rows = psdb.query(env_name, f"""
            SELECT IB_OPERATIONNAME,
                   MIN(VERSIONNAME) AS VERSIONNAME,
                   MIN(IB_RESTMETHOD) AS IB_RESTMETHOD,
                   MIN(EFF_STATUS) AS EFF_STATUS,
                   MIN(SENDERNODENAME) AS SAMPLE_SENDER,
                   MIN(RECEIVERNODENAME) AS SAMPLE_RECEIVER,
                   COUNT(*) AS ROUTING_COUNT
              FROM sysadm.PSIBRTNGDEFN
             WHERE upper(IB_OPERATIONNAME) LIKE :pat
                OR upper(ROUTINGDEFNNAME) LIKE :pat
             GROUP BY IB_OPERATIONNAME
             ORDER BY IB_OPERATIONNAME
             FETCH FIRST {limit} ROWS ONLY
        """, {"pat": pattern})
        for row in rows:
            row["status_label"] = _eff(row)
            row["service_kind"] = "REST" if row.get("ib_restmethod") else "Standard"
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("PSIBRTNGDEFN_OP_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def operation(env_name: str, opname: str) -> dict:
    """Return one service operation with versions, handlers, security, messages, and routings."""
    warnings = []
    opname = (opname or "").upper()
    item = _operation_header(env_name, opname, warnings)
    routings_data = ib_operation(env_name, opname)
    warnings.extend(routings_data.get("warnings", []))

    if not item and routings_data.get("item"):
        item = routings_data["item"]
        item["service_kind"] = "REST" if any(r.get("ib_restmethod") for r in routings_data.get("routings", [])) else "Standard"

    if not item:
        return {"item": None, "warnings": warnings}

    routings = routings_data.get("routings", [])
    item["routings"] = routings
    item["versions"] = _operation_versions(env_name, opname)
    item["handlers"] = _operation_handlers(env_name, opname, routings)
    item["security"] = _operation_security(env_name, opname)
    item["messages"] = _operation_messages(env_name, opname)
    item["runtime_queues"] = _operation_runtime_queues(env_name, opname)
    item["services"] = _services_for_operation(env_name, opname, item)
    item["routing_count"] = len(routings)
    return {"item": item, "warnings": warnings}


def _operation_header(env_name: str, opname: str, warnings: list) -> dict | None:
    if not ptmetadata.has_table(env_name, "PSOPERATION"):
        return None
    try:
        columns = psdb.select_existing_columns(
            env_name, "PSOPERATION",
            ["VERSION", "DEFAULTVER", "RTNGTYPE", "IB_RESTMETHOD", "IB_REST_SERVICE",
             "IB_RESTBASE_URL", "IB_SERVICENAME", "PTIBAPPLNAME", "IB_ALIASNAME",
             "MSGNAME", "IB_MSGVERSION", "OBJECTOWNERID", "LASTUPDDTTM",
             "LASTUPDOPRID", "DESCR", "DESCRLONG"],
            required=["IB_OPERATIONNAME"],
        )
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSOPERATION
             WHERE upper(IB_OPERATIONNAME) = :name
        """, {"name": opname})
        if not rows:
            return None
        row = rows[0]
        row["service_kind"] = _service_kind(row)
        row["rtngtype_label"] = RTNGTYPE_LABELS.get(
            str(row.get("rtngtype") or "").strip(), "Unknown")
        return row
    except Exception as exc:
        warnings.append(_warn("PSOPERATION_DETAIL_ERR", str(exc), severity="error"))
        return None


def _operation_version_count(env_name: str, opname: str) -> int | None:
    if not opname or not ptmetadata.has_table(env_name, "PSOPRVERDFN"):
        return None
    try:
        rows = psdb.query(env_name, """
            SELECT COUNT(*) AS cnt
              FROM sysadm.PSOPRVERDFN
             WHERE upper(IB_OPERATIONNAME) = :name
        """, {"name": str(opname).upper()})
        return rows[0]["cnt"] if rows else 0
    except Exception:
        return None


def _operation_routing_count(env_name: str, opname: str) -> int | None:
    if not opname or not ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        return None
    try:
        rows = psdb.query(env_name, """
            SELECT COUNT(*) AS cnt
              FROM sysadm.PSIBRTNGDEFN
             WHERE upper(IB_OPERATIONNAME) = :name
        """, {"name": str(opname).upper()})
        return rows[0]["cnt"] if rows else 0
    except Exception:
        return None


def _operation_versions(env_name: str, opname: str) -> list:
    if not ptmetadata.has_table(env_name, "PSOPRVERDFN"):
        return []
    try:
        columns = psdb.select_existing_columns(
            env_name, "PSOPRVERDFN",
            ["VERSIONNAME", "VERSION", "ACTIVE_FLAG", "NR_FLAG", "IB_VALIDATION",
             "IB_VALID_LEVEL", "IB_SYNCHNONBLOCK", "IB_MULTIQUEUE",
             "CLIENTIMPLEMENT", "IBDOCLAYOUTNAME", "OBJECTOWNERID",
             "LASTUPDDTTM", "LASTUPDOPRID", "DESCR"],
            required=["IB_OPERATIONNAME"],
        )
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSOPRVERDFN
             WHERE upper(IB_OPERATIONNAME) = :name
             ORDER BY VERSIONNAME
        """, {"name": opname})
        for row in rows:
            row["active_label"] = "Active" if str(row.get("active_flag") or "").upper() in ("A", "Y", "1") else "Inactive"
        return rows
    except Exception:
        return []


def _operation_handlers(env_name: str, opname: str, routings: list) -> list:
    handlers = []
    if ptmetadata.has_table(env_name, "PSOPRHDLR"):
        try:
            columns = psdb.select_existing_columns(
                env_name, "PSOPRHDLR",
                ["HANDLERNAME", "VERSION", "IB_HANDLERALIAS", "HANDLERID",
                 "HANDLEROWNER", "HANDLERTYPE", "ACTIVE_FLAG", "SEQNO",
                 "IB_ROLLBACK", "OBJECTOWNERID", "LASTUPDDTTM", "LASTUPDOPRID", "DESCR"],
                required=["IB_OPERATIONNAME"],
            )
            rows = psdb.query(env_name, f"""
                SELECT {", ".join(columns)}
                  FROM sysadm.PSOPRHDLR
                 WHERE upper(IB_OPERATIONNAME) = :name
                 ORDER BY VERSION, SEQNO, HANDLERNAME
            """, {"name": opname})
            for row in rows:
                row["source"] = "Handler"
                row["active_label"] = "Active" if str(row.get("active_flag") or "").upper() in ("A", "Y", "1") else "Inactive"
            handlers.extend(rows)
        except Exception:
            pass

    routing_handler_cols = [
        ("onsndhdlrname", "On Send"),
        ("onrcvhdlrname", "On Receive"),
        ("onprehdlrname", "On Pre"),
        ("onposthdlrname", "On Post"),
    ]
    seen = {(h.get("handlername"), h.get("handlertype"), h.get("version")) for h in handlers}
    for r in routings or []:
        for col, label in routing_handler_cols:
            name = (r.get(col) or "").strip()
            key = (name, label, r.get("versionname"))
            if name and key not in seen:
                seen.add(key)
                handlers.append({
                    "handlername": name,
                    "handlertype": label,
                    "version": r.get("versionname"),
                    "routingdefnname": r.get("routingdefnname"),
                    "source": "Routing",
                    "active_label": r.get("eff_status_label"),
                })
    return handlers


def _operation_security(env_name: str, opname: str) -> list:
    if ptmetadata.has_table(env_name, "PSSERVPERM_VW"):
        try:
            columns = psdb.select_existing_columns(
                env_name, "PSSERVPERM_VW",
                ["IB_SERVICENAME", "IB_INTGROUPNAME", "IB_INTGROUPSUBNAME",
                 "IB_NOPERMISSIONS", "IB_SERVICESECURITY", "SELECT_FLAG", "IB_REST_SERVICE"],
                required=["IB_OPERATIONNAME"],
            )
            rows = psdb.query(env_name, f"""
                SELECT {", ".join(columns)}
                  FROM sysadm.PSSERVPERM_VW
                 WHERE upper(IB_OPERATIONNAME) = :name
                 ORDER BY IB_SERVICENAME, IB_INTGROUPNAME, IB_INTGROUPSUBNAME
                 FETCH FIRST 200 ROWS ONLY
            """, {"name": opname})
            for row in rows:
                row["service_kind"] = _service_kind(row)
            return rows
        except Exception:
            return []
    if ptmetadata.has_table(env_name, "PSIBUSERCOMP"):
        try:
            columns = psdb.select_existing_columns(
                env_name, "PSIBUSERCOMP",
                ["VERSIONNAME", "ACTIVE_FLAG", "MENUNAME", "BARNAME",
                 "BARITEMNAME", "PNLITEMNAME", "ACTIONS"],
                required=["IB_OPERATIONNAME"],
            )
            rows = psdb.query(env_name, f"""
                SELECT {", ".join(columns)}
                  FROM sysadm.PSIBUSERCOMP
                 WHERE upper(IB_OPERATIONNAME) = :name
                 ORDER BY VERSIONNAME, MENUNAME, PNLITEMNAME
            """, {"name": opname})
            return rows
        except Exception:
            return []
    return []


def _operation_messages(env_name: str, opname: str) -> list:
    messages = []
    if ptmetadata.has_table(env_name, "PSOPRVERMSGS_VW"):
        try:
            rows = psdb.query(env_name, """
                SELECT IB_OPERATIONNAME, VERSIONNAME, IB_REQMSGNAME, INMSGVERSION,
                       IB_RESPMSGNAME, OUTMSGVERSION, IB_FLTMSGNAME, FLTMSGVERSION
                  FROM sysadm.PSOPRVERMSGS_VW
                 WHERE upper(IB_OPERATIONNAME) = :name
                 ORDER BY VERSIONNAME
            """, {"name": opname})
            for row in rows:
                messages.append(row)
        except Exception:
            pass

    if ptmetadata.has_table(env_name, "PSIBURITRAN"):
        try:
            rows = psdb.query(env_name, """
                SELECT IB_OPERATIONNAME, IBTRANSACTIONID, DESCR, DESCRLONG
                  FROM sysadm.PSIBURITRAN
                 WHERE upper(IB_OPERATIONNAME) = :name
                 ORDER BY IBTRANSACTIONID
            """, {"name": opname})
            for row in rows:
                row["source"] = "URI Transaction"
                messages.append(row)
        except Exception:
            pass

    if ptmetadata.has_table(env_name, "PSSRVQUEUE_VW"):
        try:
            rows = psdb.query(env_name, """
                SELECT QUEUENAME, IB_OPERATIONNAME, VERSIONNAME
                  FROM sysadm.PSSRVQUEUE_VW
                 WHERE upper(IB_OPERATIONNAME) = :name
                 ORDER BY VERSIONNAME, QUEUENAME
            """, {"name": opname})
            for row in rows:
                row["source"] = "Queue"
                messages.append(row)
        except Exception:
            pass
    return messages


def _operation_runtime_queues(env_name: str, opname: str) -> list:
    if not ptmetadata.has_table(env_name, "PSAPMSGPUBHDR"):
        return []
    try:
        rows = psdb.query(env_name, """
            SELECT QUEUENAME, PUBSTATUS, COUNT(*) AS CNT, MAX(CREATEDTTM) AS LAST_CREATED
              FROM sysadm.PSAPMSGPUBHDR
             WHERE upper(IB_OPERATIONNAME) = :name
             GROUP BY QUEUENAME, PUBSTATUS
             ORDER BY QUEUENAME, PUBSTATUS
             FETCH FIRST 100 ROWS ONLY
        """, {"name": opname})
        for row in rows:
            row["pubstatus_label"] = PUBSTATUS_LABELS.get(
                str(row.get("pubstatus") or "").strip(), "Unknown")
        return rows
    except Exception:
        return []


def _services_for_operation(env_name: str, opname: str, item: dict) -> list:
    services_out = []
    if ptmetadata.has_table(env_name, "PSSERVICEOPR"):
        try:
            rows = psdb.query(env_name, """
                SELECT IB_SERVICENAME, IB_OPERATIONNAME
                  FROM sysadm.PSSERVICEOPR
                 WHERE upper(IB_OPERATIONNAME) = :name
                 ORDER BY IB_SERVICENAME
            """, {"name": opname})
            services_out.extend(rows)
        except Exception:
            pass
    svc = item.get("ib_servicename")
    appl = item.get("ptibapplname")
    if svc or appl:
        candidate = {"ib_servicename": svc, "ptibapplname": appl, "ib_operationname": opname}
        if candidate not in services_out:
            services_out.append(candidate)
    return services_out


def _routings_for_service(env_name: str, applname: str) -> list:
    """Internal: fetch routing definitions that reference this application service."""
    if not ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        return []
    try:
        rows = psdb.query(env_name, """
            SELECT ROUTINGDEFNNAME, SENDERNODENAME, RECEIVERNODENAME,
                   EFF_STATUS, RTNGTYPE, EFFDT
              FROM sysadm.PSIBRTNGDEFN
             WHERE IB_OPERATIONNAME = upper(:name)
             ORDER BY EFFDT DESC, ROUTINGDEFNNAME
             FETCH FIRST 50 ROWS ONLY
        """, {"name": applname})
        for row in rows:
            row["eff_status_label"] = _eff(row)
            row["rtngtype_label"] = RTNGTYPE_LABELS.get(
                str(row.get("rtngtype") or "").strip(), "Unknown")
        return rows
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Routing Definitions
# ──────────────────────────────────────────────────────────────────────────────

def routings(env_name: str, q: str = "", limit: int = 100) -> dict:
    """Search routing definitions from PSIBRTNGDEFN."""
    warnings = []
    limit = max(1, min(int(limit), 500))

    if not ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        warnings.append(_warn("NO_PSIBRTNGDEFN",
            "SYSADM.PSIBRTNGDEFN not accessible — Integration Broker may not be configured"))
        return {"items": [], "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSIBRTNGDEFN",
        ["EFFDT", "VERSION", "EFF_STATUS", "SENDERNODENAME", "RECEIVERNODENAME",
         "RTNGTYPE", "IB_OPERATIONNAME", "VERSIONNAME", "IB_RESTMETHOD",
         "IB_DELIVERYMODE", "OBJECTOWNERID", "LASTUPDDTTM", "LASTUPDOPRID",
         "DESCR"],
        required=["ROUTINGDEFNNAME"],
    )

    pattern = f"%{q.upper()}%"
    predicates = ["upper(ROUTINGDEFNNAME) LIKE :pat"]
    if "IB_OPERATIONNAME" in columns:
        predicates.append("upper(IB_OPERATIONNAME) LIKE :pat")
    if "SENDERNODENAME" in columns:
        predicates.append("upper(SENDERNODENAME) LIKE :pat")
    if "RECEIVERNODENAME" in columns:
        predicates.append("upper(RECEIVERNODENAME) LIKE :pat")

    sql = f"""
        SELECT {", ".join(columns)}
          FROM sysadm.PSIBRTNGDEFN
         WHERE ({" OR ".join(predicates)})
         ORDER BY ROUTINGDEFNNAME, EFFDT DESC
         FETCH FIRST {limit} ROWS ONLY
    """

    try:
        rows = psdb.query(env_name, sql, {"pat": pattern})
        for row in rows:
            row["eff_status_label"] = _eff(row)
            row["rtngtype_label"] = RTNGTYPE_LABELS.get(
                str(row.get("rtngtype") or "").strip(), "Unknown")
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("PSIBRTNGDEFN_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def routing(env_name: str, rtngname: str) -> dict:
    """Return a single routing definition with sub-definitions."""
    warnings = []

    if not ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        warnings.append(_warn("NO_PSIBRTNGDEFN", "SYSADM.PSIBRTNGDEFN not accessible"))
        return {"item": None, "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSIBRTNGDEFN",
        ["EFFDT", "VERSION", "EFF_STATUS", "SENDERNODENAME", "RECEIVERNODENAME",
         "RTNGTYPE", "IB_OPERATIONNAME", "VERSIONNAME", "IB_RESTMETHOD",
         "IB_DELAYPROCESSING", "IB_SYNCHNONBLOCK", "IB_DELIVERYMODE",
         "CONNOVERRIDE", "CONNGATEWAYID", "CONNID", "LOGMSGDTLFLG",
         "ONSNDHDLRNAME", "ONRCVHDLRNAME", "ONPREHDLRNAME", "ONPOSTHDLRNAME",
         "OBJECTOWNERID", "LASTUPDDTTM", "LASTUPDOPRID", "DESCR", "DESCRLONG"],
        required=["ROUTINGDEFNNAME"],
    )

    try:
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSIBRTNGDEFN
             WHERE ROUTINGDEFNNAME = upper(:name)
             ORDER BY EFFDT DESC
             FETCH FIRST 1 ROWS ONLY
        """, {"name": rtngname})

        if not rows:
            return {"item": None, "warnings": warnings}

        row = rows[0]
        row["eff_status_label"] = _eff(row)
        row["rtngtype_label"] = RTNGTYPE_LABELS.get(
            str(row.get("rtngtype") or "").strip(), "Unknown")

        # Sub-definitions (additional node pairs).
        row["sub_definitions"] = _routing_sub(env_name, rtngname)

        return {"item": row, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("ROUTING_ERR", str(exc), severity="error"))
        return {"item": None, "warnings": warnings}


def _routing_sub(env_name: str, rtngname: str) -> list:
    if not ptmetadata.has_table(env_name, "PSIBRTNGSUBDEFN"):
        return []
    try:
        return psdb.query(env_name, """
            SELECT ROUTINGDEFNNAME, EFFDT, SEQNUM, IB_DIRECTION,
                   RTNGTYPE, SENDERNODENAME, RECEIVERNODENAME, ALIASNAME
              FROM sysadm.PSIBRTNGSUBDEFN
             WHERE ROUTINGDEFNNAME = upper(:name)
             ORDER BY EFFDT DESC, SEQNUM
        """, {"name": rtngname})
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Node Definitions
# ──────────────────────────────────────────────────────────────────────────────

def nodes(env_name: str, q: str = "", limit: int = 100) -> dict:
    """Search node definitions from PSMSGNODEDEFN."""
    warnings = []
    limit = max(1, min(int(limit), 500))

    if not ptmetadata.has_table(env_name, "PSMSGNODEDEFN"):
        warnings.append(_warn("NO_PSMSGNODEDEFN",
            "SYSADM.PSMSGNODEDEFN not accessible — Integration Broker may not be configured"))
        return {"items": [], "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSMSGNODEDEFN",
        ["VERSION", "DESCR", "ACTIVE_NODE", "LOCALNODE", "LOCALDEFAULTFLG",
         "NODE_TYPE", "TOOLSREL", "APMSGAPPREL", "IB_TGTLOCATION",
         "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["MSGNODENAME"],
    )

    pattern = f"%{q.upper()}%"
    predicates = ["upper(MSGNODENAME) LIKE :pat"]
    if "DESCR" in columns:
        predicates.append("upper(DESCR) LIKE :pat")

    sql = f"""
        SELECT {", ".join(columns)}
          FROM sysadm.PSMSGNODEDEFN
         WHERE {" OR ".join(predicates)}
         ORDER BY
           CASE WHEN LOCALNODE = 1 THEN 0 ELSE 1 END,
           MSGNODENAME
         FETCH FIRST {limit} ROWS ONLY
    """

    try:
        rows = psdb.query(env_name, sql, {"pat": pattern})
        for row in rows:
            row["active_label"] = "Active" if str(row.get("active_node") or "").upper() == "Y" else "Inactive"
            row["node_type_label"] = NODE_TYPE_LABELS.get(
                str(row.get("node_type") or "").strip(), "Unknown")
            row["is_local"] = str(row.get("localnode") or "").strip() in ("1", "Y")
            row["is_default"] = str(row.get("localdefaultflg") or "").upper() == "Y"
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("PSMSGNODEDEFN_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def node(env_name: str, nodename: str) -> dict:
    """Return a single node definition with routing associations."""
    warnings = []

    if not ptmetadata.has_table(env_name, "PSMSGNODEDEFN"):
        warnings.append(_warn("NO_PSMSGNODEDEFN", "SYSADM.PSMSGNODEDEFN not accessible"))
        return {"item": None, "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSMSGNODEDEFN",
        ["VERSION", "DESCR", "ACTIVE_NODE", "LOCALNODE", "LOCALDEFAULTFLG",
         "NODE_TYPE", "TOOLSREL", "APMSGAPPREL", "IB_TGTLOCATION",
         "AUTHOPTN", "IB_DEFLTEXTUSERID", "CONNGATEWAYID", "CONNID",
         "NETWORKNODENAME", "HUBNODENAME", "MASTERNODENAME",
         "IB_DELIVERYMODE", "IB_THROTTLEVALUE",
         "LASTUPDDTTM", "LASTUPDOPRID", "DESCRLONG"],
        required=["MSGNODENAME"],
    )

    try:
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSMSGNODEDEFN
             WHERE MSGNODENAME = upper(:name)
        """, {"name": nodename})

        if not rows:
            return {"item": None, "warnings": warnings}

        row = rows[0]
        row["active_label"] = "Active" if str(row.get("active_node") or "").upper() == "Y" else "Inactive"
        row["node_type_label"] = NODE_TYPE_LABELS.get(
            str(row.get("node_type") or "").strip(), "Unknown")
        row["is_local"] = str(row.get("localnode") or "").strip() in ("1", "Y")
        row["is_default"] = str(row.get("localdefaultflg") or "").upper() == "Y"

        # Routings that use this node.
        row["routings_as_sender"]   = _routings_for_node(env_name, nodename, "SENDERNODENAME")
        row["routings_as_receiver"] = _routings_for_node(env_name, nodename, "RECEIVERNODENAME")

        return {"item": row, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("NODE_ERR", str(exc), severity="error"))
        return {"item": None, "warnings": warnings}


def ib_operation(env_name: str, opname: str) -> dict:
    """Look up a traditional IB service operation via PSIBRTNGDEFN.IB_OPERATIONNAME.

    Used as a fallback when the name doesn't exist in PSIBAPPLDEFN (Application Services).
    Returns routings, queue names, and node names that reference this service operation.
    """
    warnings = []
    opname = opname.upper()

    if not ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        return {"item": None, "routings": [], "warnings": [
            _warn("NO_PSIBRTNGDEFN", "SYSADM.PSIBRTNGDEFN not accessible")]}

    try:
        columns = psdb.select_existing_columns(
            env_name, "PSIBRTNGDEFN",
            ["IB_OPERATIONNAME", "ROUTINGDEFNNAME", "EFF_STATUS", "SENDERNODENAME",
             "RECEIVERNODENAME", "RTNGTYPE", "VERSIONNAME", "QUEUENAME",
             "IB_RESTMETHOD", "IB_DELIVERYMODE", "LASTUPDDTTM"],
            required=["IB_OPERATIONNAME", "ROUTINGDEFNNAME"],
        )
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSIBRTNGDEFN
             WHERE upper(IB_OPERATIONNAME) = :name
             ORDER BY ROUTINGDEFNNAME
             FETCH FIRST 200 ROWS ONLY
        """, {"name": opname})

        for row in rows:
            row["eff_status_label"] = _eff(row)
            row["rtngtype_label"] = RTNGTYPE_LABELS.get(
                str(row.get("rtngtype") or "").strip(), "Unknown")

        if not rows:
            return {"item": None, "routings": [], "warnings": warnings}

        # Aggregate metadata from routings
        queues = sorted({r.get("queuename") or "" for r in rows if r.get("queuename") and r.get("queuename").strip()})
        senders = sorted({r.get("sendernodename") or "" for r in rows if r.get("sendernodename") and r.get("sendernodename").strip()})
        receivers = sorted({r.get("receivernodename") or "" for r in rows if r.get("receivernodename") and r.get("receivernodename").strip()})

        item = {
            "ib_operationname": opname,
            "routing_count": len(rows),
            "queues": queues,
            "sender_nodes": senders,
            "receiver_nodes": receivers,
        }

        return {"item": item, "routings": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("IB_OPERATION_ERR", str(exc), severity="error"))
        return {"item": None, "routings": [], "warnings": warnings}


def _routings_for_node(env_name: str, nodename: str, column: str) -> list:
    if not ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        return []
    try:
        rows = psdb.query(env_name, f"""
            SELECT ROUTINGDEFNNAME, IB_OPERATIONNAME, EFF_STATUS,
                   SENDERNODENAME, RECEIVERNODENAME
              FROM sysadm.PSIBRTNGDEFN
             WHERE {column} = upper(:name)
             ORDER BY ROUTINGDEFNNAME
             FETCH FIRST 100 ROWS ONLY
        """, {"name": nodename})
        for row in rows:
            row["eff_status_label"] = _eff(row)
        return rows
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Queue Definitions
# ──────────────────────────────────────────────────────────────────────────────

def queues(env_name: str, q: str = "", limit: int = 100) -> dict:
    """Search queue definitions from PSQUEUEDEFN."""
    warnings = []
    limit = max(1, min(int(limit), 500))

    if not ptmetadata.has_table(env_name, "PSQUEUEDEFN"):
        warnings.append(_warn("NO_PSQUEUEDEFN",
            "SYSADM.PSQUEUEDEFN not accessible — Integration Broker may not be configured"))
        return {"items": [], "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSQUEUEDEFN",
        ["VERSION", "QUEUESTATUS", "THRUPUTTYPE", "ARCHIVE",
         "IB_PURGE_DATA", "OBJECTOWNERID", "LASTUPDDTTM", "LASTUPDOPRID",
         "DESCR"],
        required=["QUEUENAME"],
    )

    pattern = f"%{q.upper()}%"
    predicates = ["upper(QUEUENAME) LIKE :pat"]
    if "DESCR" in columns:
        predicates.append("upper(DESCR) LIKE :pat")

    sql = f"""
        SELECT {", ".join(columns)}
          FROM sysadm.PSQUEUEDEFN
         WHERE {" OR ".join(predicates)}
         ORDER BY QUEUENAME
         FETCH FIRST {limit} ROWS ONLY
    """

    try:
        rows = psdb.query(env_name, sql, {"pat": pattern})
        for row in rows:
            row["queuestatus_label"] = QUEUESTATUS_LABELS.get(
                str(row.get("queuestatus") or "").strip(), "Unknown")
            row["thruput_label"] = THRUPUT_LABELS.get(
                str(row.get("thruputtype") or "").strip(), "Unknown")
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("PSQUEUEDEFN_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def queue(env_name: str, queuename: str) -> dict:
    """Return a single queue definition with runtime depth."""
    warnings = []

    if not ptmetadata.has_table(env_name, "PSQUEUEDEFN"):
        warnings.append(_warn("NO_PSQUEUEDEFN", "SYSADM.PSQUEUEDEFN not accessible"))
        return {"item": None, "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSQUEUEDEFN",
        ["VERSION", "QUEUESTATUS", "THRUPUTTYPE", "ARCHIVE",
         "IB_PURGE_DATA", "PTIB_QUEUE_PRI", "OBJECTOWNERID",
         "LASTUPDDTTM", "LASTUPDOPRID", "DESCR", "DESCRLONG"],
        required=["QUEUENAME"],
    )

    try:
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSQUEUEDEFN
             WHERE QUEUENAME = upper(:name)
        """, {"name": queuename})

        if not rows:
            return {"item": None, "warnings": warnings}

        row = rows[0]
        row["queuestatus_label"] = QUEUESTATUS_LABELS.get(
            str(row.get("queuestatus") or "").strip(), "Unknown")
        row["thruput_label"] = THRUPUT_LABELS.get(
            str(row.get("thruputtype") or "").strip(), "Unknown")

        # Runtime depth from pub/sub tables.
        row["runtime"] = queue_depth(env_name, queuename)

        return {"item": row, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("QUEUE_ERR", str(exc), severity="error"))
        return {"item": None, "warnings": warnings}


def queue_depth(env_name: str, queuename: str) -> dict:
    """Return runtime message counts for a queue, grouped by status."""
    result = {"pub_by_status": [], "sub_by_status": [], "warnings": []}

    if ptmetadata.has_table(env_name, "PSAPMSGPUBHDR"):
        try:
            rows = psdb.query(env_name, """
                SELECT PUBSTATUS, COUNT(*) AS CNT
                  FROM sysadm.PSAPMSGPUBHDR
                 WHERE QUEUENAME = upper(:q)
                 GROUP BY PUBSTATUS
                 ORDER BY PUBSTATUS
            """, {"q": queuename})
            for row in rows:
                row["status_label"] = PUBSTATUS_LABELS.get(
                    str(row.get("pubstatus") or "").strip(), "Unknown")
            result["pub_by_status"] = rows
        except Exception as exc:
            result["warnings"].append(str(exc))

    if ptmetadata.has_table(env_name, "PSAPMSGSUBCON"):
        try:
            rows = psdb.query(env_name, """
                SELECT SUBCONSTATUS, COUNT(*) AS CNT
                  FROM sysadm.PSAPMSGSUBCON
                 WHERE QUEUENAME = upper(:q)
                 GROUP BY SUBCONSTATUS
                 ORDER BY SUBCONSTATUS
            """, {"q": queuename})
            for row in rows:
                row["status_label"] = SUBCONSTATUS_LABELS.get(
                    str(row.get("subconstatus") or "").strip(), "Unknown")
            result["sub_by_status"] = rows
        except Exception as exc:
            result["warnings"].append(str(exc))

    return result


# ──────────────────────────────────────────────────────────────────────────────
# IB Transaction Log (runtime)
# ──────────────────────────────────────────────────────────────────────────────

def transactions(
    env_name: str,
    q: str = "",
    status: str = None,
    queue_name: str = None,
    limit: int = 100,
) -> dict:
    """Browse IB transactions from PSAPMSGPUBHDR."""
    warnings = []
    limit = max(1, min(int(limit), 1000))

    if not ptmetadata.has_table(env_name, "PSAPMSGPUBHDR"):
        warnings.append(_warn("NO_PSAPMSGPUBHDR",
            "SYSADM.PSAPMSGPUBHDR not accessible — Integration Broker runtime data unavailable"))
        return {"items": [], "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSAPMSGPUBHDR",
        ["IB_OPERATIONNAME", "PUBNODE", "QUEUENAME", "SUBQUEUE",
         "ORIGPUBNODE", "PUBLISHER", "PUBCLASS", "TRXTYPE",
         "CREATEDTTM", "PUBLISHTIMESTAMP", "PUBSTATUS",
         "STATUSSTRING", "RETRYCOUNT", "LASTUPDDTTM",
         "MACHINENAME", "PROCESSID"],
        required=["IBTRANSACTIONID"],
    )

    predicates = ["1=1"]
    params = {}

    if q:
        predicates.append("(upper(IB_OPERATIONNAME) LIKE :q OR upper(QUEUENAME) LIKE :q OR upper(PUBNODE) LIKE :q)")
        params["q"] = f"%{q.upper()}%"

    if status:
        predicates.append("PUBSTATUS = :status")
        params["status"] = str(status)

    if queue_name:
        predicates.append("upper(QUEUENAME) = upper(:qname)")
        params["qname"] = queue_name

    sql = f"""
        SELECT * FROM (
            SELECT {", ".join(columns)}
              FROM sysadm.PSAPMSGPUBHDR
             WHERE {" AND ".join(predicates)}
             ORDER BY CREATEDTTM DESC
        ) WHERE ROWNUM <= {limit}
    """

    try:
        rows = psdb.query(env_name, sql, params)
        for row in rows:
            row["pubstatus_label"] = PUBSTATUS_LABELS.get(
                str(row.get("pubstatus") or "").strip(), "Unknown")
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("PSAPMSGPUBHDR_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def transaction(env_name: str, txid: str) -> dict:
    """Return a single IB transaction with publication and subscription contracts."""
    warnings = []

    if not ptmetadata.has_table(env_name, "PSAPMSGPUBHDR"):
        warnings.append(_warn("NO_PSAPMSGPUBHDR", "SYSADM.PSAPMSGPUBHDR not accessible"))
        return {"item": None, "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSAPMSGPUBHDR",
        ["IB_OPERATIONNAME", "EXTOPERATIONNAME", "PUBNODE", "QUEUENAME",
         "SUBQUEUE", "ORIGPUBNODE", "PUBLISHER", "PUBCLASS", "TRXTYPE",
         "CREATEDTTM", "PUBLISHTIMESTAMP", "PUBSTATUS", "STATUSSTRING",
         "RETRYCOUNT", "LASTUPDDTTM", "MACHINENAME", "PROCESSID",
         "CONVERSATIONID", "DESTPUBNODE", "PUBROUTINGTRAIL"],
        required=["IBTRANSACTIONID"],
    )

    try:
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSAPMSGPUBHDR
             WHERE IBTRANSACTIONID = :txid
        """, {"txid": txid})

        if not rows:
            return {"item": None, "warnings": warnings}

        row = rows[0]
        row["pubstatus_label"] = PUBSTATUS_LABELS.get(
            str(row.get("pubstatus") or "").strip(), "Unknown")

        # Publication contracts (per-subscriber delivery status).
        row["pub_contracts"] = _pub_contracts(env_name, txid)

        # Subscription contracts (handler execution status).
        row["sub_contracts"] = _sub_contracts(env_name, txid)

        return {"item": row, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("TX_ERR", str(exc), severity="error"))
        return {"item": None, "warnings": warnings}


def _pub_contracts(env_name: str, txid: str) -> list:
    if not ptmetadata.has_table(env_name, "PSAPMSGPUBCON"):
        return []
    try:
        columns = psdb.select_existing_columns(
            env_name, "PSAPMSGPUBCON",
            ["SUBNODE", "ROUTINGDEFNNAME", "PUBCONSTATUS", "STATUSSTRING",
             "RETRYCOUNT", "LASTUPDDTTM", "MACHINENAME"],
            required=["IBTRANSACTIONID"],
        )
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSAPMSGPUBCON
             WHERE IBTRANSACTIONID = :txid
             ORDER BY SUBNODE
        """, {"txid": txid})
        for row in rows:
            row["pubconstatus_label"] = PUBCONSTATUS_LABELS.get(
                str(row.get("pubconstatus") or "").strip(), "Unknown")
        return rows
    except Exception:
        return []


def _sub_contracts(env_name: str, txid: str) -> list:
    if not ptmetadata.has_table(env_name, "PSAPMSGSUBCON"):
        return []
    try:
        columns = psdb.select_existing_columns(
            env_name, "PSAPMSGSUBCON",
            ["IB_OPERATIONNAME", "ACTIONNAME", "ACTIONOWNER", "ROUTINGDEFNNAME",
             "SUBCONSTATUS", "STATUSSTRING", "RETRYCOUNT", "LASTUPDDTTM",
             "MACHINENAME", "PROCESS_INSTANCE"],
            required=["IBTRANSACTIONID"],
        )
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSAPMSGSUBCON
             WHERE IBTRANSACTIONID = :txid
             ORDER BY IB_OPERATIONNAME, ACTIONNAME
        """, {"txid": txid})
        for row in rows:
            row["subconstatus_label"] = SUBCONSTATUS_LABELS.get(
                str(row.get("subconstatus") or "").strip(), "Unknown")
        return rows
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Domain / Dispatcher Status
# ──────────────────────────────────────────────────────────────────────────────

def domain_status(env_name: str) -> dict:
    """Return IB domain/dispatcher status from PSAPMSGDOMSTAT."""
    warnings = []

    if not ptmetadata.has_table(env_name, "PSAPMSGDOMSTAT"):
        warnings.append(_warn("NO_PSAPMSGDOMSTAT",
            "SYSADM.PSAPMSGDOMSTAT not accessible"))
        return {"items": [], "warnings": warnings}

    try:
        rows = psdb.query(env_name, """
            SELECT
                MACHINENAME,
                APPSERVER_PATH,
                DOMAIN_STATUS,
                IBAILOVERPRIORITY,
                IBFAILOVERGROUP,
                IB_SLAVEMODE,
                IB_LOADBALANCE,
                IB_SERVERURL,
                IB_DOMAIN_POOLING
            FROM sysadm.PSAPMSGDOMSTAT
            ORDER BY MACHINENAME, APPSERVER_PATH
            FETCH FIRST 50 ROWS ONLY
        """)

        for row in rows:
            row["domain_status_label"] = str(row.get("domain_status") or "").strip()

        return {"items": rows, "warnings": warnings}

    except Exception as exc:
        warnings.append(_warn("DOMSTAT_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}

# ──────────────────────────────────────────────────────────────────────────────
# Integration Groups
# ──────────────────────────────────────────────────────────────────────────────

def groups(env_name: str, q: str = "", limit: int = 100) -> dict:
    """Search integration group definitions from PSIBGROUPDEFN."""
    warnings = []
    limit = max(1, min(int(limit), 200))

    if not ptmetadata.has_table(env_name, "PSIBGROUPDEFN"):
        warnings.append(_warn("NO_PSIBGROUPDEFN",
            "SYSADM.PSIBGROUPDEFN not accessible"))
        return {"items": [], "warnings": warnings}

    columns = psdb.select_existing_columns(
        env_name, "PSIBGROUPDEFN",
        ["VERSION", "OBJECTOWNERID", "LASTUPDDTTM", "LASTUPDOPRID",
         "DESCR", "DESCRLONG"],
        required=["IB_INTGROUPNAME"],
    )

    pattern = f"%{q.upper()}%"
    try:
        rows = psdb.query(env_name, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSIBGROUPDEFN
             WHERE upper(IB_INTGROUPNAME) LIKE :pat
                OR upper(DESCR) LIKE :pat
             ORDER BY IB_INTGROUPNAME
             FETCH FIRST {limit} ROWS ONLY
        """, {"pat": pattern})
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(_warn("PSIBGROUPDEFN_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard / summary
# ──────────────────────────────────────────────────────────────────────────────

def dashboard(env_name: str) -> dict:
    """Return a summary of IB configuration and runtime state."""
    warnings = []
    result = {
        "service_count":  None,
        "operation_count": None,
        "routing_count":  None,
        "node_count":     None,
        "queue_count":    None,
        "pub_by_status":  [],
        "sub_by_status":  [],
        "domain_status":  [],
        "warnings":       warnings,
    }

    def _count(table, col="*"):
        try:
            if ptmetadata.has_table(env_name, table):
                rows = psdb.query(env_name, f"SELECT COUNT({col}) AS cnt FROM sysadm.{table}")
                return rows[0]["cnt"] if rows else 0
        except Exception:
            pass
        return None

    result["service_count"] = _count("PSIBAPPLDEFN", "PTIBAPPLNAME")
    result["operation_count"] = _count("PSOPERATION", "IB_OPERATIONNAME")
    if result["operation_count"] is None and ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        try:
            rows = psdb.query(env_name, """
                SELECT COUNT(DISTINCT IB_OPERATIONNAME) AS cnt
                  FROM sysadm.PSIBRTNGDEFN
            """)
            result["operation_count"] = rows[0]["cnt"] if rows else 0
        except Exception:
            result["operation_count"] = None
    result["routing_count"] = _count("PSIBRTNGDEFN", "ROUTINGDEFNNAME")
    result["node_count"]    = _count("PSMSGNODEDEFN", "MSGNODENAME")
    result["queue_count"]   = _count("PSQUEUEDEFN", "QUEUENAME")

    # Runtime pub status summary.
    if ptmetadata.has_table(env_name, "PSAPMSGPUBHDR"):
        try:
            rows = psdb.query(env_name, """
                SELECT PUBSTATUS, COUNT(*) AS cnt
                  FROM sysadm.PSAPMSGPUBHDR
                 WHERE CREATEDTTM > SYSDATE - 1
                 GROUP BY PUBSTATUS
                 ORDER BY PUBSTATUS
            """)
            for row in rows:
                row["status_label"] = PUBSTATUS_LABELS.get(
                    str(row.get("pubstatus") or "").strip(), "Unknown")
            result["pub_by_status"] = rows
        except Exception as exc:
            warnings.append(_warn("PUBHDR_SUMMARY_ERR", str(exc)))
    else:
        warnings.append(_warn("NO_PSAPMSGPUBHDR",
            "SYSADM.PSAPMSGPUBHDR not accessible — IB runtime data unavailable"))

    # Subscription status summary.
    if ptmetadata.has_table(env_name, "PSAPMSGSUBCON"):
        try:
            rows = psdb.query(env_name, """
                SELECT SUBCONSTATUS, COUNT(*) AS cnt
                  FROM sysadm.PSAPMSGSUBCON
                 WHERE CREATEDTTM > SYSDATE - 1
                 GROUP BY SUBCONSTATUS
                 ORDER BY SUBCONSTATUS
            """)
            for row in rows:
                row["status_label"] = SUBCONSTATUS_LABELS.get(
                    str(row.get("subconstatus") or "").strip(), "Unknown")
            result["sub_by_status"] = rows
        except Exception as exc:
            warnings.append(_warn("SUBCON_SUMMARY_ERR", str(exc)))
    else:
        warnings.append(_warn("NO_PSAPMSGSUBCON",
            "SYSADM.PSAPMSGSUBCON not accessible — IB subscription data unavailable"))

    result["domain_status"] = domain_status(env_name).get("items", [])
    return result


# ──────────────────────────────────────────────────────────────────────────────
# PeopleCode integration
# ──────────────────────────────────────────────────────────────────────────────

def service_peoplecode(env_name: str, applname: str) -> dict:
    """Return PeopleCode attached to a service operation (subscriptions + handlers)."""
    if not ptmetadata.has_table(env_name, "PSPCMPROG"):
        return {"items": [], "warnings": [_warn("NO_PSPCMPROG", "SYSADM.PSPCMPROG not accessible")]}

    try:
        # objectid1=60: old-style subscription PeopleCode; objectid1=104: new-style handler PeopleCode
        rows = psdb.query(env_name, """
            SELECT OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3,
                   OBJECTVALUE4, OBJECTVALUE5, OBJECTVALUE6, OBJECTVALUE7,
                   PROGSEQ, LASTUPDDTTM, LASTUPDOPRID
              FROM SYSADM.PSPCMPROG
             WHERE OBJECTID1 IN (60, 104)
               AND upper(OBJECTVALUE1) = upper(:name)
             ORDER BY OBJECTID1, OBJECTVALUE2, OBJECTVALUE3
        """, {"name": applname})

        from connectors import peoplecode as pc
        items = []
        for row in rows:
            normalized = pc.normalize_program(row)
            enc = normalized.get("encoded_reference")
            if enc:
                normalized["_links"] = {"admin": f"/admin/object/peoplecode/{enc}"}
            items.append(normalized)

        return {"items": items, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [_warn("PSPCMPROG_ERR", str(exc), severity="error")]}


# ──────────────────────────────────────────────────────────────────────────────
# Global search provider
# ──────────────────────────────────────────────────────────────────────────────

def search(env_name: str, q: str, limit: int = 10) -> list:
    """Return IB objects matching q for inclusion in global search results."""
    results = []

    for source, item_type, name_key, desc_key, url_prefix in [
        (services,  "ib_service",  "ptibapplname",   "descr",        "/admin/ib/service/"),
        (operations, "ib_operation", "ib_operationname", "descr",     "/admin/ib/operation/"),
        (routings,  "ib_routing",  "routingdefnname", "descr",       "/admin/ib/routing/"),
        (nodes,     "ib_node",     "msgnodename",    "descr",        "/admin/ib/node/"),
        (queues,    "ib_queue",    "queuename",      "descr",        "/admin/ib/queue/"),
    ]:
        try:
            data = source(env_name, q=q, limit=limit)
            for item in data.get("items", []):
                name = item.get(name_key) or ""
                desc = item.get(desc_key) or ""
                results.append({
                    "type":        item_type,
                    "name":        name,
                    "description": desc,
                    "url":         url_prefix + name,
                })
        except Exception:
            pass

    return results
