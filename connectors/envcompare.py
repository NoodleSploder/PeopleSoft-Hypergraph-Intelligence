"""
Environment comparison connector.
Queries the same PeopleSoft metadata in two named environments and diffs the results.
All comparisons are grant-aware; errors per-environment are captured as warnings.
"""

from connectors import psdb

# ── PeopleSoft decode tables ───────────────────────────────────────────────────

RECTYPE_LABELS = {
    0: "SQL Table",
    1: "SQL View",
    2: "Derived/Work",
    3: "SubRecord",
    5: "Dynamic View",
    6: "Query View",
    7: "Temporary Table",
}

FIELDTYPE_LABELS = {
    0: "Char",
    1: "Long Char",
    2: "Number",
    3: "Signed Number",
    4: "Date",
    5: "Time",
    6: "DateTime",
    8: "Image",
    9: "ImageRef",
}


def _label(mapping, val, default="?"):
    if val is None:
        return default
    try:
        return mapping.get(int(val), str(val))
    except (TypeError, ValueError):
        return str(val)


# ── Core diff engine ───────────────────────────────────────────────────────────

def _compare(env1_rows, env2_rows, key_col, compare_cols):
    """
    Diff two query result-sets.  Returns:
      only_in_env1  — rows present only in env1
      only_in_env2  — rows present only in env2
      changed       — rows in both with at least one differing compare_col
      identical_count — count of rows that match on all compare_cols
    """
    e1 = {str(r.get(key_col, "") or "").strip(): r for r in env1_rows}
    e2 = {str(r.get(key_col, "") or "").strip(): r for r in env2_rows}
    all_keys = sorted(set(e1) | set(e2))

    only1, only2, changed = [], [], []
    identical = 0

    for k in all_keys:
        if k not in e2:
            only1.append(e1[k])
        elif k not in e1:
            only2.append(e2[k])
        else:
            diffs = []
            for col in compare_cols:
                v1 = str(e1[k].get(col) or "").strip()
                v2 = str(e2[k].get(col) or "").strip()
                if v1 != v2:
                    diffs.append({"col": col, "env1": v1, "env2": v2})
            if diffs:
                changed.append({"name": k, "env1": e1[k], "env2": e2[k], "diffs": diffs})
            else:
                identical += 1

    return {
        "only_in_env1": only1,
        "only_in_env2": only2,
        "changed": changed,
        "identical_count": identical,
    }


def _run(env, sql, params):
    """Run a query, return (rows, warning_or_None)."""
    try:
        return psdb.query(env, sql, params), None
    except Exception as exc:
        return [], {"code": f"{env.upper()}_ERROR", "message": f"{env}: {exc}", "severity": "error"}


# ── Public comparison functions ────────────────────────────────────────────────

def compare_records(env1, env2, q="", limit=500):
    """Diff PSRECDEFN (record catalog) between two environments."""
    sql = """
        SELECT r.RECNAME,
               r.RECTYPE,
               r.RECDESCR,
               COUNT(f.FIELDNUM) AS field_count
        FROM SYSADM.PSRECDEFN r
        LEFT JOIN SYSADM.PSRECFIELD f ON r.RECNAME = f.RECNAME
        WHERE (:q IS NULL OR UPPER(r.RECNAME) LIKE :q OR UPPER(r.RECDESCR) LIKE :q)
        GROUP BY r.RECNAME, r.RECTYPE, r.RECDESCR
        ORDER BY r.RECNAME
        FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    # Decode rectype for display.
    for r in rows1 + rows2:
        r["rectype_label"] = _label(RECTYPE_LABELS, r.get("rectype"))

    diff = _compare(rows1, rows2, "recname", ["rectype", "field_count"])
    diff.update({"env1": env1, "env2": env2, "object_type": "record",
                 "query": q, "warnings": warnings})
    return diff


def compare_fields(env1, env2, record_name):
    """Diff PSRECFIELD for a specific record across two environments.

    FIELDTYPE/LENGTH/DECIMALPOS live in PSDBFIELD, not PSRECFIELD — join when accessible.
    """
    params = {"recname": record_name.upper()}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        if psdb.table_columns(env, "PSDBFIELD"):
            sql = """
                SELECT rf.FIELDNAME,
                       rf.FIELDNUM,
                       rf.USEEDIT,
                       rf.DEFRECNAME,
                       rf.DEFFIELDNAME,
                       fd.FIELDTYPE,
                       fd.LENGTH      AS FIELDLEN,
                       fd.DECIMALPOS
                FROM SYSADM.PSRECFIELD rf
                LEFT JOIN SYSADM.PSDBFIELD fd ON fd.FIELDNAME = rf.FIELDNAME
                WHERE rf.RECNAME = :recname
                ORDER BY rf.FIELDNUM
            """
        else:
            sql = """
                SELECT FIELDNAME,
                       FIELDNUM,
                       USEEDIT,
                       DEFRECNAME,
                       DEFFIELDNAME,
                       NULL AS FIELDTYPE,
                       NULL AS FIELDLEN,
                       NULL AS DECIMALPOS
                FROM SYSADM.PSRECFIELD
                WHERE RECNAME = :recname
                ORDER BY FIELDNUM
            """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    for r in rows1 + rows2:
        r["fieldtype_label"] = _label(FIELDTYPE_LABELS, r.get("fieldtype"))

    compare_cols = ["fieldtype", "fieldlen", "decimalpos", "useedit", "defrecname", "deffieldname"]
    diff = _compare(rows1, rows2, "fieldname", compare_cols)
    diff.update({"env1": env1, "env2": env2, "object_type": "field",
                 "record_name": record_name.upper(), "warnings": warnings})
    return diff


def compare_components(env1, env2, q="", limit=500):
    """Diff PSPNLGRPDEFN (component catalog) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSPNLGRPDEFN")
        addsrch = "ADDSRCHRECNAME" if "addsrchrecname" in cols else "NULL AS ADDSRCHRECNAME"
        actions = "ACTIONS" if "actions" in cols else "NULL AS ACTIONS"
        sql = f"""
            SELECT PNLGRPNAME,
                   SEARCHRECNAME,
                   {addsrch},
                   DESCR,
                   {actions}
            FROM SYSADM.PSPNLGRPDEFN
            WHERE MARKET = 'GBL'
              AND (:q IS NULL OR UPPER(PNLGRPNAME) LIKE :q OR UPPER(DESCR) LIKE :q)
            ORDER BY PNLGRPNAME
            FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "pnlgrpname", ["searchrecname", "addsrchrecname", "actions"])
    diff.update({"env1": env1, "env2": env2, "object_type": "component",
                 "query": q, "warnings": warnings})
    return diff


def compare_permissions(env1, env2, q="", limit=500):
    """Diff PSCLASSDEFN (permission list catalog) between two environments.

    PSCLASSDEFN uses DESCR in older PeopleTools and CLASSDEFNDESC in newer — check per env.
    """
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSCLASSDEFN")
        descr_col = next(
            (c for c in ("DESCR", "CLASSDEFNDESC") if c.lower() in cols),
            None,
        )
        if descr_col:
            descr_sel = descr_col
            descr_filter = f"OR UPPER({descr_col}) LIKE :q"
        else:
            descr_sel = "NULL AS DESCR"
            descr_filter = ""
        sql = f"""
            SELECT CLASSID, {descr_sel} AS DESCR
            FROM SYSADM.PSCLASSDEFN
            WHERE (:q IS NULL OR UPPER(CLASSID) LIKE :q {descr_filter})
            ORDER BY CLASSID
            FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "classid", ["descr"])
    diff.update({"env1": env1, "env2": env2, "object_type": "permission",
                 "query": q, "warnings": warnings})
    return diff


def compare_ae(env1, env2, q="", limit=500):
    """Diff PSAEAPPLDEFN (Application Engine program catalog) between two environments.

    AE_STATUS does not exist in PSAEAPPLDEFN; use DESCR + LASTUPDDTTM, guard per env.
    """
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSAEAPPLDEFN")
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        descr_filter = "OR UPPER(DESCR) LIKE :q" if "descr" in cols else ""
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT AE_APPLID, {descr_col}, {ts_col}
            FROM SYSADM.PSAEAPPLDEFN
            WHERE (:q IS NULL OR UPPER(AE_APPLID) LIKE :q {descr_filter})
            ORDER BY AE_APPLID
            FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "ae_applid", ["descr", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "ae",
                 "query": q, "warnings": warnings})
    return diff


def compare_roles(env1, env2, q="", limit=500):
    """Diff PSROLEDEFN (role catalog) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSROLEDEFN")
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        descr_filter = "OR UPPER(DESCR) LIKE :q" if "descr" in cols else ""
        sql = f"""
            SELECT ROLENAME, {descr_col}
            FROM SYSADM.PSROLEDEFN
            WHERE (:q IS NULL OR UPPER(ROLENAME) LIKE :q {descr_filter})
            ORDER BY ROLENAME
            FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "rolename", ["descr"])
    diff.update({"env1": env1, "env2": env2, "object_type": "role",
                 "query": q, "warnings": warnings})
    return diff


def compare_peoplecode(env1, env2, q="", limit=500):
    """Diff PSPCMPROG (PeopleCode program catalog) between two environments.

    Groups by the logical program identity (OBJECTID1 + OBJECTVALUE1..5) so that
    multi-row programs (multiple PROGSEQ rows per event) appear as a single entry.
    Comparing LASTUPDDTTM (MAX per program) reveals which programs changed.
    Filter by q to scope the comparison to a specific parent object (e.g. record name).
    """
    sql = """
        SELECT OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3,
               OBJECTVALUE4, OBJECTVALUE5,
               MAX(LASTUPDDTTM) AS LASTUPDDTTM
          FROM SYSADM.PSPCMPROG
         WHERE (:q IS NULL OR UPPER(OBJECTVALUE1) LIKE :q OR UPPER(OBJECTVALUE2) LIKE :q)
         GROUP BY OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3,
                  OBJECTVALUE4, OBJECTVALUE5
         ORDER BY OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3
         FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    def _pc_key(row):
        return "|".join([
            str(row.get("objectid1") or ""),
            str(row.get("objectvalue1") or "").strip(),
            str(row.get("objectvalue2") or "").strip(),
            str(row.get("objectvalue3") or "").strip(),
            str(row.get("objectvalue4") or "").strip(),
            str(row.get("objectvalue5") or "").strip(),
        ])

    for r in rows1:
        r["_key"] = _pc_key(r)
    for r in rows2:
        r["_key"] = _pc_key(r)

    diff = _compare(rows1, rows2, "_key", ["lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "peoplecode",
                 "query": q, "warnings": warnings})
    return diff


def compare_sql_definitions(env1, env2, q="", limit=500):
    """Diff PSSQLDEFN (SQL object catalog) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSSQLDEFN")
        owner_col = "OBJECTOWNERID" if "objectownerid" in cols else "NULL AS OBJECTOWNERID"
        owner_filter = "OR UPPER(OBJECTOWNERID) LIKE :q" if "objectownerid" in cols else ""
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT SQLID, SQLTYPE, {owner_col}, {ts_col}
              FROM SYSADM.PSSQLDEFN
             WHERE (:q IS NULL OR UPPER(SQLID) LIKE :q {owner_filter})
             ORDER BY SQLTYPE, SQLID
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "sqlid", ["sqltype", "objectownerid", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "sql_definitions",
                 "query": q, "warnings": warnings})
    return diff


def compare_portals(env1, env2, q="", limit=500):
    """Diff PSPRSMDEFN (Portal Registry content references) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSPRSMDEFN")
        label_col = "PORTAL_LABEL" if "portal_label" in cols else "NULL AS PORTAL_LABEL"
        label_filter = "OR UPPER(PORTAL_LABEL) LIKE :q" if "portal_label" in cols else ""
        prnt_col = "PORTAL_PRNTOBJNAME" if "portal_prntobjname" in cols else "NULL AS PORTAL_PRNTOBJNAME"
        type_col = "PORTAL_OBJTYPE" if "portal_objtype" in cols else "NULL AS PORTAL_OBJTYPE"
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT PORTAL_OBJNAME, PORTAL_NAME, {label_col},
                   {prnt_col}, {type_col}, {ts_col}
              FROM SYSADM.PSPRSMDEFN
             WHERE (:q IS NULL OR UPPER(PORTAL_OBJNAME) LIKE :q {label_filter})
             ORDER BY PORTAL_OBJNAME
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "portal_objname",
                    ["portal_label", "portal_prntobjname", "portal_objtype", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "portals",
                 "query": q, "warnings": warnings})
    return diff


def compare_queries(env1, env2, q="", limit=500):
    """Diff PSQRYDEFN (public PS Queries, OPRID=' ') between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSQRYDEFN")
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        descr_filter = "OR UPPER(DESCR) LIKE :q" if "descr" in cols else ""
        folder_col = "QRYFOLDER" if "qryfolder" in cols else "NULL AS QRYFOLDER"
        disabled_col = "QRYDISABLED" if "qrydisabled" in cols else "NULL AS QRYDISABLED"
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT QRYNAME, {descr_col}, QRYTYPE, {folder_col}, {disabled_col}, {ts_col}
              FROM SYSADM.PSQRYDEFN
             WHERE OPRID = ' '
               AND (:q IS NULL OR UPPER(QRYNAME) LIKE :q {descr_filter})
             ORDER BY QRYNAME
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "qryname",
                    ["descr", "qrytype", "qryfolder", "qrydisabled", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "queries",
                 "query": q, "warnings": warnings})
    return diff


def summary(env1, env2):
    """
    Quick catalog-count comparison across key object types.
    Returns a list of {type, env1_count, env2_count, delta} rows.
    """
    queries = [
        ("Records",          "SELECT COUNT(*) AS n FROM SYSADM.PSRECDEFN"),
        ("Fields",           "SELECT COUNT(*) AS n FROM SYSADM.PSRECFIELD"),
        ("Components",       "SELECT COUNT(*) AS n FROM SYSADM.PSPNLGRPDEFN WHERE MARKET='GBL'"),
        ("Pages",            "SELECT COUNT(*) AS n FROM SYSADM.PSPNLDEFN"),
        ("Permission Lists", "SELECT COUNT(*) AS n FROM SYSADM.PSCLASSDEFN"),
        ("Roles",            "SELECT COUNT(*) AS n FROM SYSADM.PSROLEDEFN"),
        ("AE Programs",      "SELECT COUNT(*) AS n FROM SYSADM.PSAEAPPLDEFN"),
        ("PeopleCode Progs", "SELECT COUNT(DISTINCT OBJECTVALUE1||'|'||OBJECTVALUE2||'|'||OBJECTVALUE3) AS n FROM SYSADM.PSPCMPROG"),
        ("SQL Definitions",  "SELECT COUNT(*) AS n FROM SYSADM.PSSQLDEFN"),
        ("Portal Entries",   "SELECT COUNT(*) AS n FROM SYSADM.PSPRSMDEFN"),
        ("PS Queries",       "SELECT COUNT(*) AS n FROM SYSADM.PSQRYDEFN WHERE OPRID = ' '"),
    ]
    rows = []
    warnings = []
    for label, sql in queries:
        c1 = c2 = None
        try:
            r = psdb.query(env1, sql)
            c1 = r[0]["n"] if r else 0
        except Exception as e:
            warnings.append({"code": "ENV1_COUNT_ERR", "message": f"{env1}/{label}: {e}", "severity": "warning"})
        try:
            r = psdb.query(env2, sql)
            c2 = r[0]["n"] if r else 0
        except Exception as e:
            warnings.append({"code": "ENV2_COUNT_ERR", "message": f"{env2}/{label}: {e}", "severity": "warning"})
        rows.append({
            "type": label,
            "env1_count": c1,
            "env2_count": c2,
            "delta": (c1 - c2) if (c1 is not None and c2 is not None) else None,
        })
    return {"env1": env1, "env2": env2, "counts": rows, "warnings": warnings}


def compare_portal_object(env1, env2, portal_objname):
    """
    Deep diff of a specific Portal Registry object across two environments.
    Compares: definition fields, permissions, children set.
    """
    from connectors import psdb

    portal_objname = portal_objname.strip().upper()
    warnings = []
    result = {"env1": env1, "env2": env2, "portal_objname": portal_objname}

    def _fetch_defn(env):
        try:
            cols = psdb.table_columns(env, "PSPRSMDEFN")
            want = ["PORTAL_OBJNAME", "PORTAL_NAME", "PORTAL_REFTYPE", "PORTAL_LABEL",
                    "PORTAL_URLTEXT", "PORTAL_URI_SEG1", "PORTAL_URI_SEG2", "PORTAL_URI_SEG3",
                    "PORTAL_PRNTOBJNAME", "DESCR254", "LASTUPDDTTM", "LASTUPDOPRID",
                    "PORTAL_SECTYPE", "PORTAL_HIDE"]
            sel = [c for c in want if c.lower() in cols]
            if not sel:
                return None
            rows = psdb.query(env, f"""
                SELECT {', '.join(sel)}
                  FROM SYSADM.PSPRSMDEFN
                 WHERE PORTAL_OBJNAME = :name
                 FETCH FIRST 1 ROWS ONLY
            """, {"name": portal_objname})
            return rows[0] if rows else None
        except Exception as exc:
            warnings.append({"code": "defn_error", "env": env, "message": str(exc), "severity": "warning"})
            return None

    def _fetch_children(env):
        try:
            rows = psdb.query(env, """
                SELECT PORTAL_OBJNAME, PORTAL_LABEL, PORTAL_REFTYPE
                  FROM SYSADM.PSPRSMDEFN
                 WHERE PORTAL_PRNTOBJNAME = :name
                 ORDER BY PORTAL_OBJNAME
            """, {"name": portal_objname})
            return {str(r.get("portal_objname") or "").strip(): dict(r) for r in rows}
        except Exception as exc:
            warnings.append({"code": "children_error", "env": env, "message": str(exc), "severity": "warning"})
            return {}

    def _fetch_permissions(env):
        try:
            rows = psdb.query(env, """
                SELECT CLASSID, PORTAL_PERMTYPE
                  FROM SYSADM.PSPORTALDEFN
                 WHERE PORTAL_OBJNAME = :name
                 ORDER BY CLASSID
            """, {"name": portal_objname})
            return {str(r.get("classid") or "").strip(): str(r.get("portal_permtype") or "").strip() for r in rows}
        except Exception:
            return {}

    defn1 = _fetch_defn(env1)
    defn2 = _fetch_defn(env2)

    # Definition field diff
    defn_diff = []
    compare_fields = ["portal_reftype", "portal_label", "portal_urltext",
                      "portal_uri_seg1", "portal_uri_seg2", "portal_uri_seg3",
                      "portal_prntobjname", "descr254", "portal_sectype", "portal_hide"]
    for field in compare_fields:
        v1 = str(defn1.get(field) or "").strip() if defn1 else None
        v2 = str(defn2.get(field) or "").strip() if defn2 else None
        if v1 != v2:
            defn_diff.append({"field": field, env1: v1, env2: v2})

    # Children diff
    children1 = _fetch_children(env1)
    children2 = _fetch_children(env2)
    all_children = sorted(set(children1) | set(children2))
    children_diff = []
    for child in all_children:
        in1 = child in children1
        in2 = child in children2
        if not (in1 and in2):
            children_diff.append({
                "portal_objname": child,
                "status": f"only_in_{env1}" if in1 else f"only_in_{env2}",
                "portal_label": (children1.get(child) or children2.get(child) or {}).get("portal_label"),
            })
        else:
            # Both have it — check if label differs
            l1 = str(children1[child].get("portal_label") or "").strip()
            l2 = str(children2[child].get("portal_label") or "").strip()
            if l1 != l2:
                children_diff.append({
                    "portal_objname": child,
                    "status": "label_differs",
                    env1: l1,
                    env2: l2,
                })

    # Permissions diff
    perms1 = _fetch_permissions(env1)
    perms2 = _fetch_permissions(env2)
    all_perms = sorted(set(perms1) | set(perms2))
    perms_diff = []
    for classid in all_perms:
        in1 = classid in perms1
        in2 = classid in perms2
        if not (in1 and in2):
            perms_diff.append({
                "classid": classid,
                "status": f"only_in_{env1}" if in1 else f"only_in_{env2}",
            })
        elif perms1[classid] != perms2[classid]:
            perms_diff.append({
                "classid": classid,
                "status": "type_differs",
                env1: perms1[classid],
                env2: perms2[classid],
            })

    ts1 = str(defn1.get("lastupddttm") or "") if defn1 else None
    ts2 = str(defn2.get("lastupddttm") or "") if defn2 else None

    result.update({
        "exists_in_env1": defn1 is not None,
        "exists_in_env2": defn2 is not None,
        "last_updated": {env1: ts1, env2: ts2},
        "definition_diffs": defn_diff,
        "children_diffs": children_diff,
        "permissions_diffs": perms_diff,
        "summary": {
            "definition_changes": len(defn_diff),
            "children_changes": len(children_diff),
            "permissions_changes": len(perms_diff),
            "total_changes": len(defn_diff) + len(children_diff) + len(perms_diff),
        },
        "warnings": warnings,
    })
    return result
