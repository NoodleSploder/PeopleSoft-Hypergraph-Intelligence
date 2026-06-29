import subprocess
import psutil


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


