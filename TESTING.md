# Testing Guide

## API

The API test suite covers password hashing, signed-token parsing, image re-encoding/limits, consent-aware candidate filtering, ranking explanations, and an HTTP registration/search/logout flow using in-memory SQLite and a fake Redis service.

```powershell
apps\api\.venv311\Scripts\python.exe -m pytest apps\api\tests -q
```

The `.venv311` name is specific to the local validation environment and is ignored by Git. In a clean Python 3.11/3.12 environment, install `apps/api/requirements.txt` and run `python -m pytest apps/api/tests -q`.

## Web

```powershell
npm run lint --prefix apps/web
npm run build --prefix apps/web
```

The upload, sign-in panel, remove-photo action, and desktop/mobile overflow were manually exercised in the browser. No committed Playwright end-to-end suite exists yet.

## Integration and security gaps

The HTTP integration test uses SQLite and a fake Redis implementation; it does not validate PostgreSQL, Redis behavior under failure/load, Docker networking, migrations, or browser-to-live-API authentication. The Docker daemon was unavailable during this run. Add PostgreSQL/Redis-backed CI, migration-from-empty tests, owner/role authorization tests, request-size/chunked-upload tests, rate-limit bypass tests, CSP/CORS checks, and Playwright upload/search/no-match flows before release.

The tests do not demonstrate matching accuracy. Evaluation must use synthetic or explicitly consented identities and report precision, false positives, no-match accuracy, and calibration before production use.