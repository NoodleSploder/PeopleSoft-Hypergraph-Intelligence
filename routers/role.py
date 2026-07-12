"""
Role Explorer router — PSROLEDEFN + PSROLEUSER.
"""

from fastapi import APIRouter, Query
from connectors import psdb

router = APIRouter(prefix="/api/role", tags=["Role Explorer"])


def _safe(fn, *args, empty=None, **kwargs):
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:
        return empty, str(exc)


@router.get("/search")
def role_search(env: str = Query(psdb.default_env()), q: str = Query(""), limit: int = Query(100)):
    rows, err = _safe(psdb.search_roles_with_count, env, q, limit, empty=[])
    return {"items": rows or [], "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{rolename}")
def role_detail(rolename: str, env: str = Query(psdb.default_env())):
    item, err = _safe(psdb.role_detail, env, rolename)
    return {"item": item, "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{rolename}/members")
def role_members(rolename: str, env: str = Query(psdb.default_env())):
    rows, err = _safe(psdb.role_users, env, rolename, empty=[])
    return {"items": rows or [], "rolename": rolename,
            "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{rolename}/permissionlists")
def role_permissionlists(rolename: str, env: str = Query(psdb.default_env())):
    rows, err = _safe(psdb.role_permissionlists, env, rolename, empty=[])
    return {"items": rows or [], "rolename": rolename,
            "warnings": [{"message": err, "severity": "warning"}] if err else []}
