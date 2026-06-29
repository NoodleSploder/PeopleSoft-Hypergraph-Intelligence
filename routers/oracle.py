from fastapi import APIRouter
from connectors import oracle

router = APIRouter()


@router.get("/api/oracle/listener")
def oracle_listener():
    return oracle.listener_status()


@router.get("/api/oracle/health")
def oracle_health():
    return oracle.health()


@router.get("/api/oracle/instances")
def oracle_instances():
    return oracle.instances()


@router.get("/api/oracle/sessions")
def oracle_sessions():
    return oracle.sessions()

@router.get("/api/oracle/tablespaces")
def oracle_tablespaces():
    return oracle.tablespaces()


@router.get("/api/oracle/blocking")
def oracle_blocking():
    return oracle.blocking_sessions()


@router.get("/api/oracle/longops")
def oracle_longops():
    return oracle.longops()
