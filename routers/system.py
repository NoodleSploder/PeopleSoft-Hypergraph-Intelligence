from fastapi import APIRouter, HTTPException
from connectors import system

router = APIRouter()


@router.get("/api/metrics/host")
def host_metrics():
    return system.host_metrics()


@router.get("/api/system/services")
def system_services():
    return system.services_summary()


@router.get("/api/system/service/{service}")
def system_service(service: str):
    return system.service_status(service)


@router.post("/api/system/service/{unit}/restart")
def restart_service(unit: str):
    return system.restart_service(unit)


@router.post("/api/system/nginx/reload")
def reload_nginx():
    return system.reload_nginx()


@router.get("/api/system/containers")
def list_containers():
    return system.containers()


@router.get("/api/system/containers/{name}/logs")
def container_logs(name: str, lines: int = 50):
    return system.container_logs(name, lines)


@router.post("/api/system/containers/{name}/restart")
def restart_container(name: str):
    return system.restart_container(name)


@router.get("/api/logs/journal")
def journal_logs(units: str = "nginx,deathstar-api", lines: int = 100):
    return system.journal(units, lines)
