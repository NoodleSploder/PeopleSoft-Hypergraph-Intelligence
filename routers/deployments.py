"""
Deployment/Configuration History API — config-fingerprint timeline per
environment, independent of the promotion log (config can change without a
logged promotion, and vice versa).
"""

from fastapi import APIRouter, Query

from connectors import deploymentdb

router = APIRouter(prefix="/api/deployments", tags=["Deployments"])


@router.get("/{env}/history")
def get_deployment_history(env: str, limit: int = Query(200)):
    """Config-fingerprint timeline for an environment, newest first."""
    return {"env": env.upper(), "history": deploymentdb.get_history(env, limit=limit)}
