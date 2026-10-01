# JKLU Profile Finder Architecture

## Product boundary

JKLU Profile Finder is a one-photo search interface backed by an authenticated, institution-scoped index of profiles that are synthetic or explicitly enrolled with documented consent. It is not a general-purpose face identification service. It does not search the public internet for a person's identity, scrape social networks, access private accounts, or infer identity from non-participating students.

The institution is fixed to JKLU in server-side configuration. The consumer submits no name, username, department, or search keywords. A photo is untrusted temporary input; the user receives possible matches with evidence and calibrated confidence, or a no-reliable-match response.

## System components

```text
Browser (Next.js App Router)
  | HTTPS, secure session, one image
  v
FastAPI API -- auth, validation, ownership, quotas, audit
  |                       |
  |                       +--> Redis (rate limits and short-lived job state)
  v
PostgreSQL (users, profiles, consent, searches, results, audit)
  ^
  | authorized index only
Worker (image normalization, matching, retention cleanup)
```

The web app handles preview, upload progress, processing status, evidence display, profile links, and deletion. The API owns validation and authorization; UI validation is only convenience. PostgreSQL is the source of truth and initial full-text/search index. Redis is not permanent storage. A worker handles image processing and cleanup; no object store is required for the initial local build because the upload can be processed in a bounded temporary directory and removed in a `finally` path. Production may use private encrypted object storage with lifecycle deletion.

## Trust boundaries and data flow

1. The user authenticates. Search is unavailable to anonymous callers.
2. The API checks account state, per-account/IP quotas, request size, actual file signature, decodability, dimensions, and supported format (JPEG, PNG, WEBP).
3. The processor decodes and re-encodes the image, strips metadata, and holds only the normalized temporary image required for the authorized matcher. The upload is deleted after processing and on failures.
4. Candidate generation is institution-filtered in the repository query and requires an active enrollment with valid consent. Revoked/expired records cannot participate.
5. Ranking uses a versioned configuration. The response includes only display-safe evidence, confidence band, and profile data whose visibility permits display. Scores are not proof of identity.
6. Search metadata and result references are retained only for the documented short retention period; the image itself is not persisted. Users can delete search history.
7. Audit events record sensitive actions without recording image bytes, credentials, tokens, or raw biometric signals.

## Matching and confidence

`CandidateMatcher` is an independent service boundary with candidate generation, feature calculation, ranking, and explanation methods. The initial development implementation must use synthetic/consented fixtures only. Production enrollment requires documented consent, a revocation path, deletion support, access restrictions, and privacy/security review. No arbitrary external profile lookup is permitted.

The configured ranking model is versioned and evaluated against authorized/synthetic holdout data. A confidence threshold for showing a result is a deployment configuration, not a UI guarantee. Results below that threshold return `NO_RELIABLE_MATCH`. The UI says “Possible match” and never says “this is definitely this person.” Explanations contain only permitted signals (for example, JKLU affiliation and consistent public profile details), not raw embeddings or sensitive internal data.

## Main data entities

- `users`: authentication identity, role, active status, timestamps.
- `profiles`: JKLU-scoped display and academic details, visibility, deletion state.
- `profile_sources`: canonical, validated profile URLs and source verification metadata.
- `enrolled_identity_records`: explicit consent state and reference to isolated encrypted matching material; no raw photo by default.
- `searches`: owner, lifecycle status, timestamps, expiry.
- `search_results`: ranked profile references, score, safe signals, model version.
- `audit_logs`: privacy-minimized security and admin events.

See [DATABASE.md](DATABASE.md) for constraints and retention and [API.md](API.md) for contracts.

## API and authorization model

All application routes are versioned under `/api/v1`. Authentication uses secure, HTTP-only, SameSite cookies with CSRF protection for state-changing requests. Passwords use Argon2id. Access sessions are short-lived; refresh credentials rotate and are revocable. Roles are `USER`, `ADMIN`, and `SUPER_ADMIN`. Search resources are owner-scoped; administrative operations require server-side role checks. No caller-supplied institution can broaden the fixed JKLU boundary.

The first deployable increment may use a local development auth adapter, but production must not ship with demo credentials, weak secrets, or disabled authorization. Search actions require authentication and enforce account and network limits.

## Ingestion

Adapters share a `discover/fetch/normalize/validate` contract. Initial data comes only from synthetic fixtures or an explicit admin import of authorized records. There are no brittle social scrapers. External adapters must use official/permitted APIs, obey terms and rate limits, validate URLs, and never fetch arbitrary user-supplied URLs server-side. Normalization, deduplication, validation, indexing, and quality reporting are separate pipeline stages.

## Deployment and operations

Local development runs web, API, PostgreSQL, Redis, and worker through Compose. PostgreSQL is not exposed publicly in production; service credentials are least-privilege and TLS is required in production. Secrets come from environment injection locally and a secret manager in production. Health/readiness checks, request IDs, structured redacted logs, metrics, encrypted backups, restore verification, dependency scanning, and CI gates are deployment requirements.

## Repository layout

```text
apps/
  web/                 Next.js TypeScript App Router
  api/                 FastAPI application
    app/{api,core,models,schemas,services,repositories,workers,security,ingestion,matching,search}/
    tests/
    alembic/
workers/               Worker entry points if separately packaged
database/              SQL/bootstrap and local fixtures
packages/              Shared types/configuration where useful
tests/                 Cross-service and end-to-end tests
docs/                  Supporting operational documentation
scripts/               Local development and maintenance helpers
docker-compose.yml
.env.example
README.md
```

## Delivery phases

1. Architecture, database, API, threat model, and repository shape.
2. Monorepo foundation, Compose services, environment configuration, and secure auth.
3. Profile schema, consent-aware synthetic/authorized ingestion, normalization, and indexing.
4. Independent matcher, ranking configuration, explanations, and evaluation fixtures.
5. Upload validation, temporary image processing, asynchronous lifecycle, and cleanup.
6. Consumer UI for one-photo upload, status, possible matches, and no-match.
7. Security hardening, authorization/abuse tests, and CI.
8. Deployment and operational documentation.

Each phase is incomplete until its focused tests pass. The product must not be represented as production-ready until deployment-specific consent, privacy, security, and compliance reviews are complete.