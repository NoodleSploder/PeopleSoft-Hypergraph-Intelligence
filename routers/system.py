from fastapi import APIRouter
from connectors import system

router = APIRouter()

@router.get("/api/metrics/host")
def host_metrics():
    return system.host_metrics()

@router.get("/api/system/service/{service}")
def system_service(service: str):
    return system.service_status(service)

@router.get("/api/logs/journal")
def journal_logs(units: str = "nginx,deathstar-api", lines: int = 100):
    return system.journal(units, lines)
