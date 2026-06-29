from fastapi import APIRouter
from connectors import nginx

router = APIRouter()

@router.get("/api/logs/nginx")
def nginx_logs(lines: int = 100):
    return nginx.access_logs(lines)

@router.get("/api/logs/nginx/error")
def nginx_error_logs(lines: int = 100):
    return nginx.error_logs(lines)

@router.get("/api/sessions/nginx")
def nginx_sessions(lines: int = 300):
    return nginx.sessions(lines)

