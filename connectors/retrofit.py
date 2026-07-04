"""
Upgrade Retrofit connector — Phase 13.

Implements the reframed Phase A (customization detection + object-level
compare) and the data layer Phase B's AI tools sit on (retrofit guidance +
closure verification). See ROADMAP.md's "Phase 13 — Upgrade Automation"
section for the full plan and why it's scoped this way.

This is a directive-then-verify workflow, not an automated-write one:
every function here is read-only. The AI uses these to tell a human
precisely what to change; the human changes it themselves (in Application
Designer); the AI re-runs the same compare to confirm it worked.

Object registry reuses the exact table/key-column pairs already verified
elsewhere in this codebase (connectors/psdb.py's global_search() specs,
connectors/ptmetadata.py's discovery specs) rather than re-guessing column
names.
"""

from connectors import psdb, ptmetadata

# (table, key_col) per object type — verified against this codebase's own
# existing usage (psdb.global_search()'s specs, ptmetadata.py's per-type
# discovery specs), not re-derived from scratch.
_OBJECT_TABLES = {
    "page":               {"table": "PSPNLDEFN",   "key_col": "PNLNAME"},
    "record":             {"table": "PSRECDEFN",   "key_col": "RECNAME"},
    "field":              {"table": "PSDBFIELD",   "key_col": "FIELDNAME"},
    "component_interface": {"table": "PSBCDEFN",    "key_col": "BCNAME"},
    "permission_list":    {"table": "PSCLASSDEFN", "key_col": "CLASSID"},
    "menu":               {"table": "PSMENUDEFN",  "key_col": "MENUNAME"},
    "ae_program":         {"table": "PSAEAPPLDEFN", "key_col": "AE_APPLID"},
}

# Columns that vary for reasons unrelated to a real definition change
# (audit stamps, cache/version counters) — excluded from the header diff
# itself so "what needs modification" doesn't get cluttered with noise;
# still reported separately as metadata.
_NOISE_COLUMNS = {"lastupddttm", "lastupdoprid", "objectownerid", "versionnumber", "svcbasever"}


def object_types() -> list[str]:
    return sorted(_OBJECT_TABLES.keys())


def customization_inventory(env: str, object_types: list[str] | None = None, limit: int = 200) -> dict:
    """Classify every row per requested object type as delivered or
    customized via LASTUPDOPRID — the same heuristic
    connectors/peoplecode.py already uses for PeopleCode
    (`LASTUPDOPRID not in _DELIVERED_OPRIDS`), generalized across every
    customizable object type this registry covers. Filtering happens
    server-side (not fetch-all-then-filter in Python) since real customer
    tables can have hundreds of thousands of rows (PSDBFIELD alone is
    ~90K-110K rows in this lab's demo environments).

    A 0-customized result is a legitimate, honest outcome — this lab's demo
    databases are pristine vendor copies with zero real customizations
    anywhere (verified directly against every table in this registry before
    writing this function) — not a sign the query is broken.
    """
    from connectors.peoplecode import _DELIVERED_OPRIDS

    types = object_types or list(_OBJECT_TABLES.keys())
    delivered_list = sorted(o for o in _DELIVERED_OPRIDS if o)
    placeholders = ", ".join(f"'{o}'" for o in delivered_list)

    result = {}
    for obj_type in types:
        spec = _OBJECT_TABLES.get(obj_type)
        if not spec:
            result[obj_type] = {"error": f"Unknown object_type '{obj_type}'"}
            continue

        table, key_col = spec["table"], spec["key_col"]
        if not ptmetadata.has_table(env, table):
            result[obj_type] = {"error": f"{table} not accessible", "total": 0, "customized_count": 0, "customized": []}
            continue

        try:
            total = psdb.query(env, f"SELECT COUNT(*) AS n FROM SYSADM.{table}")[0]["n"]
            custom_count = psdb.query(env, f"""
                SELECT COUNT(*) AS n FROM SYSADM.{table}
                 WHERE LASTUPDOPRID IS NULL OR UPPER(LASTUPDOPRID) NOT IN ({placeholders})
            """)[0]["n"]
            custom_rows = psdb.query(env, f"""
                SELECT {key_col} AS name, LASTUPDOPRID, LASTUPDDTTM
                  FROM SYSADM.{table}
                 WHERE LASTUPDOPRID IS NULL OR UPPER(LASTUPDOPRID) NOT IN ({placeholders})
                 ORDER BY LASTUPDDTTM DESC
                 FETCH FIRST {int(limit)} ROWS ONLY
            """)
        except Exception as exc:
            result[obj_type] = {"error": str(exc), "total": 0, "customized_count": 0, "customized": []}
            continue

        result[obj_type] = {
            "table": table,
            "total": total,
            "customized_count": custom_count,
            "customized": [
                {
                    "name": r.get("name"),
                    "last_upd_oprid": (r.get("lastupdoprid") or "").strip(),
                    "last_upd_dttm": str(r.get("lastupddttm"))[:19] if r.get("lastupddttm") else None,
                }
                for r in custom_rows
            ],
        }
    return result


def compare_object_header(env_a: str, env_b: str, object_type: str, name: str) -> dict:
    """Generic single-object header-row compare between two environments —
    works uniformly for any type in _OBJECT_TABLES. Reports which columns
    differ (excluding audit-noise columns), and whether the object exists
    in each environment at all (a missing/renamed object is itself a real,
    important finding — upstream sometimes deletes or renames things)."""
    spec = _OBJECT_TABLES.get(object_type)
    if not spec:
        return {"error": f"Unknown object_type '{object_type}'"}
    table, key_col = spec["table"], spec["key_col"]

    def _fetch(env):
        if not ptmetadata.has_table(env, table):
            return None, f"{table} not accessible in {env}"
        rows = psdb.query(env, f"SELECT * FROM SYSADM.{table} WHERE {key_col} = :name", {"name": name})
        return (rows[0] if rows else None), None

    row_a, err_a = _fetch(env_a)
    row_b, err_b = _fetch(env_b)
    if err_a or err_b:
        return {"error": err_a or err_b}

    if row_a is None and row_b is None:
        return {"object_type": object_type, "name": name, "exists_in_a": False, "exists_in_b": False,
                "note": f"'{name}' not found in either {env_a} or {env_b}"}
    if row_a is None:
        return {"object_type": object_type, "name": name, "exists_in_a": False, "exists_in_b": True,
                "note": f"'{name}' exists in {env_b} but not in {env_a}"}
    if row_b is None:
        return {"object_type": object_type, "name": name, "exists_in_a": True, "exists_in_b": False,
                "note": f"'{name}' exists in {env_a} but not in {env_b} — deleted or renamed upstream?"}

    diffs = []
    all_cols = set(row_a.keys()) | set(row_b.keys())
    for col in sorted(all_cols):
        if col in _NOISE_COLUMNS:
            continue
        va, vb = row_a.get(col), row_b.get(col)
        if str(va) != str(vb):
            diffs.append({"column": col, f"value_{env_a.lower()}": va, f"value_{env_b.lower()}": vb})

    return {
        "object_type": object_type, "name": name,
        "exists_in_a": True, "exists_in_b": True,
        "identical": len(diffs) == 0,
        "diff_count": len(diffs),
        "diffs": diffs,
        "last_upd_a": {"oprid": row_a.get("lastupdoprid"), "dttm": str(row_a.get("lastupddttm"))[:19] if row_a.get("lastupddttm") else None},
        "last_upd_b": {"oprid": row_b.get("lastupdoprid"), "dttm": str(row_b.get("lastupddttm"))[:19] if row_b.get("lastupddttm") else None},
    }


def compare_page_fields(env_a: str, env_b: str, pnlname: str) -> dict:
    """Page-field-level structural compare (PSPNLFIELD) between two
    environments — the concrete 'page manipulation' case: which fields
    were added/removed upstream, and which fields common to both moved
    position (FIELDNUM — the field's sequence within the page — and its
    physical FIELDTOP/FIELDLEFT coordinates)."""
    def _fetch(env):
        if not ptmetadata.has_table(env, "PSPNLFIELD"):
            return None, f"PSPNLFIELD not accessible in {env}"
        rows = psdb.query(env, """
            SELECT RECNAME, FIELDNAME, FIELDNUM, OCCURSLEVEL, FIELDTOP, FIELDLEFT, FIELDTYPE
              FROM SYSADM.PSPNLFIELD
             WHERE PNLNAME = :pnlname
             ORDER BY FIELDNUM
        """, {"pnlname": pnlname})
        return rows, None

    rows_a, err_a = _fetch(env_a)
    rows_b, err_b = _fetch(env_b)
    if err_a or err_b:
        return {"error": err_a or err_b}
    if not rows_a and not rows_b:
        return {"pnlname": pnlname, "note": f"No PSPNLFIELD rows found for '{pnlname}' in either {env_a} or {env_b}"}

    def _key(r):
        return (r.get("recname") or "").strip(), (r.get("fieldname") or "").strip()

    by_key_a = {_key(r): r for r in rows_a}
    by_key_b = {_key(r): r for r in rows_b}

    only_a = sorted(by_key_a.keys() - by_key_b.keys())
    only_b = sorted(by_key_b.keys() - by_key_a.keys())
    moved = []
    for key in sorted(by_key_a.keys() & by_key_b.keys()):
        ra, rb = by_key_a[key], by_key_b[key]
        if (ra.get("fieldnum") != rb.get("fieldnum")
                or ra.get("fieldtop") != rb.get("fieldtop")
                or ra.get("fieldleft") != rb.get("fieldleft")):
            moved.append({
                "record_field": f"{key[0]}.{key[1]}",
                f"fieldnum_{env_a.lower()}": ra.get("fieldnum"), f"fieldnum_{env_b.lower()}": rb.get("fieldnum"),
                f"position_{env_a.lower()}": [ra.get("fieldtop"), ra.get("fieldleft")],
                f"position_{env_b.lower()}": [rb.get("fieldtop"), rb.get("fieldleft")],
            })

    return {
        "pnlname": pnlname,
        f"field_count_{env_a.lower()}": len(rows_a),
        f"field_count_{env_b.lower()}": len(rows_b),
        f"only_in_{env_a.lower()}": [f"{k[0]}.{k[1]}" for k in only_a],
        f"only_in_{env_b.lower()}": [f"{k[0]}.{k[1]}" for k in only_b],
        "moved_or_repositioned": moved,
        "identical_layout": not only_a and not only_b and not moved,
    }


def retrofit_worklist(env: str, target_env: str, object_types: list[str] | None = None,
                       inventory_limit: int = 50) -> dict:
    """The Phase A deliverable: for every customized object (per
    customization_inventory), compare it against target_env and report
    whether it's already reconciled or needs attention. This is a 2-way
    compare (current vs. target) — the practical shape needed for
    directive-then-verify; see ROADMAP.md for why a full 3-way diff
    (current vs. old-delivered vs. new-delivered) needs a second baseline
    environment this lab doesn't have, and isn't required for the
    reframed initiative."""
    inventory = customization_inventory(env, object_types=object_types, limit=inventory_limit)

    worklist = []
    for obj_type, info in inventory.items():
        if info.get("error"):
            continue
        for item in info.get("customized", []):
            name = item["name"]
            cmp = compare_object_header(env, target_env, obj_type, name)
            if cmp.get("error"):
                status = "error"
            elif not cmp.get("exists_in_b", True):
                status = "needs_review"  # deleted/renamed upstream
            elif cmp.get("identical"):
                status = "reconciled"
            else:
                status = "needs_review"
            worklist.append({
                "object_type": obj_type,
                "name": name,
                "last_upd_oprid": item["last_upd_oprid"],
                "status": status,
                "diff_count": cmp.get("diff_count", 0),
            })

    return {
        "env": env, "target_env": target_env,
        "total_customized": sum(i.get("customized_count", 0) for i in inventory.values() if not i.get("error")),
        "worklist": worklist,
        "needs_review_count": sum(1 for w in worklist if w["status"] == "needs_review"),
        "reconciled_count": sum(1 for w in worklist if w["status"] == "reconciled"),
    }


def retrofit_guidance(env: str, target_env: str, object_type: str, name: str) -> dict:
    """The specific, actionable instruction for one object: what exactly
    differs between the current object and the target, so the AI can turn
    this into a concrete 'change X to Y' directive rather than a vague
    'this is at risk.'"""
    header = compare_object_header(env, target_env, object_type, name)
    result = {"object_type": object_type, "name": name, "env": env, "target_env": target_env, "header": header}
    if object_type == "page" and header.get("exists_in_a") and header.get("exists_in_b"):
        result["fields"] = compare_page_fields(env, target_env, name)
    return result


def retrofit_verify(env: str, target_env: str, object_type: str, name: str,
                     previous_diff_columns: list[str] | None = None) -> dict:
    """Re-run the exact same compare after the user reports a change was
    made, and return an explicit closure verdict — never leave the caller
    to infer it from raw diff data.

    previous_diff_columns (optional): the column names that differed
    *before* the user's change (from an earlier retrofit_guidance call in
    the same conversation). Passing this distinguishes STILL_DIVERGENT
    (the same problem persists) from NEW_ISSUE_INTRODUCED (the change
    fixed the original problem but created a different one) — without it,
    both collapse to STILL_DIVERGENT, which is still correct but less
    specific."""
    guidance = retrofit_guidance(env, target_env, object_type, name)
    header = guidance.get("header", {})
    fields = guidance.get("fields")
    current_diff_columns = {d["column"] for d in header.get("diffs", [])}

    if header.get("error"):
        verdict = "ERROR"
    elif not header.get("exists_in_a", True):
        verdict = "STILL_DIVERGENT"
    elif header.get("identical") and (fields is None or fields.get("identical_layout")):
        verdict = "RESOLVED"
    elif previous_diff_columns is not None and not (current_diff_columns <= set(previous_diff_columns)):
        # Current diff includes at least one column that wasn't different before —
        # the original problem may be fixed, but something new diverged.
        verdict = "NEW_ISSUE_INTRODUCED"
    else:
        verdict = "STILL_DIVERGENT"

    return {**guidance, "verdict": verdict}
