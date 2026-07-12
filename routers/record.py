"""
Record Explorer router.
Dedicated routes for PeopleSoft record (PSRECDEFN/PSRECFIELD) exploration.
All endpoints are grant-aware — missing tables return warnings, not 500s.
"""

from fastapi import APIRouter, Query
from connectors import psdb

router = APIRouter(prefix="/api/record", tags=["Record Explorer"])


def _safe(fn, *args, empty=None, **kwargs):
    """Run fn; on any exception return (empty_value, warning_message)."""
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:
        return empty, str(exc)


@router.get("/search")
def record_search(env: str = Query(psdb.default_env()), q: str = Query("")):
    """Search PSRECDEFN by record name or description."""
    rows, err = _safe(psdb.search_records, env, q, empty=[])
    for r in (rows or []):
        rt = r.get("rectype")
        r["rectype_label"] = psdb.RECTYPE_LABELS.get(int(rt), str(rt)) if rt is not None else ""
    return {"items": rows or [], "warnings": [{"message": err, "severity": "error"}] if err else []}


@router.get("/{recname}")
def record_detail(recname: str, env: str = Query(psdb.default_env())):
    """Return PSRECDEFN detail for a single record."""
    rec, err = _safe(psdb.record_detail, env, recname)
    if rec:
        rt = rec.get("rectype")
        rec["rectype_label"] = psdb.RECTYPE_LABELS.get(int(rt) if rt is not None else -1, str(rt))
    return {"item": rec, "warnings": [{"message": err, "severity": "error"}] if err else []}


@router.get("/{recname}/fields")
def record_fields(recname: str, env: str = Query(psdb.default_env())):
    """Return PSRECFIELD rows for a record."""
    rows, err = _safe(psdb.record_fields, env, recname, empty=[])
    return {"items": rows or [], "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{recname}/keys")
def record_keys(recname: str, env: str = Query(psdb.default_env())):
    """Return key field definitions for a record."""
    rows, err = _safe(psdb.record_keys, env, recname, empty=[])
    return {"items": rows or [], "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{recname}/indexes")
def record_indexes(recname: str, env: str = Query(psdb.default_env())):
    """Return index definitions for a record."""
    rows, err = _safe(psdb.record_indexes, env, recname, empty=[])
    return {"items": rows or [], "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{recname}/ddl")
def record_ddl(recname: str, env: str = Query(psdb.default_env())):
    """Return CREATE TABLE DDL for a record."""
    result, err = _safe(psdb.record_ddl, env, recname, empty={})
    if err:
        return {"ddl": None, "warnings": [{"message": err, "severity": "warning"}]}
    return result


@router.get("/{recname}/count")
def record_count(recname: str, env: str = Query(psdb.default_env())):
    """Return row count for the underlying Oracle table."""
    result, err = _safe(psdb.record_count, env, recname, empty={})
    if err:
        return {"row_count": None, "warnings": [{"message": err, "severity": "warning"}]}
    return result


@router.get("/{recname}/sample")
def record_sample(recname: str, env: str = Query(psdb.default_env()), limit: int = Query(20)):
    """Return sample rows from the underlying Oracle table."""
    result, err = _safe(psdb.record_sample, env, recname, limit=limit, empty={})
    if err:
        return {"rows": [], "warnings": [{"message": err, "severity": "warning"}]}
    return result


@router.get("/{recname}/children")
def record_children(recname: str, env: str = Query(psdb.default_env())):
    """Return child records (PSRECDEFN where PARENTRECNAME = this record)."""
    rows, err = _safe(psdb.record_children, env, recname, empty=[])
    for r in (rows or []):
        rt = r.get("rectype")
        r["rectype_label"] = psdb.RECTYPE_LABELS.get(int(rt) if rt is not None else -1, str(rt))
    return {"items": rows or [], "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{recname}/components")
def record_components(recname: str, env: str = Query(psdb.default_env())):
    """Return components that use this record as search or add search record."""
    rows, err = _safe(psdb.record_components, env, recname, empty=[])
    return {"items": rows or [], "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{recname}/pages")
def record_pages(recname: str, env: str = Query(psdb.default_env())):
    """Return pages where fields from this record appear."""
    rows, err = _safe(psdb.record_pages, env, recname, empty=[])
    return {"items": rows or [], "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{recname}/related")
def record_related(recname: str, env: str = Query(psdb.default_env())):
    """Return parent record, language variant, audit record, and related views."""
    result, err = _safe(psdb.record_related, env, recname, empty={})
    if err:
        return {"parent": None, "lang": None, "audit": None, "views": [],
                "warnings": [{"message": err, "severity": "warning"}]}
    return result


@router.get("/{recname}/storage")
def record_storage(recname: str, env: str = Query(psdb.default_env())):
    """Return Oracle storage statistics from ALL_TABLES."""
    item, err = _safe(psdb.record_storage, env, recname)
    return {"item": item, "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{recname}/peoplecode")
def record_peoplecode(recname: str, env: str = Query(psdb.default_env())):
    """Return all record-level PeopleCode programs (PSPCMPROG OBJECTID1=2).
    These fire at the record/field definition level, independent of component.
    """
    result, err = _safe(psdb.record_peoplecode, env, recname, empty={})
    if err:
        return {"recname": recname, "row_events": [], "field_events": [], "total": 0,
                "warnings": [{"message": err, "severity": "warning"}]}
    return result or {}
