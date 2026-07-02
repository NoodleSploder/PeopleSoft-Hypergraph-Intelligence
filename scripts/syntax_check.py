#!/usr/bin/env python3
"""Syntax-check all Python source files in the project.

Runs py_compile on every .py file outside __pycache__ and .venv.
Exits 0 if all files compile cleanly; exits 1 and prints errors otherwise.

Usage:
    python3 scripts/syntax_check.py
    python3 scripts/syntax_check.py --quiet          # suppress per-file OK lines
    python3 scripts/syntax_check.py --exit-zero      # always exit 0 (for pre-commit)
"""

from __future__ import annotations

import argparse
import py_compile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# Directories to skip (relative to ROOT)
_SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules"}


def collect_files() -> list[Path]:
    files = []
    for path in sorted(ROOT.rglob("*.py")):
        # Skip excluded directories
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def check_files(files: list[Path], quiet: bool = False) -> list[tuple[Path, str]]:
    errors: list[tuple[Path, str]] = []
    for f in files:
        try:
            py_compile.compile(str(f), doraise=True)
            if not quiet:
                rel = f.relative_to(ROOT)
                print(f"  OK  {rel}")
        except py_compile.PyCompileError as exc:
            rel = f.relative_to(ROOT)
            errors.append((rel, str(exc)))
            print(f"  ERR {rel}")
            print(f"      {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    parser.add_argument(
        "--exit-zero",
        action="store_true",
        help="Exit 0 even if errors found (useful for pre-commit hooks)",
    )
    args = parser.parse_args()

    files = collect_files()
    print(f"Checking {len(files)} Python files…")
    errors = check_files(files, quiet=args.quiet)

    if errors:
        print(f"\n{len(errors)} SYNTAX ERROR(S) found:")
        for path, msg in errors:
            print(f"  {path}: {msg}")
        return 0 if args.exit_zero else 1

    print(f"\nAll {len(files)} files OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
