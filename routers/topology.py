import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

STATUS_JSON = Path("/opt/nginx/shared/status/status.json")


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

    nodes = [
        {
            "id": "internet",
            "label": "INTERNET",
            "kind": "edge",
            "status": "ONLINE",
            "target": "10443 ingress",
            "meta": ""
        },
        node("nginx", "NGINX", "Nginx", "proxy"),
        node("hcm_web", "HCMDMO_WEB"),
        node("hcm_app", "HCMDMO_APP"),
        node("fscm_web", "FSCMDMO_WEB"),
        node("fscm_app", "FSCMDMO_APP"),
        node("oracle", "ORACLE DB", "Oracle DB", "database"),
        node("opensearch", "OPENSEARCH", "OpenSearch", "search"),
    ]

    links = [
        {"from": "internet", "to": "nginx"},
        {"from": "nginx", "to": "hcm_web"},
        {"from": "nginx", "to": "fscm_web"},
        {"from": "hcm_web", "to": "hcm_app"},
        {"from": "fscm_web", "to": "fscm_app"},
        {"from": "hcm_app", "to": "oracle"},
        {"from": "fscm_app", "to": "oracle"},
        {"from": "hcm_web", "to": "opensearch"},
        {"from": "fscm_web", "to": "opensearch"},
    ]

    return {
        "generated_at": data.get("generated_at"),
        "nodes": nodes,
        "links": links
    }
