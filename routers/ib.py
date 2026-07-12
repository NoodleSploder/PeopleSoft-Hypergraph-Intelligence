"""
Integration Broker API router.
All routes are read-only and grant-aware — missing tables return warnings, not errors.
"""

from fastapi import APIRouter, Query
from connectors import ib, psdb

router = APIRouter(prefix="/api/ib", tags=["Integration Broker"])


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def ib_dashboard(env: str = psdb.default_env()):
    """IB summary: catalog counts and 24-hour runtime pub/sub status breakdown."""
    return ib.dashboard(env)


# ──────────────────────────────────────────────────────────────────────────────
# Services / Application Definitions
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/services")
def list_services(
    env: str = Query(psdb.default_env()),
    q:     str = Query(""),
    limit: int = Query(100),
):
    """Search application service definitions (PSIBAPPLDEFN)."""
    return ib.services(env, q=q, limit=limit)


@router.get("/services/{applname}")
def get_service(applname: str, env: str = Query(psdb.default_env())):
    """Return a single application service definition with operations and routings."""
    return ib.service(env, applname)


@router.get("/services/{applname}/operations")
def get_service_operations(applname: str, env: str = Query(psdb.default_env())):
    """Return operations (PSIBAPPLOPR) for a given service."""
    return ib.service_operations(env, applname)


# ──────────────────────────────────────────────────────────────────────────────
# Service Operations
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/operations")
def list_operations(
    env: str = Query(psdb.default_env()),
    q:     str = Query(""),
    limit: int = Query(100),
):
    """Search Integration Broker service operations."""
    return ib.operations(env, q=q, limit=limit)


@router.get("/operations/{opname}")
def get_operation(opname: str, env: str = Query(psdb.default_env())):
    """Return one service operation with versions, handlers, security, messages, and routings."""
    return ib.operation(env, opname)


# ──────────────────────────────────────────────────────────────────────────────
# Routings
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/routings")
def list_routings(
    env: str = Query(psdb.default_env()),
    q:     str = Query(""),
    limit: int = Query(100),
):
    """Search routing definitions (PSIBRTNGDEFN)."""
    return ib.routings(env, q=q, limit=limit)


@router.get("/routings/{rtngname}")
def get_routing(rtngname: str, env: str = Query(psdb.default_env())):
    """Return a single routing definition with sub-definitions."""
    return ib.routing(env, rtngname)


# ──────────────────────────────────────────────────────────────────────────────
# Nodes
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/nodes")
def list_nodes(
    env: str = Query(psdb.default_env()),
    q:     str = Query(""),
    limit: int = Query(100),
):
    """Search node definitions (PSMSGNODEDEFN)."""
    return ib.nodes(env, q=q, limit=limit)


@router.get("/nodes/{nodename}")
def get_node(nodename: str, env: str = Query(psdb.default_env())):
    """Return a single node definition with associated routings."""
    return ib.node(env, nodename)


# ──────────────────────────────────────────────────────────────────────────────
# Queues
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/queues")
def list_queues(
    env: str = Query(psdb.default_env()),
    q:     str = Query(""),
    limit: int = Query(100),
):
    """Search queue definitions (PSQUEUEDEFN)."""
    return ib.queues(env, q=q, limit=limit)


@router.get("/queues/{queuename}")
def get_queue(queuename: str, env: str = Query(psdb.default_env())):
    """Return a single queue definition with runtime depth counts."""
    return ib.queue(env, queuename)


# ──────────────────────────────────────────────────────────────────────────────
# Transactions (runtime)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/transactions")
def list_transactions(
    env: str = Query(psdb.default_env()),
    q:      str = Query(""),
    status: str = Query(None, description="Filter by PUBSTATUS code (e.g. 5 for Error)"),
    queue:  str = Query(None, description="Filter by QUEUENAME"),
    limit:  int = Query(100),
):
    """Browse IB transaction headers (PSAPMSGPUBHDR), newest first."""
    return ib.transactions(env, q=q, status=status, queue_name=queue, limit=limit)


@router.get("/transactions/{txid}")
def get_transaction(txid: str, env: str = Query(psdb.default_env())):
    """Return a single IB transaction with pub/sub contracts."""
    return ib.transaction(env, txid)


# ──────────────────────────────────────────────────────────────────────────────
# Integration Groups
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/groups")
def list_groups(
    env: str = Query(psdb.default_env()),
    q:     str = Query(""),
    limit: int = Query(100),
):
    """Search integration group definitions (PSIBGROUPDEFN)."""
    return ib.groups(env, q=q, limit=limit)


# ──────────────────────────────────────────────────────────────────────────────
# Domain status
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/domain")
def get_domain_status(env: str = Query(psdb.default_env())):
    """Return IB domain / dispatcher status (PSAPMSGDOMSTAT)."""
    return ib.domain_status(env)
