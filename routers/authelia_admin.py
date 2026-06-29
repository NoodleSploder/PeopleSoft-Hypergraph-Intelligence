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


