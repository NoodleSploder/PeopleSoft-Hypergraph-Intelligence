import asyncio
import json
import os
import re
import time
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from connectors import nginx as nginx_connector
from connectors import oracle as oracle_connector
from connectors import system as system_connector
from config.applications import APPLICATIONS

router = APIRouter()

NGINX_ACCESS_LOG = os.getenv("NGINX_ACCESS_LOG", "/opt/nginx/logs/access.log")

ACCESS_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<uri>\S+) (?P<proto>[^"]+)" '
    r'(?P<status>\d{3}) (?P<size>\S+) '
    r'"(?P<referrer>[^"]*)" "(?P<agent>[^"]*)" '
    r'host="(?P<host>[^"]*)" '
    r'request_time="(?P<request_time>[^"]*)" '
    r'upstream_time="(?P<upstream_time>[^"]*)" '
    r'upstream_addr="(?P<upstream_addr>[^"]*)"'
)


def ts():
    return datetime.now().strftime("%H:%M:%S")


def make_event(kind, source, message, severity="info", data=None):
    return {
        "ts": ts(),
        "epoch": time.time(),
        "kind": kind,
        "source": source,
        "severity": severity,
        "message": message,
        "data": data or {},
    }


def severity_for_status(status):
    try:
        code = int(status)
    except Exception:
        return "info"

    if code >= 500:
        return "error"
    if code >= 400:
        return "warn"
    if code >= 300:
        return "info"
    return "ok"


def normalize_host(value):
    return str(value or "").lower().split(":")[0].strip()


def classify_session(s):
    host = normalize_host(
        s.get("host")
        or s.get("hostname")
        or s.get("server_name")
        or s.get("http_host")
    )

    app_info = APPLICATIONS.get(host)

    if app_info:
        return {
            "host": host,
            "session_type": app_info.get("type", "application"),
            "application": app_info.get("name", host),
            "group": app_info.get("group", "UNKNOWN"),
            "web_server": app_info.get("web", "UNKNOWN"),
            "app_server": app_info.get("app", "UNKNOWN"),
            "backend": app_info.get("backend", app_info.get("db", "UNKNOWN")),
            "database": app_info.get("db"),
        }

    return {
        "host": host,
        "session_type": "unknown",
        "application": "Unknown",
        "group": "UNKNOWN",
        "web_server": "UNKNOWN",
        "app_server": "UNKNOWN",
        "backend": "UNKNOWN",
        "database": None,
    }


async def nginx_log_events(queue: asyncio.Queue):
    while not os.path.exists(NGINX_ACCESS_LOG):
        await queue.put(make_event(
            "system",
            "nginx",
            f"Waiting for nginx access log: {NGINX_ACCESS_LOG}",
            "warn",
        ))
        await asyncio.sleep(5)

    with open(NGINX_ACCESS_LOG, "r", errors="ignore") as fh:
        fh.seek(0, os.SEEK_END)

        while True:
            line = fh.readline()

            if not line:
                await asyncio.sleep(0.25)
                continue

            line = line.strip()
            match = ACCESS_RE.search(line)

            if not match:
                await queue.put(
                    make_event(
                        "nginx",
                        "nginx",
                        line[:240],
                        "info",
                        {"raw": line},
                    )
                )
                continue

            d = match.groupdict()
            status = d["status"]

            message = (
                f'{d["method"]} {d["uri"]} '
                f'{status} ({d.get("request_time", "?")}s)'
            )

            await queue.put(
                make_event(
                    "http",
                    d["ip"],
                    message,
                    severity_for_status(status),
                    {
                        "ip": d["ip"],
                        "host": normalize_host(d.get("host")),
                        "method": d["method"],
                        "uri": d["uri"],
                        "status": int(status),
                        "request_time": d.get("request_time"),
                        "upstream_time": d.get("upstream_time"),
                        "upstream_addr": d.get("upstream_addr"),
                        "referrer": d.get("referrer"),
                        "user_agent": d.get("agent"),
                        "raw": line,
                    },
                )
            )


async def oracle_pulse_events(queue: asyncio.Queue):
    last = None

    while True:
        try:
            data = oracle_connector.listener_status()
            status = str(data.get("status", "UNKNOWN")).upper()
        except Exception as exc:
            status = "ERROR"
            data = {"error": str(exc)}

        if status != last:
            severity = "ok" if status == "ONLINE" else "error"
            
            message = "Oracle listener responding" if status == "ONLINE" else "Oracle listener not responding"

            await queue.put(make_event(
                "oracle",
                "oracle",
                message,
                severity,
                data,
            ))

            last = status

        await asyncio.sleep(10)


async def system_pulse_events(queue: asyncio.Queue):
    last_nginx = None

    while True:
        try:
            data = system_connector.service_status("nginx")
            status = str(data.get("status", "UNKNOWN")).upper()
        except Exception as exc:
            status = "ERROR"
            data = {"error": str(exc)}

        if status != last_nginx:
            severity = "ok" if status in ("ACTIVE", "ONLINE", "RUNNING") else "warn"
            await queue.put(make_event(
                "system",
                "nginx",
                f"Nginx service status: {status}",
                severity,
                data,
            ))
            last_nginx = status

        await asyncio.sleep(15)


async def event_stream():
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)

    tasks = [
        asyncio.create_task(nginx_log_events(queue)),
        asyncio.create_task(oracle_pulse_events(queue)),
        asyncio.create_task(system_pulse_events(queue)),
    ]

    try:
        yield make_event("system", "deathstar", "Live operations stream connected", "ok")

        while True:
            item = await queue.get()
            yield item

    finally:
        for task in tasks:
            task.cancel()


@router.get("/api/live/events")
async def live_events():
    async def sse():
        async for item in event_stream():
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/live/sessions")
def live_sessions(lines: int = 500):
    nginx_data = nginx_connector.sessions(lines)

    sessions = []

    for s in nginx_data.get("sessions", []):
        uri = s.get("last_uri") or s.get("uri") or ""
        ip = s.get("ip") or s.get("client_ip") or "unknown"
        classified = classify_session(s)

        sessions.append({
            "client_ip": ip,
            "browser": s.get("browser") or s.get("user_agent") or "Unknown",
            "method": s.get("method") or "GET",
            "uri": uri,
            "cookies": s.get("cookies") or [],
            "status": "active",
            "oracle_sid": s.get("oracle_sid"),
            "request_count": s.get("request_count", 0),
            "last_seen": s.get("last_seen"),
            "raw": s,
            **classified,
        })

    return {
        "status": "ok",
        "source": "nginx",
        "client_count": nginx_data.get("client_count", len(sessions)),
        "sessions": sessions,
        "nginx": nginx_data,
    }


@router.get("/api/live/transactions")
def live_transactions(lines: int = 500):
    nginx_data = nginx_connector.sessions(lines)

    transactions = []

    for s in nginx_data.get("sessions", []):
        classified = classify_session(s)

        for req in s.get("requests", [])[-25:]:
            status = int(req.get("status") or 0)
            request_time = req.get("request_time")
            upstream_time = req.get("upstream_time")
            upstream_addr = req.get("upstream_addr")

            severity = "ok"
            if status >= 500:
                severity = "error"
            elif status >= 400:
                severity = "warn"

            transactions.append({
                "id": f'{s.get("session_key", s.get("ip", ""))}|{req.get("time", "")}|{req.get("uri", "")}',
                "time": req.get("time"),
                "client_ip": s.get("ip"),
                "host": s.get("host"),
                "application": classified.get("application"),
                "session_type": classified.get("session_type"),
                "group": classified.get("group"),
                "method": req.get("method"),
                "uri": req.get("uri"),
                "status": status,
                "severity": severity,
                "request_time": request_time,
                "upstream_time": upstream_time,
                "upstream_addr": upstream_addr,
                "web_server": classified.get("web_server"),
                "app_server": classified.get("app_server"),
                "backend": classified.get("backend"),
                "database": classified.get("database"),
                "stages": [
                    {
                        "name": "Client",
                        "type": "client",
                        "target": s.get("ip"),
                        "status": "ok",
                    },
                    {
                        "name": "NGINX",
                        "type": "proxy",
                        "target": s.get("host"),
                        "status": severity,
                    },
                    {
                        "name": classified.get("web_server"),
                        "type": "web",
                        "target": upstream_addr,
                        "status": severity,
                    },
                    {
                        "name": classified.get("app_server"),
                        "type": "app",
                        "target": classified.get("group"),
                        "status": severity,
                    },
                    {
                        "name": classified.get("backend"),
                        "type": "backend",
                        "target": classified.get("database") or upstream_addr,
                        "status": severity,
                    },
                ],
            })

    transactions.sort(key=lambda x: x.get("time") or "", reverse=True)

    return {
        "status": "ok",
        "source": "nginx",
        "count": len(transactions),
        "transactions": transactions[:100],
    }


def parse_peoplesoft_uri(uri: str):
    parts = [p for p in str(uri or "").split("/") if p]

    result = {
        "is_peoplesoft": False,
        "site": None,
        "environment": None,
        "portal": None,
        "node": None,
        "mode": None,
        "component": None,
        "market": None,
        "raw_parts": parts,
    }

    if len(parts) < 2:
        return result

    if parts[0].lower() not in ("psc", "psp"):
        return result

    result["is_peoplesoft"] = True
    result["site"] = parts[0].lower()
    result["environment"] = parts[1] if len(parts) > 1 else None
    result["portal"] = parts[2] if len(parts) > 2 else None
    result["node"] = parts[3] if len(parts) > 3 else None
    result["mode"] = parts[4] if len(parts) > 4 else None

    obj = parts[5] if len(parts) > 5 else ""
    tokens = obj.split(".")

    if len(tokens) >= 2:
        result["component"] = tokens[-2]
        result["market"] = tokens[-1]

    return result


