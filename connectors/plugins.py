"""
Plugin SDK registries (Phase 9 — Platform Extensibility).

Six appendable registries that let a plugin extend the platform without
editing core files:
  - object providers  (new UOM object types, e.g. /admin/object/{type}/{name})
  - graph providers    (new Knowledge Graph node/edge builders)
  - runtime providers   (new /admin/runtime status sources)
  - health checks       (new operational health checks, e.g. /admin/runtime)
  - source types        (config-driven ingest sources, the SQR/COBOL pattern)
  - nav entries         (new admin dashboard pages in the nav bar)

Plugins call `register_*()` at import time (see connectors/pluginloader.py).
This module is pure Python — no FastAPI/DB imports at module scope — so it
can be imported early and by anything without cycles.
"""

import logging
import threading
import time

logger = logging.getLogger("deathstar.plugins")

_OBJECT_PROVIDERS: dict[str, dict] = {}
_GRAPH_PROVIDERS: list[tuple[str, callable]] = []
_RUNTIME_PROVIDERS: dict[str, dict] = {}
_HEALTH_CHECKS: dict[str, dict] = {}
_SOURCE_TYPES: dict[str, dict] = {}
_NAV_ENTRIES: list[tuple[str, tuple]] = []
_ROUTERS: list = []
_LOADED_PLUGINS: list[str] = []


def register_object_provider(object_type: str, object_fn, payload_fn, registry_meta: dict | None = None):
    """Register a new UOM object type.

    object_fn(env, name) -> object dict (canonical UOM shape)
    payload_fn(obj) -> API/UI payload dict (sections, etc.)
    registry_meta is merged into ptmetadata.OBJECT_REGISTRY[object_type]
    (icon, display_title, graph_node_type, object_page, relationships, ...).
    """
    _OBJECT_PROVIDERS[object_type] = {"object_fn": object_fn, "payload_fn": payload_fn}
    if registry_meta:
        from connectors import ptmetadata
        ptmetadata.OBJECT_REGISTRY.setdefault(object_type, registry_meta)


def register_graph_provider(name: str, loader):
    """Register a Knowledge Graph builder. loader(graph, env, limit) -> int (item count)."""
    _GRAPH_PROVIDERS.append((name, loader))


def register_runtime_provider(name: str, fetch_fn, label: str = "", admin_render=None):
    """Register a runtime status source. fetch_fn(env) -> dict.
    admin_render(data) -> HTML string, optional (falls back to a generic
    key/value dump in the admin UI if omitted)."""
    _RUNTIME_PROVIDERS[name] = {"fetch_fn": fetch_fn, "label": label or name, "admin_render": admin_render}


def register_health_check(name: str, check_fn, label: str = ""):
    """Register an operational health check. check_fn(env) -> dict, at
    minimum {"status": "ok"|"warn"|"error", "message": str}. Run on demand
    (not polled) by GET /api/runtime/health-checks; surfaced on
    /admin/runtime alongside the existing Plugin Providers card."""
    _HEALTH_CHECKS[name] = {"check_fn": check_fn, "label": label or name}


def register_source_type(name: str, config_key: str, ingest_fn, status_fn=None, label: str = ""):
    """Register a config-driven ingest source, replicating the SQR/COBOL
    pattern (a config.json array of {env, key, source_type, ...} entries +
    an SSH-fetch-and-index pipeline) without a plugin needing to hand-roll
    its own background-thread/lock/status-tracking boilerplate.

    config_key: top-level config.json key holding this source type's list
        of source entries (e.g. "sqr_sources" is the built-in precedent).
    ingest_fn(): callable, triggers a full reindex; run in a background
        thread by the SDK (same threading/locking pattern already used by
        routers/sqr.py and routers/cobol.py's own ingest triggers), so the
        plugin only needs to write the ingest logic itself.
    status_fn(): optional callable returning current index stats. If
        omitted, GET /api/plugins/sources/{name}/status falls back to the
        SDK's own generically-tracked last-ingest-result.
    """
    _SOURCE_TYPES[name] = {
        "config_key": config_key, "ingest_fn": ingest_fn, "status_fn": status_fn,
        "label": label or name, "running": False, "last_result": None,
    }


def trigger_source_ingest(name: str) -> dict:
    """Start a registered source type's ingest_fn in a background thread
    (skips if already running). Returns {"status": "started"|"already_running"}."""
    entry = _SOURCE_TYPES.get(name)
    if not entry:
        return {"status": "not_found"}
    if entry["running"]:
        return {"status": "already_running"}
    entry["running"] = True

    def _run():
        try:
            result = entry["ingest_fn"]()
            entry["last_result"] = {
                "status": "ok", "result": result,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        except Exception as exc:
            entry["last_result"] = {
                "status": "error", "error": str(exc),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        finally:
            entry["running"] = False

    threading.Thread(target=_run, daemon=True, name=f"plugin-source-ingest-{name}").start()
    return {"status": "started"}


def get_source_type_status(name: str) -> dict:
    entry = _SOURCE_TYPES.get(name)
    if not entry:
        return {"error": f"No source type registered as '{name}'"}
    if entry["status_fn"]:
        try:
            return entry["status_fn"]()
        except Exception as exc:
            return {"error": str(exc)}
    return {"running": entry["running"], "last_result": entry["last_result"]}


def get_source_types() -> dict[str, dict]:
    return dict(_SOURCE_TYPES)


def register_nav_entry(group_label: str, key: str, label: str, href: str):
    """Register a nav bar entry pointing at a plugin's own admin page."""
    _NAV_ENTRIES.append((group_label, (key, label, href)))


def register_router(router):
    """Register a FastAPI APIRouter (the plugin's own admin page/API routes)."""
    _ROUTERS.append(router)


def get_object_provider(object_type: str):
    return _OBJECT_PROVIDERS.get(object_type)


def get_graph_providers() -> list[tuple[str, callable]]:
    return list(_GRAPH_PROVIDERS)


def get_runtime_providers() -> dict[str, dict]:
    return dict(_RUNTIME_PROVIDERS)


def get_health_checks() -> dict[str, dict]:
    return dict(_HEALTH_CHECKS)


def get_nav_entries() -> list[tuple[str, tuple]]:
    return list(_NAV_ENTRIES)


def get_routers() -> list:
    return list(_ROUTERS)


def mark_loaded(plugin_name: str):
    _LOADED_PLUGINS.append(plugin_name)


def status() -> dict:
    """Introspection: what got loaded and what each registry currently holds."""
    return {
        "loaded_plugins": list(_LOADED_PLUGINS),
        "object_providers": sorted(_OBJECT_PROVIDERS.keys()),
        "graph_providers": [name for name, _ in _GRAPH_PROVIDERS],
        "runtime_providers": sorted(_RUNTIME_PROVIDERS.keys()),
        "health_checks": sorted(_HEALTH_CHECKS.keys()),
        "source_types": sorted(_SOURCE_TYPES.keys()),
        "nav_entries": [entry[1][0] for entry in _NAV_ENTRIES],
        "routers": len(_ROUTERS),
    }
