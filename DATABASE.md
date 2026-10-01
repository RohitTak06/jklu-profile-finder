# Database Design

PostgreSQL is the source of truth. Use SQLAlchemy 2.x models, Alembic migrations, UUID primary keys, UTC timestamps, foreign keys, and explicit indexes. Institution scope is a server-controlled JKLU identifier; ordinary users cannot select another institution.

## Tables

### `users`

`id UUID PK`, `email VARCHAR(320) UNIQUE NOT NULL` (normalized to lowercase by the API), `password_hash TEXT`, `auth_provider TEXT`, `role` constrained to `USER`, `ADMIN`, or `SUPER_ADMIN`, `is_active BOOL`, `email_verified_at TIMESTAMPTZ NULL`, `created_at`, `updated_at`, `last_login_at NULL`, `deleted_at NULL`.

Passwords are Argon2id hashes. Never store plaintext passwords, access tokens, or refresh tokens. Session/refresh token records, if persisted, store only token hashes, family/rotation metadata, expiry, and revocation time.

### `institutions`

`id UUID PK`, `code TEXT UNIQUE NOT NULL` (fixed application code `JKLU`), `display_name TEXT NOT NULL`, `created_at`. Application configuration pins search to this row.

### `profiles`

`id UUID PK`, `institution_id UUID FK NOT NULL`, `display_name TEXT NOT NULL`, `department TEXT NULL`, `program TEXT NULL`, `academic_year SMALLINT NULL`, `bio TEXT NULL`, `profile_image_url TEXT NULL`, `visibility ENUM(PRIVATE, ENROLLED, PUBLIC)`, `is_active BOOL`, `created_at`, `updated_at`, `deleted_at NULL`.

Index `(institution_id, is_active)` and full-text search fields for permitted profile discovery. Profile visibility applies to returned profile fields and links; private profiles are never returned.

### `profile_sources`

`id UUID PK`, `profile_id UUID FK NOT NULL`, `source_type ENUM(LINKEDIN, INSTAGRAM, GITHUB, PORTFOLIO, JKLU, OTHER)`, `source_url TEXT NOT NULL`, `source_identifier TEXT NULL`, `verification_status ENUM(UNVERIFIED, VERIFIED, INVALID, REVOKED)`, `retrieved_at TIMESTAMPTZ NULL`, `last_verified_at TIMESTAMPTZ NULL`, `created_at`, `updated_at`.

Canonicalize and validate URLs at ingestion. Do not fetch these URLs automatically from search requests. Index `profile_id`, `(source_type, verification_status)`.

### `enrolled_identity_records`

`id UUID PK`, `profile_id UUID FK NOT NULL`, `identity_reference TEXT UNIQUE NOT NULL`, `consent_status` constrained to `PENDING`, `ACTIVE`, `REVOKED`, or `EXPIRED`, `consent_timestamp TIMESTAMPTZ NULL`, `consent_version TEXT NULL`, `revoked_at TIMESTAMPTZ NULL`, `created_at`, `updated_at`.

The table stores references and consent state, not raw photographs or embeddings. Any approved matching artifact lives in a separate restricted/encrypted store keyed by `identity_reference`, with retention, deletion, access logging, and key management defined before production use. Active matching requires active consent and an active profile. Revocation must atomically disable matching and enqueue artifact deletion.

### `searches`

`id UUID PK`, `user_id UUID FK NOT NULL`, `status ENUM(QUEUED, PROCESSING, COMPLETED, FAILED, DELETED)`, `created_at`, `started_at NULL`, `completed_at NULL`, `expires_at TIMESTAMPTZ NOT NULL`, `deleted_at NULL`, `request_id UUID NOT NULL`.

No uploaded-image bytes, embedding, or original filename are stored in this table. Index `(user_id, created_at DESC)` and `(status, expires_at)`.

### `search_results`

`id UUID PK`, `search_id UUID FK NOT NULL ON DELETE CASCADE`, `profile_id UUID FK NOT NULL`, `rank SMALLINT NOT NULL`, `ranking_score REAL NOT NULL CHECK (ranking_score BETWEEN 0 AND 1)`, `confidence_band` constrained to `LOW`, `MEDIUM`, or `HIGH`, `matching_signals JSON NOT NULL`, `model_version TEXT NOT NULL`, `created_at`.

Unique `(search_id, rank)` and `(search_id, profile_id)`. Only display-safe signals are persisted; never persist raw biometric vectors here. Search owner authorization is checked through `searches.user_id` on every read/delete.

### `audit_logs`

`id UUID PK`, `actor_id UUID NULL`, `action TEXT NOT NULL`, `resource_type TEXT NOT NULL`, `resource_id UUID NULL`, `ip_hash TEXT NULL`, `user_agent_hash TEXT NULL`, `metadata JSON NOT NULL DEFAULT '{}'`, `created_at`.

The weighted `ranking_score` is experimental and is not a calibrated probability of identity. Only a coarse confidence band and safe evidence may be shown; the current consumer API exposes no numeric score.

Never log passwords, tokens, image data, raw biometric features, or unnecessary PII. Restrict read access and apply a documented retention schedule.

## Integrity and deletion

- Foreign keys prevent orphaned profiles, sources, enrollments, results, and user-owned searches.
- Search-result queries always join through the owning search and enforce the authenticated user ID.
- Database role used by the API has only required DML rights; migration role is separate.
- Search history expires on a short configurable schedule. Image files are deleted after processing regardless of success. Deleting a search cascades its results.
- Profile deletion disables indexing immediately, revokes active enrollment, removes sources, and schedules deletion of restricted matching artifacts.
- Account deletion invalidates sessions and removes or anonymizes user-owned searches per the retention policy; security audit records are retained only as legally/operationally justified.
- Migrations and restore-from-backup are tested from a clean database before release.