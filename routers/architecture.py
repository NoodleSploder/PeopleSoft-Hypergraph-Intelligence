"""
Architecture Assistant API — auto-generated dependency reports, sequence
narratives, and impact summaries as Markdown/Mermaid documents.
"""

from fastapi import APIRouter, HTTPException, Query

from connectors import archreport

router = APIRouter(prefix="/api/architecture", tags=["Architecture"])


@router.get("/dependency-report")
def dependency_report(
    env: str = Query(...),
    node_type: str = Query(...),
    node_name: str = Query(...),
    depth: int = Query(3),
):
    result = archreport.dependency_report(env, node_type, node_name, depth=depth)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=f"No object {node_type}:{node_name} found in {env} knowledge graph")
    return result


@router.get("/sequence-report")
def sequence_report(
    env: str = Query(...),
    target_type: str = Query(...),
    name: str = Query(...),
):
    result = archreport.sequence_narrative(env, target_type, name)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("markdown", "Not found"))
    return result


@router.get("/impact-summary")
def impact_summary(
    env: str = Query(...),
    node_type: str = Query(...),
    node_name: str = Query(...),
    depth: int = Query(2),
):
    result = archreport.impact_summary_doc(env, node_type, node_name, depth=depth)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("markdown", "Not found"))
    return result
