# JKLU Profile Finder

An authenticated JKLU profile discovery application designed around a single-photo consumer flow. Matching is restricted to synthetic or explicitly consented profile records; this project does not identify arbitrary students, search the public internet for identities, scrape social networks, or access private accounts.

## Current status

Phase 0 architecture and threat model are documented. Foundation work is in progress. The API currently provides registration, login, logout with access-token revocation, current-user lookup, health checks, Redis rate limiting, hashed audit events, and strict upload validation. Search intentionally fails closed until an authorized profile index and matching pipeline are configured; it does not return fabricated matches.

## Architecture

- `apps/web`: Next.js App Router frontend.
- `apps/api`: FastAPI API and independent matching services.
- PostgreSQL: application records.
- Redis: short-lived rate-limit counters.

Read [ARCHITECTURE.md](ARCHITECTURE.md), [DATABASE.md](DATABASE.md), [API.md](API.md), and [SECURITY.md](SECURITY.md) before extending the matching/indexing behavior.

## Local development

1. Copy `.env.example` to `.env` and replace `JWT_SECRET` with a random value of at least 32 characters.
2. Start services with `docker compose up --build`.
3. Open `http://localhost:3000`; API health is at `http://localhost:8000/health`.

Do not use the sample database or Redis passwords outside local development. Production requires a secrets manager, TLS, private service networking, database migrations, email verification, refresh-token rotation, and a privacy/security review.

## Tests

API tests are under `apps/api/tests`. Run them in the API environment with `pytest`. Frontend checks use `npm run lint --prefix apps/web` and `npm run build --prefix apps/web`.

## Limitations

There is no authorized production identity index, profile ingestion adapter, background worker, production session refresh or email-verification flow, account-deletion workflow, or image-to-evidence signal extractor yet. The ranking service is an independently tested metadata ranker, not a calibrated identity model. No arbitrary-person face recognition or social scraping is implemented. Uploaded images are validated and re-encoded in memory; until the matching service is enabled, the API returns a service-unavailable response and does not retain the image.