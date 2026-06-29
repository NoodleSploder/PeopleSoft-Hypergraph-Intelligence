import re
from collections import Counter
from pathlib import Path

NGINX_ACCESS_LOG = Path("/opt/nginx/logs/access.log")
NGINX_ERROR_LOG = Path("/opt/nginx/logs/error.log")

LOG_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<uri>\S+) (?P<proto>[^"]+)" '
    r'(?P<status>\d+) (?P<size>\S+) '
    r'"(?P<referrer>[^"]*)" "(?P<agent>[^"]*)" '
    r'host="(?P<host>[^"]*)" '
    r'request_time="(?P<request_time>[^"]*)" '
    r'upstream_time="(?P<upstream_time>[^"]*)" '
    r'upstream_addr="(?P<upstream_addr>[^"]*)"'
)


def access_logs(lines: int = 100):
    if not NGINX_ACCESS_LOG.exists():
        return {"error": "access.log not found"}

    output = NGINX_ACCESS_LOG.read_text(errors="ignore").splitlines()[-lines:]

    return {
        "source": str(NGINX_ACCESS_LOG),
        "lines": output
    }


def error_logs(lines: int = 100):
    if not NGINX_ERROR_LOG.exists():
        return {"error": "error.log not found"}

    output = NGINX_ERROR_LOG.read_text(errors="ignore").splitlines()[-lines:]

    return {
        "source": str(NGINX_ERROR_LOG),
        "lines": output
    }


def sessions(lines: int = 300):
    if not NGINX_ACCESS_LOG.exists():
        return {"error": "access.log not found"}

    raw_lines = NGINX_ACCESS_LOG.read_text(errors="ignore").splitlines()[-lines:]

    sessions_by_key = {}
    status_counts = Counter()
    method_counts = Counter()
    uri_counts = Counter()
    host_counts = Counter()
    upstream_counts = Counter()

    for line in raw_lines:
        match = LOG_RE.match(line)
        if not match:
            continue

        item = match.groupdict()

        ip = item["ip"]
        status = item["status"]
        method = item["method"]
        uri = item["uri"]
        agent = item["agent"]
        host = item.get("host", "").lower().split(":")[0]
        upstream_addr = item.get("upstream_addr") or ""
        request_time = item.get("request_time") or ""
        upstream_time = item.get("upstream_time") or ""

        session_key = f"{host}|{ip}"

        status_counts[status] += 1
        method_counts[method] += 1
        uri_counts[uri] += 1
        host_counts[host] += 1
        if upstream_addr:
            upstream_counts[upstream_addr] += 1

        if session_key not in sessions_by_key:
            sessions_by_key[session_key] = {
                "session_key": session_key,
                "ip": ip,
                "host": host,
                "request_count": 0,
                "last_seen": item["time"],
                "last_uri": uri,
                "last_status": status,
                "last_request_time": request_time,
                "last_upstream_time": upstream_time,
                "last_upstream_addr": upstream_addr,
                "user_agents": Counter(),
                "requests": []
            }

        session = sessions_by_key[session_key]
        session["request_count"] += 1
        session["last_seen"] = item["time"]
        session["last_uri"] = uri
        session["last_status"] = status
        session["last_request_time"] = request_time
        session["last_upstream_time"] = upstream_time
        session["last_upstream_addr"] = upstream_addr
        session["user_agents"][agent] += 1
        session["requests"].append({
            "time": item["time"],
            "host": host,
            "method": method,
            "uri": uri,
            "status": status,
            "size": item["size"],
            "referrer": item["referrer"],
            "agent": agent,
            "request_time": request_time,
            "upstream_time": upstream_time,
            "upstream_addr": upstream_addr
        })

    result = []

    for session in sessions_by_key.values():
        session["user_agents"] = dict(session["user_agents"].most_common(3))
        session["requests"] = session["requests"][-10:]
        result.append(session)

    result.sort(key=lambda x: x["request_count"], reverse=True)

    return {
        "source": str(NGINX_ACCESS_LOG),
        "lines_scanned": len(raw_lines),
        "client_count": len(result),
        "status_counts": dict(status_counts),
        "method_counts": dict(method_counts),
        "host_counts": dict(host_counts),
        "upstream_counts": dict(upstream_counts),
        "top_uris": dict(uri_counts.most_common(10)),
        "sessions": result
    }
