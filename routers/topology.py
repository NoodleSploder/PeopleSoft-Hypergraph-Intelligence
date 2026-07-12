import json
from pathlib import Path
from fastapi import APIRouter, Query

router = APIRouter()

STATUS_JSON = Path("/opt/nginx/shared/status/status.json")

# Tiers we know how to draw for a PeopleSoft environment "lane", keyed by the
# suffix on the status.json system name (e.g. "HCMDMO_WEB" -> tier "WEB").
_TIER_KIND = {
    "WEB":  "weblogic",
    "APP":  "appserver",
    "PRCS": "prcs",
}


def _discover_lanes(systems):
    """
    Group status.json systems into PeopleSoft environment lanes.

    A lane is any status.json "group" that has at least one WEB/APP/PRCS
    tier system (e.g. group "HCM" with systems "HCMDMO_WEB", "HCMDMO_APP",
    "HCMDMO_PRCS"). This makes the topology reflect whatever environments
    are actually monitored, instead of a fixed HCM/FSCM pair.
    """
    lanes = {}
    for s in systems:
        name = str(s.get("name", ""))
        group = str(s.get("group", ""))
        if "_" not in name:
            continue
        prefix, _, tier = name.rpartition("_")
        tier = tier.upper()
        if tier not in _TIER_KIND:
            continue
        lane = lanes.setdefault(group, {"group": group, "prefix": prefix, "tiers": {}})
        lane["tiers"][tier] = name
    return dict(sorted(lanes.items()))


@router.get("/api/topology")
def topology(env: str = Query(None, description="Limit to a single lane/environment group")):
    if not STATUS_JSON.exists():
        return {"nodes": [], "links": [], "envs": [], "error": "status.json not found"}

    data = json.loads(STATUS_JSON.read_text())
    systems = data.get("systems", [])

    status_by_name = {
        str(s.get("name", "")).upper(): s
        for s in systems
    }

    def node(node_id, label, system_name=None, kind="system", lane=None):
        system = status_by_name.get((system_name or label).upper(), {})
        return {
            "id": node_id,
            "label": label,
            "kind": kind,
            "lane": lane,
            "status": system.get("status", "UNKNOWN"),
            "target": system.get("target", ""),
            "meta": system.get("meta", "")
        }

    all_lanes = _discover_lanes(systems)
    envs = list(all_lanes.keys())
    lanes = {g: l for g, l in all_lanes.items() if not env or g.upper() == env.upper()}

    # ── Shared infrastructure ────────────────────────────────────────────────
    nodes = [
        {
            "id": "browser", "label": "BROWSER", "kind": "client", "lane": None,
            "status": "ONLINE", "target": "end user", "meta": ""
        },
        node("nginx", "NGINX", "Nginx", "proxy"),
        node("oracle", "ORACLE DB", "Oracle DB", "database"),
        node("opensearch", "OPENSEARCH", "OpenSearch", "search"),
    ]
    links = [
        {"from": "browser", "to": "nginx", "label": "HTTPS"},
    ]

    for group, lane in lanes.items():
        gid = group.lower().replace(" ", "_")
        tiers = lane["tiers"]

        if "WEB" in tiers:
            nodes.append(node(f"{gid}_web", tiers["WEB"], tiers["WEB"], "weblogic", lane=group))
            links.append({"from": "nginx", "to": f"{gid}_web", "label": ""})
            links.append({"from": f"{gid}_web", "to": "opensearch", "label": "REST"})
        if "APP" in tiers:
            nodes.append(node(f"{gid}_app", tiers["APP"], tiers["APP"], "appserver", lane=group))
            links.append({"from": f"{gid}_app", "to": "oracle", "label": "SQL*Net"})
            if "WEB" in tiers:
                links.append({"from": f"{gid}_web", "to": f"{gid}_app", "label": "Jolt"})
            # IB runs on the same app server; inherit its status.
            nodes.append({**node(f"{gid}_ib", f"{lane['prefix']}_IB", tiers["APP"], "ib", lane=group),
                          "label": f"{lane['prefix']}_IB"})
            links.append({"from": f"{gid}_app", "to": f"{gid}_ib", "label": "IB"})
            links.append({"from": f"{gid}_ib", "to": "oracle", "label": "SQL*Net"})
        if "PRCS" in tiers:
            nodes.append(node(f"{gid}_prcs", tiers["PRCS"], tiers["PRCS"], "prcs", lane=group))
            links.append({"from": f"{gid}_prcs", "to": "oracle", "label": "SQL*Net"})
            if "APP" in tiers:
                links.append({"from": f"{gid}_app", "to": f"{gid}_prcs", "label": "RPC"})

    return {
        "generated_at": data.get("generated_at"),
        "envs": envs,
        "env": env,
        "nodes": nodes,
        "links": links
    }
