import json
import subprocess
import psutil


# Services to monitor — (display_name, systemd_unit, restartable)
MONITORED_SERVICES = [
    ("NGINX",         "nginx.service",              True),
    ("DeathStar API", "deathstar-api.service",       False),  # restarting self is dangerous
    ("GoAccess Live", "goaccess-live.service",       True),
]


def host_metrics():
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "memory": psutil.virtual_memory()._asdict(),
        "disk": psutil.disk_usage("/")._asdict(),
        "loadavg": psutil.getloadavg(),
        "boot_time": psutil.boot_time(),
    }


def service_status(service: str):
    result = subprocess.run(
        ["systemctl", "is-active", service],
        capture_output=True,
        text=True,
        timeout=3
    )

    return {
        "service": service,
        "status": result.stdout.strip() or "unknown",
        "returncode": result.returncode
    }


def services_summary():
    results = []
    for display_name, unit, restartable in MONITORED_SERVICES:
        st = service_status(unit)
        results.append({
            "name": display_name,
            "unit": unit,
            "status": st["status"],
            "active": st["status"] == "active",
            "restartable": restartable,
        })
    return results


def restart_service(unit: str):
    # Only allow restarting known non-self services
    allowed = {u for _, u, ok in MONITORED_SERVICES if ok}
    if unit not in allowed:
        return {"status": "error", "message": f"Restart not permitted for {unit}"}

    result = subprocess.run(
        ["systemctl", "restart", unit],
        capture_output=True, text=True, timeout=15
    )
    return {
        "unit": unit,
        "status": "ok" if result.returncode == 0 else "error",
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
    }


def reload_nginx():
    result = subprocess.run(
        ["systemctl", "reload", "nginx.service"],
        capture_output=True, text=True, timeout=10
    )
    return {
        "status": "ok" if result.returncode == 0 else "error",
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def containers():
    try:
        result = subprocess.run(
            ["podman", "ps", "--all", "--format", "json"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return {"containers": [], "error": result.stderr.strip()}
        raw = json.loads(result.stdout or "[]")
        items = []
        for c in raw:
            items.append({
                "id": (c.get("Id") or "")[:12],
                "name": (c.get("Names") or [""])[0] if isinstance(c.get("Names"), list) else c.get("Names", ""),
                "image": c.get("Image", ""),
                "status": c.get("State", c.get("Status", "")),
                "running": c.get("State", "").lower() == "running",
                "created": c.get("CreatedAt", ""),
            })
        return {"containers": items}
    except Exception as exc:
        return {"containers": [], "error": str(exc)}


def container_logs(name: str, lines: int = 50):
    name = name.strip()
    result = subprocess.run(
        ["podman", "logs", "--tail", str(int(lines)), name],
        capture_output=True, text=True, timeout=5
    )
    return {
        "name": name,
        "lines": (result.stdout + result.stderr).splitlines()[-lines:],
        "returncode": result.returncode,
    }


def restart_container(name: str):
    name = name.strip()
    result = subprocess.run(
        ["podman", "restart", name],
        capture_output=True, text=True, timeout=30
    )
    return {
        "name": name,
        "status": "ok" if result.returncode == 0 else "error",
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
    }


def journal(units: str = "nginx,deathstar-api", lines: int = 100):
    cmd = ["journalctl", "--no-pager", "-n", str(lines)]

    for unit in [u.strip() for u in units.split(",") if u.strip()]:
        cmd.extend(["-u", unit])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=5
    )

    return {
        "units": units,
        "lines": result.stdout.splitlines(),
        "stderr": result.stderr.splitlines(),
        "returncode": result.returncode
    }


