import json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

STATUS_JSON = Path("/opt/nginx/shared/status/status.json")

@router.get("/api/health")
def health():
    if STATUS_JSON.exists():
        return JSONResponse(json.loads(STATUS_JSON.read_text()))
    return {"systems": [], "error": "status.json not found"}
