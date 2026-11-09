#!/usr/bin/env python3
"""Read-only Padala prerequisite check. No installs, network requests, or secret output."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def command_version(name: str, args: list[str]) -> str | None:
    executable = shutil.which(name)
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, *args],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
            shell=os.name == 'nt' and executable.lower().endswith(('.cmd', '.bat')),
        )
        if result.returncode != 0:
            return '(found, but version command failed)'
        return (result.stdout.strip() or '(no version output)').splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        return '(found, but version check could not complete)'


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(('127.0.0.1', port))
        except OSError:
            return False
    return True


def main() -> int:
    failures = 0
    print('Padala local preflight — no files changed; no external services contacted.\n')
    print('Project:', ROOT)
    print('Python:', sys.version.split()[0])
    if sys.version_info < (3, 11):
        print('FAIL: Python 3.11 or newer is required.')
        failures += 1
    else:
        print('OK: Python meets the declared minimum.')

    for name, args, required in [
        ('node', ['--version'], True),
        ('npm', ['--version'], True),
        ('git', ['--version'], False),
        ('codex', ['--version'], False),
    ]:
        version = command_version(name, args)
        print(f'{name}: {version or "not found on PATH"}')
        if required and (version is None or version.startswith('(')):
            failures += 1
        if name == 'node' and version:
            match = re.match(r'^v?(\d+)', version)
            if match and int(match.group(1)) < 22:
                print('FAIL: The project requires Node 22 or newer.')
                failures += 1

    print('\nThe Codex CLI is optional when using an existing desktop/editor installation.')
    print('\nRequired source files:')
    for relative in [
        'AGENTS.md', 'REQUIREMENTS.md', 'CODEX_START_PROMPT.md', 'run_local.py',
        'frontend/package.json', 'backend/requirements.txt',
        'backend/requirements-dev.txt', 'backend/.env.example',
        'frontend/.env.local.example', 'docs/openapi.json',
    ]:
        present = (ROOT / relative).is_file()
        print(f'  {"OK" if present else "MISSING"}: {relative}')
        failures += int(not present)

    manifest = ROOT / 'frontend/package.json'
    if manifest.is_file():
        try:
            spec = json.loads(manifest.read_text(encoding='utf-8'))
            print('\nDeclared frontend dependencies (not registry-validated):')
            for name, declared in spec.get('dependencies', {}).items():
                print(f'  {name}: {declared}')
        except (OSError, ValueError):
            print('FAIL: Cannot read frontend/package.json as JSON.')
            failures += 1

    print('\nLocal setup state (contents and secrets are not displayed):')
    venv_python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    for label, path in [
        ('Python virtual environment', venv_python),
        ('Frontend dependencies', ROOT / 'frontend/node_modules/next/package.json'),
        ('Frontend lockfile', ROOT / 'frontend/package-lock.json'),
        ('Backend .env', ROOT / 'backend/.env'),
        ('Frontend .env.local', ROOT / 'frontend/.env.local'),
    ]:
        print(f'  {label}: {"present" if path.exists() else "not created yet"}')

    print('\nDefault local ports:')
    for port in (3000, 8000):
        print(f'  {port}: {"available" if port_available(port) else "in use or unavailable"}')
    print('Busy ports may mean Padala is already running; do not stop unrelated processes.')
    print('\nPreflight does not test dependency installation, the application, APIs, or credentials.')
    if failures:
        print(f'Result: {failures} prerequisite issue(s). See handoff/LOCAL_SETUP.md.')
        return 1
    print('Result: core local prerequisites found. Continue with CODEX_START_PROMPT.md.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
