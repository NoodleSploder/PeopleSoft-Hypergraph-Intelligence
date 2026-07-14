"""
Single source of truth for the application's on-disk root.

Every module that reads config.json, or writes to data/ or logs/, used to
hardcode the absolute path "/opt/deathstar-api" directly — correct for the
one production host this app has always run on, but it meant the app could
never be imported (let alone run) anywhere else: a fresh checkout in CI, a
developer's laptop, or a future second deployment all break identically,
since nothing computes the root — it's just repeated as a literal in 19
files.

APP_ROOT resolves the real repository root from this file's own location
(connectors/paths.py -> parent is connectors/, parent.parent is the repo
root) by default, so production behavior is unchanged — this file still
lives at /opt/deathstar-api/connectors/paths.py in production, so
APP_ROOT still resolves to /opt/deathstar-api. DEATHSTAR_HOME can override
it explicitly (e.g. a CI job pointing it at the checkout directory,
instead of needing to `sudo mkdir /opt/deathstar-api` and copy a fixture
into a path unrelated to where the code actually is).
"""

import os
from pathlib import Path

APP_ROOT = Path(os.environ.get("DEATHSTAR_HOME", Path(__file__).resolve().parent.parent))
