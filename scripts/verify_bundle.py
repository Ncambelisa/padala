#!/usr/bin/env python3
"""Verify the transferred source files against FILE_MANIFEST.json using only stdlib.

Run before editing. Local edits legitimately differ from the initial package.
A checksum manifest detects changes; it is not a publisher signature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def verify(root: Path) -> int:
    root = root.resolve()
    try:
        data = json.loads((root / 'FILE_MANIFEST.json').read_text(encoding='utf-8'))
        records = data['files']
        if data.get('algorithm') != 'sha256' or not isinstance(records, list):
            raise ValueError('Invalid manifest format.')
        seen: set[str] = set()
        invalid: list[str] = []
        for record in records:
            relative = record['path']
            if not isinstance(relative, str):
                raise ValueError('Non-string path.')
            logical = PurePosixPath(relative)
            if not relative or logical.is_absolute() or '..' in logical.parts or '\\' in relative:
                raise ValueError('Unsafe manifest path.')
            if relative in seen:
                raise ValueError('Duplicate manifest path.')
            seen.add(relative)
            path = root.joinpath(*logical.parts).resolve()
            if not path.is_relative_to(root):
                raise ValueError('Manifest path escapes the project root.')
            if not path.is_file():
                invalid.append(f'MISSING {relative}')
            elif path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
                invalid.append(f'CHANGED {relative}')
        if invalid:
            print('\n'.join(invalid))
            print(f'FAIL: {len(invalid)} of {len(records)} listed files differ or are missing.')
            return 1
        print(f'PASS: all {len(records)} listed files match their size and SHA-256 checksum.')
        print('Extra local files are ignored. The manifest excludes itself and is not a signature.')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Cannot verify this bundle: {error}', file=sys.stderr)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1],
                        help='Extracted project root; defaults to the parent of scripts/.')
    args = parser.parse_args()
    return verify(args.root)


if __name__ == '__main__':
    raise SystemExit(main())
