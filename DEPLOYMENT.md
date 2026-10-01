# Deployment Guide

## Local Compose

Prerequisites: Docker Desktop with its Linux container engine running, Docker Compose v2, and an available port 3000 and 8000.

1. Copy `.env.example` to `.env`.
2. Replace `JWT_SECRET` with a randomly generated value of at least 32 characters. Keep local database and Redis passwords local-only.
3. Run `docker compose up --build` from the repository root.
4. Open `http://localhost:3000`; check `http://localhost:8000/health` and `/ready`.

The API creates tables automatically only in development mode. This is a bootstrap convenience, not a migration strategy. Alembic configuration and a reviewed initial migration must be added before production deployment. The `web` and `api` services publish local development ports; production networking must not expose PostgreSQL or Redis publicly.

## Production gate

Do not deploy this snapshot as a production identity service. Before production, complete database migrations, email verification, refresh-token rotation, account/profile deletion, consent enrollment/revocation workflow, admin RBAC routes, authorized index ingestion, matching evaluation, search persistence/retention, request-body limits, monitoring, and security/privacy review.

Use a non-root minimal container, TLS termination, secure cookies, strict CSP, private database/Redis networking, least-privilege credentials, a secrets manager, encrypted backups with tested restore, dependency/image scanning, and health/readiness probes. Set `APP_ENV=production`, `COOKIE_SECURE=true`, a unique random `JWT_SECRET`, and production-specific database/Redis URLs. Never use the sample credentials.

## Current operational limitations

The local environment used for this implementation had Docker installed but its daemon was stopped, so `docker compose config` passed while image builds and `docker compose up` could not be verified. No worker, object store, email provider, metrics exporter, or production migration pipeline is included yet.