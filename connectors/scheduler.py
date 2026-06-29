"""
Background scheduler for periodic graph snapshots and retention pruning.

Starts a single daemon thread that:
  1. Waits INITIAL_DELAY_SECONDS before its first run (avoids hammering the
     database on every server restart).
  2. Builds and snapshots the knowledge graph for each configured environment.
  3. Prunes old snapshots beyond RETAIN_COUNT.
  4. Sleeps INTERVAL_HOURS * 3600 before repeating.

No external dependencies — pure threading.
"""

import logging
import threading
import time

from connectors import graphdb

logger = logging.getLogger("deathstar.scheduler")

# Configuration — values can be overridden before calling start().
ENVS: list[str] = ["HCM"]
INTERVAL_HOURS: int = 24
RETAIN_COUNT: int = 7
INITIAL_DELAY_SECONDS: int = 300   # 5-minute startup grace period
BUILD_LIMIT: int = 100

_thread: threading.Thread | None = None
_stop_event = threading.Event()
_last_run: dict = {}   # env → ISO timestamp of last successful snapshot
_last_error: dict = {}  # env → last error string


def _run_for_env(env: str) -> None:
    try:
        logger.info("Scheduler: building graph for %s", env)
        graphdb.build(env, limit=BUILD_LIMIT)
        entry = graphdb.create_snapshot(
            env,
            name="scheduled",
            note=f"Auto-snapshot (daily scheduler) — {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        )
        graphdb.prune_snapshots(env, keep=RETAIN_COUNT)
        _last_run[env] = entry.get("created_at", "")
        _last_error.pop(env, None)
        logger.info("Scheduler: snapshot complete for %s (id=%s, nodes=%s, edges=%s)",
                    env, entry.get("id"), entry.get("node_count"), entry.get("edge_count"))
    except Exception as exc:
        _last_error[env] = str(exc)
        logger.warning("Scheduler: snapshot failed for %s: %s", env, exc)


def _loop() -> None:
    logger.info("Snapshot scheduler started (envs=%s, interval=%dh, retain=%d, initial_delay=%ds)",
                ENVS, INTERVAL_HOURS, RETAIN_COUNT, INITIAL_DELAY_SECONDS)
    # Initial delay
    if _stop_event.wait(INITIAL_DELAY_SECONDS):
        return  # stopped before first run
    while not _stop_event.is_set():
        for env in ENVS:
            if _stop_event.is_set():
                break
            _run_for_env(env)
        _stop_event.wait(INTERVAL_HOURS * 3600)
    logger.info("Snapshot scheduler stopped")


def start() -> None:
    global _thread
    if _thread and _thread.is_alive():
        logger.debug("Scheduler already running")
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, name="snapshot-scheduler", daemon=True)
    _thread.start()
    logger.info("Snapshot scheduler thread started")


def stop() -> None:
    _stop_event.set()
    if _thread:
        _thread.join(timeout=5)
    logger.info("Snapshot scheduler thread stopped")


def status() -> dict:
    return {
        "running": bool(_thread and _thread.is_alive()),
        "envs": ENVS,
        "interval_hours": INTERVAL_HOURS,
        "retain_count": RETAIN_COUNT,
        "initial_delay_seconds": INITIAL_DELAY_SECONDS,
        "build_limit": BUILD_LIMIT,
        "last_run": _last_run,
        "last_error": _last_error,
    }
