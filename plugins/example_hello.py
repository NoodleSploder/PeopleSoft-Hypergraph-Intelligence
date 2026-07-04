"""
Example plugin — proves out all four Plugin SDK extension points end to end.

This is deliberately trivial (in-memory fake data, no DB/SSH) so it reads as
a copy-paste starting point for a real plugin, not a feature in its own
right. See PLUGINS.md at the repo root for the full walkthrough.

Registers:
  - an object provider  ("hello_widget" — visible in Object/Graph Explorer)
  - a graph provider     (adds hello_widget nodes/edges to the Knowledge Graph)
  - a runtime provider   (static status, visible on /admin/runtime)
  - a health check       (widgets-degraded check, visible on /admin/runtime)
  - a source type        (config-driven ingest, GET/POST /api/plugins/sources/hello_widgets)
  - a nav entry + admin page (/admin/plugin/hello, under a "Plugins" nav group)
"""

import time

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

_WIDGETS = {
    "ALPHA": {"status": "OK", "record": "JOB"},
    "BRAVO": {"status": "OK", "record": "PERSONAL_DATA"},
    "CHARLIE": {"status": "DEGRADED", "record": "JOB"},
}

_ingest_count = 0
_last_ingest_ts = None


# ── object provider ──────────────────────────────────────────────────────────

def _widget_object(env, name):
    from connectors import uom
    name = name.upper()
    widget = _WIDGETS.get(name)
    if not widget:
        return {"status": "not_found"}
    return uom.canonical_base(
        env, "hello_widget", name,
        description=f"Example plugin widget {name}",
        status=widget["status"],
        _relationships={"records": [widget["record"]]},
    )


def _widget_payload(obj):
    return {
        "type": "hello_widget",
        "name": obj["name"],
        "title": f"Hello Widget: {obj['name']}",
        "sections": [{
            "id": "overview",
            "title": "Overview",
            "type": "kv",
            "rows": [
                {"label": "Status", "value": obj.get("status", "unknown")},
                {"label": "Record", "value": (obj.get("_relationships") or {}).get("records", ["—"])[0]},
            ],
        }],
    }


# ── graph provider ────────────────────────────────────────────────────────────

def _widget_graph_loader(graph, env, limit):
    from connectors import graphdb
    added = 0
    for name, widget in _WIDGETS.items():
        graphdb.add_node(graph, "hello_widget", name, name, widget)
        graphdb.add_node(graph, "record", widget["record"], widget["record"], {})
        graphdb.add_edge(graph, "hello_widget", name, "record", widget["record"], "USES", widget)
        added += 1
    return added


# ── runtime provider ──────────────────────────────────────────────────────────

def _widget_runtime_status(env):
    healthy = sum(1 for w in _WIDGETS.values() if w["status"] == "OK")
    return {
        "widgets_total": len(_WIDGETS),
        "widgets_healthy": healthy,
        "widgets_degraded": len(_WIDGETS) - healthy,
        "env": env,
    }


# ── health check ──────────────────────────────────────────────────────────────

def _widget_health_check(env):
    degraded = [name for name, w in _WIDGETS.items() if w["status"] != "OK"]
    if not degraded:
        return {"status": "ok", "message": f"All {len(_WIDGETS)} widgets healthy"}
    return {
        "status": "warn",
        "message": f"{len(degraded)} widget(s) degraded: {', '.join(degraded)}",
    }


# ── source type ───────────────────────────────────────────────────────────────
# Mirrors the SQR/COBOL config-driven ingest pattern: a config.json array
# (here "hello_sources", deliberately absent from config.json — an empty
# list is the honest, correct result for a demo source with nothing real to
# ingest, same as any other real-but-unpopulated case elsewhere in this
# codebase) + an ingest_fn the SDK runs in a background thread for you.

def _widget_ingest():
    """Deliberately trivial 'reindex' — real plugins would SSH-fetch source,
    parse it, and write to their own SQLite store here, same shape as
    connectors/sqringest.py's index_all()."""
    global _ingest_count, _last_ingest_ts
    _ingest_count += 1
    _last_ingest_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {"widgets_indexed": len(_WIDGETS), "run": _ingest_count}


def _widget_source_status():
    return {"ingest_count": _ingest_count, "last_ingest_ts": _last_ingest_ts}


# ── admin page ────────────────────────────────────────────────────────────────

_router = APIRouter()


@_router.get("/admin/plugin/hello", response_class=HTMLResponse)
def _admin_hello_page():
    from routers.admin._core import _shell
    rows = "".join(
        f"<tr><td>{name}</td><td>{w['status']}</td><td>{w['record']}</td>"
        f"<td><a href='/admin/object/hello_widget/{name}'>Object Explorer</a></td></tr>"
        for name, w in _WIDGETS.items()
    )
    content = f"""
    <p style="color:#7faab2;font-size:12px">
      Example plugin (plugins/example_hello.py) — proves out the Plugin SDK's
      six extension points: object provider, graph provider, runtime
      provider, health check, source type, and this admin page itself.
    </p>
    <table><thead><tr><th>Widget</th><th>Status</th><th>Record</th><th>&nbsp;</th></tr></thead>
    <tbody>{rows}</tbody></table>
    """
    return HTMLResponse(_shell("Hello Plugin", "plugin_hello", content))


def register(sdk):
    sdk.register_object_provider(
        "hello_widget", _widget_object, _widget_payload,
        registry_meta={
            "display_title": "Hello Widget",
            "icon": "puzzle",
            "graph_node_type": "hello_widget",
            "object_page": "/admin/object/hello_widget/{name}",
            "discovery": None,
            "search": None,
            "supported_versions": [],
            "relationships": ["USES"],
        },
    )
    sdk.register_graph_provider("hello_widgets", _widget_graph_loader)
    sdk.register_runtime_provider("hello", _widget_runtime_status, label="Hello Widgets")
    sdk.register_health_check("hello_widgets", _widget_health_check, label="Hello Widgets Health")
    sdk.register_source_type(
        "hello_widgets", "hello_sources", _widget_ingest,
        status_fn=_widget_source_status, label="Hello Widgets Source",
    )
    sdk.register_nav_entry("Plugins", "plugin_hello", "Hello Plugin", "/admin/plugin/hello")
    sdk.register_router(_router)
