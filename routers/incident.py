"""
Incident REST API.

POST   /api/incidents                  Create incident (optionally capture RCA snapshot)
GET    /api/incidents                  List incidents (?state=open|resolved &env=)
GET    /api/incidents/{id}             Get incident + snapshots
PATCH  /api/incidents/{id}             Update (title, severity, state, notes)
DELETE /api/incidents/{id}             Delete incident
GET    /api/incidents/{id}/snapshot    Re-run RCA and save snapshot against incident
"""

import datetime as _dt

from fastapi import APIRouter, HTTPException, Body

from connectors import incidentdb
from connectors import execution

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("")
def create_incident(body: dict = Body(...)):
    """
    Required body fields: title, env
    Optional: severity (P1-P4), window_start, window_end, notes, capture_rca (bool)
    """
    title    = (body.get("title") or "").strip()
    env      = (body.get("env")   or "HCM").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required")
    severity = body.get("severity", "P3")
    if severity not in ("P1", "P2", "P3", "P4"):
        severity = "P3"

    window_end   = body.get("window_end")   or _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    window_start = body.get("window_start") or (
        _dt.datetime.utcnow() - _dt.timedelta(hours=1)
    ).strftime("%Y-%m-%d %H:%M:%S")

    inc_id = incidentdb.create_incident(
        title        = title,
        env          = env,
        severity     = severity,
        window_start = window_start,
        window_end   = window_end,
        notes        = body.get("notes", ""),
    )

    if body.get("capture_rca", True):
        try:
            rca_data = execution.rca_snapshot(env, window_start, window_end)
            incidentdb.add_snapshot(inc_id, "rca", rca_data)
        except Exception as exc:
            incidentdb.add_snapshot(inc_id, "rca", {"error": str(exc)})

    return {"id": inc_id, "status": "created"}


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("")
def list_incidents(state: str = None, env: str = None, limit: int = 200):
    return incidentdb.list_incidents(state=state or None, env=env or None, limit=limit)


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
def incident_stats():
    return incidentdb.stats()


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get("/{incident_id}")
def get_incident(incident_id: int):
    inc = incidentdb.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc["snapshots"] = incidentdb.get_snapshots(incident_id)
    return inc


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{incident_id}")
def update_incident(incident_id: int, body: dict = Body(...)):
    inc = incidentdb.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    ok = incidentdb.update_incident(incident_id, **body)
    return {"updated": ok}


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{incident_id}")
def delete_incident(incident_id: int):
    ok = incidentdb.delete_incident(incident_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"deleted": True}


# ── Re-snapshot ───────────────────────────────────────────────────────────────

@router.get("/{incident_id}/snapshot")
def refresh_snapshot(incident_id: int):
    """Re-run the RCA against the incident window and attach a new snapshot."""
    inc = incidentdb.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    try:
        rca_data = execution.rca_snapshot(
            inc["env"],
            inc.get("window_start") or "",
            inc.get("window_end")   or "",
        )
        snap_id = incidentdb.add_snapshot(incident_id, "rca", rca_data)
        return {"snapshot_id": snap_id, "status": "captured"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
