from pathlib import Path
import yaml
from fastapi import APIRouter
from pydantic import BaseModel
from passlib.hash import argon2
from datetime import datetime, timezone
import json

from routers import authelia_admin
from connectors import psdb

router = APIRouter(prefix="/api/identity", tags=["Identity"])

ROLE_MAP_FILE    = Path("/opt/deathstar-api/config/role_mapping.yml")
AUDIT_FILE       = Path("/opt/deathstar-api/logs/identity_audit.jsonl")

class ProvisionRequest(BaseModel):
    password: str


def load_role_map():
    if not ROLE_MAP_FILE.exists():
        return {}
    return yaml.safe_load(ROLE_MAP_FILE.read_text()) or {}


def audit(action: str, target: str, detail: dict):
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "target": target,
        "detail": detail,
    }

    with AUDIT_FILE.open("a") as f:
        f.write(json.dumps(event) + "\n")


@router.get("/compare/{oprid}")
def compare_identity(oprid: str, env: str = "HCM"):
    oprid = oprid.upper()

    ps_user = psdb.oprid(oprid, env)
    roles = psdb.oprid_roles(oprid, env)

    role_map = load_role_map()
    mapped_groups = set()

    for r in roles:
        for g in role_map.get(r["rolename"], []):
            mapped_groups.add(g)

    authelia = authelia_admin.load_db()
    authelia_user = authelia["users"].get(oprid)

    return {
        "oprid": oprid,
        "peoplesoft": ps_user,
        "roles": roles,
        "mapped_groups": sorted(mapped_groups),
        "authelia_exists": authelia_user is not None,
        "authelia": {
            "email": authelia_user.get("email"),
            "groups": authelia_user.get("groups", []),
            "disabled": authelia_user.get("disabled", False),
        } if authelia_user else None
    }


@router.post("/sync/{oprid}")
def sync_identity(oprid: str, env: str = "HCM"):
    comparison = compare_identity(oprid, env)
    oprid = comparison["oprid"]

    if not comparison["peoplesoft"]:
        return {"status": "error", "message": "PeopleSoft OPRID not found"}

    if not comparison["authelia_exists"]:
        return {"status": "error", "message": "Authelia user does not exist"}

    data = authelia_admin.load_db()
    user = data["users"][oprid]

    old_groups = set(user.get("groups", []))
    new_groups = set(comparison["mapped_groups"])

    old_disabled = user.get("disabled", False)
    new_disabled = comparison["peoplesoft"].get("acctlock") != 0

    old_displayname = user.get("displayname")
    new_displayname = comparison["peoplesoft"].get("oprdefndesc") or oprid

    user["displayname"] = new_displayname
    user["groups"] = sorted(new_groups)
    user["disabled"] = new_disabled

    authelia_admin.save_db(data)


    result = {
        "status": "synced",
        "oprid": oprid,
        "groups": {
            "added": sorted(new_groups - old_groups),
            "removed": sorted(old_groups - new_groups),
            "unchanged": sorted(old_groups & new_groups),
            "current": sorted(new_groups),
        },
        "disabled": {
            "old": old_disabled,
            "new": new_disabled,
            "changed": old_disabled != new_disabled,
        },
        "displayname": {
            "old": old_displayname,
            "new": new_displayname,
            "changed": old_displayname != new_displayname,
        }
    }

    audit("sync_identity", oprid, result)
    return result


@router.post("/provision/{oprid}")
def provision_identity(oprid: str, req: ProvisionRequest, env: str = "HCM"):
    comparison = compare_identity(oprid, env)
    oprid = comparison["oprid"]

    if not comparison["peoplesoft"]:
        return {"status": "error", "message": "PeopleSoft OPRID not found"}

    if comparison["authelia_exists"]:
        return {"status": "error", "message": "Authelia user already exists"}

    data = authelia_admin.load_db()

    data["users"][oprid] = {
        "disabled": comparison["peoplesoft"].get("acctlock") != 0,
        "displayname": comparison["peoplesoft"].get("oprdefndesc") or oprid,
        "password": argon2.hash(req.password),
        "email": f"{oprid.lower()}@deathstar.chickenkiller.com",
        "groups": comparison["mapped_groups"],
    }

    authelia_admin.save_db(data)

    result = {
        "status": "provisioned",
        "oprid": oprid,
        "groups": comparison["mapped_groups"],
        "disabled": data["users"][oprid]["disabled"],
    }

    audit("provision_identity", oprid, result)
    return result

@router.get("/status")
def identity_status(env: str = "HCM"):
    data = authelia_admin.load_db()
    results = []

    for username, user in data["users"].items():
        try:
            c = compare_identity(username, env)

            ps_exists = c["peoplesoft"] is not None
            expected_groups = set(c["mapped_groups"])
            actual_groups = set(user.get("groups", []))

            in_sync = (
                ps_exists
                and expected_groups == actual_groups
                and user.get("disabled", False) == (c["peoplesoft"].get("acctlock") != 0)
            )

            results.append({
                "username": username,
                "peoplesoft_exists": ps_exists,
                "authelia_exists": True,
                "in_sync": in_sync,
                "expected_groups": sorted(expected_groups),
                "actual_groups": sorted(actual_groups),
                "missing_groups": sorted(expected_groups - actual_groups),
                "extra_groups": sorted(actual_groups - expected_groups),
            })
        except Exception as exc:
            results.append({
                "username": username,
                "error": str(exc),
                "in_sync": False,
            })

    return results


@router.post("/sync-all")
def sync_all_identities(env: str = "HCM"):
    data = authelia_admin.load_db()
    results = []

    for username in list(data["users"].keys()):
        try:
            result = sync_identity(username, env)
            results.append({
                "username": username,
                "result": result
            })
        except Exception as exc:
            results.append({
                "username": username,
                "status": "error",
                "error": str(exc)
            })

    result = {
        "status": "complete",
        "count": len(results),
        "results": results
    }

    audit("sync_all_identities", "all", result)
    return result


@router.get("/audit")
def identity_audit(limit: int = 100):
    if not AUDIT_FILE.exists():
        return []

    lines = AUDIT_FILE.read_text().splitlines()[-limit:]
    return [json.loads(line) for line in lines]



