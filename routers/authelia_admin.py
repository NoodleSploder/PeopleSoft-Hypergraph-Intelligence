import sqlite3
import subprocess
from pathlib import Path
from typing import List, Dict, Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.hash import argon2

router = APIRouter(prefix="/authelia", tags=["Authelia Admin"])

USERS_FILE = Path("/opt/authelia/config/users_database.yml")
COMPOSE_DIR = Path("/opt/authelia")
AUTHELIA_DB = Path("/opt/authelia/config/db.sqlite3")


def _sqlite_query(sql: str, params: tuple = (), write: bool = False) -> list:
    """Execute a SQLite query against the Authelia database."""
    if not AUTHELIA_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(AUTHELIA_DB))
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, params)
        if write:
            conn.commit()
            conn.close()
            return []
        rows = [dict(row) for row in cur.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


class UserCreate(BaseModel):
    username: str
    password: str
    displayname: str | None = None
    email: str | None = None
    groups: List[str] = []


class UserUpdate(BaseModel):
    displayname: str | None = None
    email: str | None = None
    groups: List[str] | None = None
    disabled: bool | None = None


class PasswordReset(BaseModel):
    password: str


def load_db() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {"users": {}}

    with USERS_FILE.open("r") as f:
        data = yaml.safe_load(f) or {}

    if "users" not in data:
        data["users"] = {}

    return data


def save_db(data: Dict[str, Any]) -> None:
    backup = USERS_FILE.with_suffix(".yml.bak")
    if USERS_FILE.exists():
        backup.write_text(USERS_FILE.read_text())

    with USERS_FILE.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False)

    validate_authelia()
    restart_authelia()


def validate_authelia() -> None:
    cmd = [
        "podman", "run", "--rm",
        "-v", "/opt/authelia/config:/config",
        "docker.io/authelia/authelia:latest",
        "authelia", "config", "validate",
        "--config", "/config/configuration.yml",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Authelia config validation failed:\n{result.stdout}\n{result.stderr}",
        )


def restart_authelia() -> None:
    result = subprocess.run(
        ["podman", "compose", "restart"],
        cwd=str(COMPOSE_DIR),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Authelia restart failed:\n{result.stdout}\n{result.stderr}",
        )


@router.get("/users")
def list_users():
    data = load_db()
    users = []

    for username, info in data["users"].items():
        users.append({
            "username": username,
            "displayname": info.get("displayname"),
            "email": info.get("email"),
            "groups": info.get("groups", []),
            "disabled": info.get("disabled", False),
        })

    return users


@router.post("/users")
def create_user(req: UserCreate):
    data = load_db()

    if req.username in data["users"]:
        raise HTTPException(status_code=409, detail="User already exists")

    data["users"][req.username] = {
        "disabled": False,
        "displayname": req.displayname or req.username,
        "password": argon2.hash(req.password),
        "email": req.email or f"{req.username}@deathstar.chickenkiller.com",
        "groups": req.groups,
    }

    save_db(data)
    return {"status": "created", "username": req.username}


@router.patch("/users/{username}")
def update_user(username: str, req: UserUpdate):
    data = load_db()

    if username not in data["users"]:
        raise HTTPException(status_code=404, detail="User not found")

    user = data["users"][username]

    if req.displayname is not None:
        user["displayname"] = req.displayname

    if req.email is not None:
        user["email"] = req.email

    if req.groups is not None:
        user["groups"] = req.groups

    if req.disabled is not None:
        user["disabled"] = req.disabled

    save_db(data)
    return {"status": "updated", "username": username}


@router.post("/users/{username}/reset-password")
def reset_password(username: str, req: PasswordReset):
    data = load_db()

    if username not in data["users"]:
        raise HTTPException(status_code=404, detail="User not found")

    data["users"][username]["password"] = argon2.hash(req.password)

    save_db(data)
    return {"status": "password_reset", "username": username}


@router.delete("/users/{username}")
def delete_user(username: str):
    data = load_db()

    if username not in data["users"]:
        raise HTTPException(status_code=404, detail="User not found")

    del data["users"][username]

    save_db(data)
    return {"status": "deleted", "username": username}


@router.get("/groups")
def list_groups():
    data = load_db()
    groups = set()

    for info in data["users"].values():
        for group in info.get("groups", []):
            groups.add(group)

    return sorted(groups)


@router.get("/mfa/status")
def mfa_status():
    """Return MFA registration status for all users.

    Reads from the Authelia SQLite database: totp_configurations, webauthn_credentials,
    user_preferences, and recent authentication_logs.
    """
    totp_rows = _sqlite_query(
        "SELECT username, created_at, last_used_at, algorithm, digits, period FROM totp_configurations"
    )
    webauthn_rows = _sqlite_query(
        "SELECT username, description, created_at, last_used_at, attachment FROM webauthn_credentials"
    )
    prefs_rows = _sqlite_query("SELECT username, second_factor_method FROM user_preferences")
    last_auth_rows = _sqlite_query("""
        SELECT username, MAX(time) AS last_seen, SUM(CASE WHEN successful THEN 1 ELSE 0 END) AS successes,
               SUM(CASE WHEN NOT successful THEN 1 ELSE 0 END) AS failures,
               SUM(CASE WHEN auth_type='2FA' AND successful THEN 1 ELSE 0 END) AS mfa_auths
          FROM authentication_logs
         GROUP BY username
    """)

    totp_by_user = {r["username"]: r for r in totp_rows}
    webauthn_by_user: dict = {}
    for r in webauthn_rows:
        webauthn_by_user.setdefault(r["username"], []).append(r)
    prefs_by_user = {r["username"]: r["second_factor_method"] for r in prefs_rows}
    auth_by_user = {r["username"]: r for r in last_auth_rows}

    users_data = load_db()
    result = []
    for username in sorted(users_data["users"]):
        auth = auth_by_user.get(username, {})
        result.append({
            "username": username,
            "totp_configured": username in totp_by_user,
            "totp_last_used": (totp_by_user[username].get("last_used_at") if username in totp_by_user else None),
            "totp_algorithm": (totp_by_user[username].get("algorithm") if username in totp_by_user else None),
            "webauthn_count": len(webauthn_by_user.get(username, [])),
            "webauthn_devices": webauthn_by_user.get(username, []),
            "preferred_method": prefs_by_user.get(username),
            "last_seen": auth.get("last_seen"),
            "total_logins": auth.get("successes", 0),
            "failed_logins": auth.get("failures", 0),
            "mfa_logins": auth.get("mfa_auths", 0),
        })
    return result


@router.get("/mfa/status/{username}")
def mfa_status_user(username: str):
    """Return MFA registration detail for a single user."""
    users_data = load_db()
    if username not in users_data["users"]:
        raise HTTPException(status_code=404, detail="User not found")

    totp_rows = _sqlite_query(
        "SELECT * FROM totp_configurations WHERE username = ?", (username,)
    )
    webauthn_rows = _sqlite_query(
        "SELECT id, description, created_at, last_used_at, attachment, transport, sign_count FROM webauthn_credentials WHERE username = ?",
        (username,)
    )
    auth_rows = _sqlite_query(
        "SELECT time, successful, auth_type, remote_ip, request_uri FROM authentication_logs WHERE username = ? ORDER BY time DESC LIMIT 20",
        (username,)
    )
    prefs = _sqlite_query("SELECT second_factor_method FROM user_preferences WHERE username = ?", (username,))

    return {
        "username": username,
        "totp": totp_rows[0] if totp_rows else None,
        "webauthn_devices": webauthn_rows,
        "preferred_method": prefs[0]["second_factor_method"] if prefs else None,
        "recent_auth_log": auth_rows,
    }


@router.delete("/mfa/{username}/totp")
def revoke_totp(username: str):
    """Revoke a user's TOTP configuration. Forces them to re-register on next 2FA login."""
    rows = _sqlite_query("SELECT id FROM totp_configurations WHERE username = ?", (username,))
    if not rows:
        raise HTTPException(status_code=404, detail="No TOTP configuration found for user")
    _sqlite_query("DELETE FROM totp_configurations WHERE username = ?", (username,), write=True)
    _sqlite_query("DELETE FROM totp_history WHERE username = ?", (username,), write=True)
    return {"status": "revoked", "username": username, "method": "totp"}


@router.delete("/mfa/{username}/webauthn")
def revoke_webauthn(username: str, device_id: int | None = None):
    """Revoke WebAuthn credentials. Pass device_id to remove one device; omit to remove all."""
    if device_id is not None:
        rows = _sqlite_query("SELECT id FROM webauthn_credentials WHERE username = ? AND id = ?", (username, device_id))
        if not rows:
            raise HTTPException(status_code=404, detail="WebAuthn device not found")
        _sqlite_query("DELETE FROM webauthn_credentials WHERE username = ? AND id = ?", (username, device_id), write=True)
        return {"status": "revoked", "username": username, "method": "webauthn", "device_id": device_id}
    else:
        _sqlite_query("DELETE FROM webauthn_credentials WHERE username = ?", (username,), write=True)
        _sqlite_query("DELETE FROM webauthn_users WHERE username = ?", (username,), write=True)
        return {"status": "revoked", "username": username, "method": "webauthn", "device_id": "all"}


@router.delete("/mfa/{username}")
def revoke_all_mfa(username: str):
    """Revoke all MFA (TOTP + WebAuthn) for a user. Forces 1FA-only access."""
    users_data = load_db()
    if username not in users_data["users"]:
        raise HTTPException(status_code=404, detail="User not found")
    _sqlite_query("DELETE FROM totp_configurations WHERE username = ?", (username,), write=True)
    _sqlite_query("DELETE FROM totp_history WHERE username = ?", (username,), write=True)
    _sqlite_query("DELETE FROM webauthn_credentials WHERE username = ?", (username,), write=True)
    _sqlite_query("DELETE FROM webauthn_users WHERE username = ?", (username,), write=True)
    _sqlite_query("DELETE FROM user_preferences WHERE username = ?", (username,), write=True)
    return {"status": "all_mfa_revoked", "username": username}


@router.get("/logs")
def auth_logs(limit: int = 100, username: str = "", failed_only: bool = False):
    """Return recent authentication log entries from the Authelia database."""
    params: list = []
    where_parts = []
    if username:
        where_parts.append("username = ?")
        params.append(username)
    if failed_only:
        where_parts.append("successful = 0")
    where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    limit = max(1, min(int(limit), 1000))
    rows = _sqlite_query(
        f"SELECT time, successful, banned, username, auth_type, remote_ip, request_uri FROM authentication_logs {where} ORDER BY time DESC LIMIT {limit}",
        tuple(params)
    )
    return {"logs": rows, "count": len(rows)}
