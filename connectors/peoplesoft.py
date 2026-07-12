import json
from pathlib import Path
from connectors import psdb

STATUS_JSON = Path("/opt/nginx/shared/status/status.json")


def load_systems():
    if not STATUS_JSON.exists():
        return []
    return json.loads(STATUS_JSON.read_text()).get("systems", [])


def _env_map():
    """Map every configured environment (config.json) to whatever
    status.json systems are tracked for it (matched by status.json's
    "group" field). Environments with no monitored services still appear
    — with an empty system list — instead of being silently omitted, so
    this always reflects the full configured environment list, not just
    the ones that happen to have infra monitoring wired up."""
    systems = load_systems()
    by_group = {}
    for s in systems:
        group = str(s.get("group", "")).upper()
        by_group.setdefault(group, []).append(s.get("name", ""))

    return {e["name"]: by_group.get(e["name"].upper(), []) for e in psdb.load_envs()}


def summary():
    systems = load_systems()
    by_name = {s.get("name", "").upper(): s for s in systems}
    env_map = _env_map()

    envs = []
    for env, names in env_map.items():
        items = [by_name.get(name.upper(), {"name": name, "status": "UNKNOWN"}) for name in names]
        faulted = [i for i in items if i.get("status") not in ("ONLINE", "DISABLED")]

        envs.append({
            "environment": env,
            "status": "UNKNOWN" if not items else ("READY" if not faulted else "WARN"),
            "fault_count": len(faulted),
            "systems": items,
        })

    return {"environments": envs}


def environment(env: str):
    env_map = _env_map()
    match = next((name for name in env_map if name.upper() == env.upper()), None)
    if match is None:
        return {"error": f"Unknown PeopleSoft environment: {env}"}

    systems = load_systems()
    by_name = {s.get("name", "").upper(): s for s in systems}
    items = [by_name.get(name.upper(), {"name": name, "status": "UNKNOWN"}) for name in env_map[match]]
    faulted = [i for i in items if i.get("status") not in ("ONLINE", "DISABLED")]

    return {
        "environment": match,
        "status": "UNKNOWN" if not items else ("READY" if not faulted else "WARN"),
        "fault_count": len(faulted),
        "systems": items,
    }
