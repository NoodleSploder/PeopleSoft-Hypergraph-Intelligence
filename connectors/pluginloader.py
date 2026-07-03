"""
Plugin discovery/loader.

Scans a `plugins/` directory (repo root by default) for plugin modules —
either `plugins/<name>.py` or `plugins/<name>/__init__.py` — imports each,
and calls its `register(sdk)` function if present. `sdk` is simply the
`connectors.plugins` module: the plugin calls `sdk.register_object_provider(...)`
etc.

Isolated per-plugin: one broken plugin (import error, exception in
register()) is logged and skipped — it never prevents the rest of the
platform, or other plugins, from starting. Same isolation philosophy as
connectors/graphdb.py's provider() wrapper around each KG builder.
"""

import importlib.util
import logging
from pathlib import Path

from connectors import plugins as sdk

logger = logging.getLogger("deathstar.pluginloader")


def discover_and_load(app=None, plugins_dir: str = "plugins") -> list[str]:
    """Import every plugin module under plugins_dir and call its register(sdk).

    If `app` (a FastAPI instance) is given, any router the plugin registers
    via sdk.register_router() is included on it immediately after that
    plugin loads. Returns the list of plugin names successfully loaded.
    """
    base = Path(__file__).parent.parent / plugins_dir
    if not base.exists():
        logger.info("pluginloader: no %s directory — skipping plugin discovery", plugins_dir)
        return []

    loaded = []
    candidates = sorted(base.glob("*.py")) + sorted(p for p in base.iterdir() if p.is_dir() and (p / "__init__.py").exists())
    for path in candidates:
        if path.name.startswith("_"):
            continue
        name = path.stem if path.is_file() else path.name
        module_file = path if path.is_file() else (path / "__init__.py")
        try:
            spec = importlib.util.spec_from_file_location(f"deathstar_plugin_{name}", module_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            routers_before = len(sdk.get_routers())
            if hasattr(module, "register"):
                module.register(sdk)
            sdk.mark_loaded(name)
            loaded.append(name)

            if app is not None:
                for router in sdk.get_routers()[routers_before:]:
                    app.include_router(router)

            logger.info("pluginloader: loaded plugin '%s'", name)
        except Exception as exc:
            logger.warning("pluginloader: failed to load plugin '%s' — %s", name, exc)

    return loaded
