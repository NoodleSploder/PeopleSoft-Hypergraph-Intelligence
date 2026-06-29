import json
from pathlib import Path

STATUS_JSON = Path("/opt/nginx/shared/status/status.json")


ENV_MAP = {
    "HCM": ["HCMDMO_WEB", "HCMDMO_APP", "HCMDMO_PRCS"],
    "FSCM": ["FSCMDMO_WEB", "FSCMDMO_APP", "FSCMDMO_PRCS"],
}


def load_systems():
    if not STATUS_JSON.exists():
        return []
    return json.loads(STATUS_JSON.read_text()).get("systems", [])


def summary():
    systems = load_systems()
    by_name = {s.get("name", "").upper(): s for s in systems}

    envs = []
    for env, names in ENV_MAP.items():
        items = [by_name.get(name, {"name": name, "status": "UNKNOWN"}) for name in names]
        faulted = [i for i in items if i.get("status") not in ("ONLINE", "DISABLED")]

        envs.append({
            "environment": env,
            "status": "READY" if not faulted else "WARN",
            "fault_count": len(faulted),
            "systems": items,
        })

    return {"environments": envs}


def environment(env: str):
    env = env.upper()
    if env not in ENV_MAP:
        return {"error": f"Unknown PeopleSoft environment: {env}"}

    systems = load_systems()
    by_name = {s.get("name", "").upper(): s for s in systems}
    items = [by_name.get(name, {"name": name, "status": "UNKNOWN"}) for name in ENV_MAP[env]]
    faulted = [i for i in items if i.get("status") not in ("ONLINE", "DISABLED")]

    return {
        "environment": env,
        "status": "READY" if not faulted else "WARN",
        "fault_count": len(faulted),
        "systems": items,
    }
