import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

STATUS_JSON = Path("/opt/nginx/shared/status/status.json")

# Known group-to-system name mapping (ordered: most specific first)
_HCM_SYSTEMS = {
    "hcm_web":  "HCMDMO_WEB",
    "hcm_app":  "HCMDMO_APP",
    "hcm_prcs": "HCMDMO_PRCS",
    "hcm_ib":   "HCMDMO",       # Integration Broker domain
}
_FSCM_SYSTEMS = {
    "fscm_web":  "FSCMDMO_WEB",
    "fscm_app":  "FSCMDMO_APP",
    "fscm_prcs": "FSCMDMO_PRCS",
    "fscm_ib":   "FSCMDMO",
}


@router.get("/api/topology")
def topology():
    if not STATUS_JSON.exists():
        return {"nodes": [], "links": [], "error": "status.json not found"}

    data = json.loads(STATUS_JSON.read_text())
    systems = data.get("systems", [])

    status_by_name = {
        str(s.get("name", "")).upper(): s
        for s in systems
    }

    def node(node_id, label, system_name=None, kind="system"):
        system = status_by_name.get((system_name or label).upper(), {})
        return {
            "id": node_id,
            "label": label,
            "kind": kind,
            "status": system.get("status", "UNKNOWN"),
            "target": system.get("target", ""),
            "meta": system.get("meta", "")
        }

    # ── Shared infrastructure ────────────────────────────────────────────────
    nodes = [
        {
            "id": "browser",
            "label": "BROWSER",
            "kind": "client",
            "status": "ONLINE",
            "target": "end user",
            "meta": ""
        },
        node("nginx", "NGINX", "Nginx", "proxy"),
        node("oracle", "ORACLE DB", "Oracle DB", "database"),
        node("opensearch", "OPENSEARCH", "OpenSearch", "search"),
    ]

    # ── HCM tier ─────────────────────────────────────────────────────────────
    nodes += [
        node("hcm_web",  "HCMDMO_WEB",  "HCMDMO_WEB",  "weblogic"),
        node("hcm_app",  "HCMDMO_APP",  "HCMDMO_APP",  "appserver"),
        node("hcm_prcs", "HCMDMO_PRCS", "HCMDMO_PRCS", "prcs"),
        # IB runs on the same app server; inherit its status
        {**node("hcm_ib", "HCMDMO_IB", "HCMDMO_APP", "ib"),
         "label": "HCMDMO_IB"},
    ]

    # ── FSCM tier ─────────────────────────────────────────────────────────────
    nodes += [
        node("fscm_web",  "FSCMDMO_WEB",  "FSCMDMO_WEB",  "weblogic"),
        node("fscm_app",  "FSCMDMO_APP",  "FSCMDMO_APP",  "appserver"),
        node("fscm_prcs", "FSCMDMO_PRCS", "FSCMDMO_PRCS", "prcs"),
        # IB runs on the same app server; inherit its status
        {**node("fscm_ib", "FSCMDMO_IB", "FSCMDMO_APP", "ib"),
         "label": "FSCMDMO_IB"},
    ]

    links = [
        # browser → nginx
        {"from": "browser",   "to": "nginx",     "label": "HTTPS"},
        # nginx → web tiers
        {"from": "nginx",     "to": "hcm_web",   "label": "8020"},
        {"from": "nginx",     "to": "fscm_web",  "label": "8010"},
        # web → app servers
        {"from": "hcm_web",   "to": "hcm_app",   "label": "Jolt"},
        {"from": "fscm_web",  "to": "fscm_app",  "label": "Jolt"},
        # app servers → oracle
        {"from": "hcm_app",   "to": "oracle",    "label": "SQL*Net"},
        {"from": "fscm_app",  "to": "oracle",    "label": "SQL*Net"},
        # process schedulers → oracle
        {"from": "hcm_prcs",  "to": "oracle",    "label": "SQL*Net"},
        {"from": "fscm_prcs", "to": "oracle",    "label": "SQL*Net"},
        # app servers → process schedulers
        {"from": "hcm_app",   "to": "hcm_prcs",  "label": "RPC"},
        {"from": "fscm_app",  "to": "fscm_prcs", "label": "RPC"},
        # app servers → IB
        {"from": "hcm_app",   "to": "hcm_ib",    "label": "IB"},
        {"from": "fscm_app",  "to": "fscm_ib",   "label": "IB"},
        # IB → oracle
        {"from": "hcm_ib",    "to": "oracle",    "label": "SQL*Net"},
        {"from": "fscm_ib",   "to": "oracle",    "label": "SQL*Net"},
        # web → opensearch
        {"from": "hcm_web",   "to": "opensearch", "label": "REST"},
        {"from": "fscm_web",  "to": "opensearch", "label": "REST"},
    ]

    return {
        "generated_at": data.get("generated_at"),
        "nodes": nodes,
        "links": links
    }
