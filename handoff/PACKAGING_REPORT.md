# Packaging and validation report

Prepared November 3, 2026, in the authoring container, not on the owner's computer.

## Baseline and preservation

- Input archive: `Padala-NextJS-Python.zip`.
- Input SHA-256: `dd4d9f0cbbad10e1446d45f5077c05f15ae94f12db82979956dfd0facadc1cde`.
- **All 66 original files are preserved byte-for-byte**, including frontend/backend source, migrations, API documentation, launchers, tests, sample receipts and historical previews.
- New handoff documents and two standard-library diagnostic scripts were added. No application behavior or dependency version was changed in this packaging task.

## Checks executed for this handoff

| Check | Result |
|---|---|
| Original ZIP extraction and content preservation | All original file contents match |
| Backend regression, `python -m pytest -q --disable-warnings` | **59 passed in 12.71 seconds** in the saved run |
| Python environment | Python 3.13.5; installed package versions matched the supplied backend/test pins |
| API export structure | Valid JSON, 28 paths, 30 operations |
| New preflight syntax and execution | Passed in this container; Node 22.16.0 and npm 10.9.2 found |
| Checksum verification utility | Valid-file, modified-file, missing-file and unsafe-path cases behaved as expected |
| Source packaging exclusions | No real .env, database, private uploads, dependencies or build/cache directories included |

The actual backend command output is preserved in `BACKEND_REGRESSION_OUTPUT.txt`. This was a backend regression on the installed container environment, not a fresh installation on Windows or macOS. The new scripts were not executed on those operating systems.

## Still not run or established here

Actual npm dependency resolution/lockfile creation, dependency-aware TypeScript checking, Next.js development/production execution, the included real-Next Playwright tests, a new browser UI run, physical-phone installation, Docker builds, live Azure extraction, live SMTP delivery, bank verification, subscriptions, security/penetration/accessibility/privacy audits, or production approval.

Historical screenshots are preserved from the earlier disclosed browser harness. They were not newly generated from a real Next.js build in this packaging task. The Codex CLI is not installed in this authoring container; the instructions are for use in the owner's local Codex environment.

## Transfer integrity

`FILE_MANIFEST.json` records each included file's size and SHA-256 except the manifest itself. Run `python3 scripts/verify_bundle.py` immediately after extraction (Windows: `py -3 scripts/verify_bundle.py`). All listed files should match before editing. The manifest is a change-detection aid, not a digital publisher signature.

Expected Codex modifications will change checksums. Keep the original downloaded ZIP separately as a restore point; do not overwrite a working project or real data merely to make the old manifest match.
