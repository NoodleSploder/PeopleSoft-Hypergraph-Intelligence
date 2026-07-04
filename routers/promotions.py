"""
Promotion Event Log API — manually recorded project promotion events.
Phase 1: manual log. Phase 2: auto-detection from PSPROJECTDEFN when
DV/TST/UAT/PRD DB connections are available.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from connectors import promotiondb, deploymentdb

router = APIRouter(prefix="/api/promotions", tags=["Promotions"])


class PromotionCreate(BaseModel):
    pillar:       str
    project:      str
    from_env:     str
    to_env:       str
    promoted_at:  str           # ISO date or datetime
    promoted_by:  str = None
    notes:        str = None
    ticket_ref:   str = None


@router.post("")
def create_promotion(body: PromotionCreate):
    """Record a promotion event."""
    if not body.pillar or not body.project or not body.from_env or not body.to_env:
        raise HTTPException(status_code=400, detail="pillar, project, from_env, to_env are required")
    if not body.promoted_at:
        raise HTTPException(status_code=400, detail="promoted_at is required")
    promotion = promotiondb.record_promotion(
        pillar=body.pillar,
        project=body.project,
        from_env=body.from_env,
        to_env=body.to_env,
        promoted_at=body.promoted_at,
        promoted_by=body.promoted_by,
        notes=body.notes,
        ticket_ref=body.ticket_ref,
    )
    # Attach a config/drift fingerprint to this promotion automatically —
    # best-effort, never blocks the promotion record itself.
    try:
        deploymentdb.record_deployment_snapshot(env=body.to_env, promotion_id=promotion["id"])
    except Exception:
        pass
    return promotion


@router.get("")
def get_promotions(
    pillar:  str = Query(None),
    project: str = Query(None),
    env:     str = Query(None),
    limit:   int = Query(200),
):
    """List promotion events, newest first. Filter by pillar, project, or env."""
    return {
        "promotions": promotiondb.list_promotions(
            pillar=pillar, project=project, env=env, limit=limit
        )
    }


@router.get("/timeline")
def get_timeline(
    pillar:  str = Query(...),
    project: str = Query(...),
):
    """Chronological promotion timeline for a single project."""
    return {
        "pillar":    pillar.upper(),
        "project":   project.upper(),
        "timeline":  promotiondb.project_timeline(pillar, project),
    }


@router.get("/summary")
def get_summary(pillar: str = Query(...)):
    """Per-project promotion summary for a pillar."""
    return {
        "pillar":   pillar.upper(),
        "projects": promotiondb.pillar_summary(pillar),
    }


@router.delete("/{id}")
def delete_promotion(id: int):
    """Remove a promotion record."""
    if not promotiondb.delete_promotion(id):
        raise HTTPException(status_code=404, detail=f"Promotion {id} not found")
    return {"deleted": id}


@router.get("/{id}/deployment")
def get_promotion_deployment(id: int):
    """Return the config/drift fingerprint captured for this promotion, if any."""
    result = deploymentdb.get_for_promotion(id)
    if not result:
        raise HTTPException(status_code=404, detail=f"No deployment snapshot for promotion {id}")
    return result
