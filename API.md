# API Contract

All routes are under `/api/v1`. Production uses HTTPS. This document records the target contract; route tables label current implementation explicitly. Implemented errors still use FastAPI's `detail` shape; the standardized envelope below is planned. Messages must never include stack traces, SQL, paths, or secrets. Authenticated endpoints derive the user from the server-side session, never from caller-supplied user IDs.

## Authentication

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Create an account; rate limited (email verification planned) |
| POST | `/auth/login` | Establish secure session; throttled and audited |
| POST | `/auth/logout` | Revoke current session and clear cookie |
| GET | `/auth/me` | Return current user-safe account fields |

Registration, login, logout, and current-user lookup are implemented. Email verification, password reset, refresh-token rotation, and verification anti-enumeration flows are planned, not present.

Cookie-based state changes require CSRF protection. Password reset and verification endpoints must use one-time, hashed, expiring tokens and avoid account enumeration.

## Search

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/search` | Submit one photo as multipart field `image`; currently validates/re-encodes in memory then returns 503 until the authorized index is configured |
| GET | `/search/{search_id}` | Planned: read owner-scoped status |
| GET | `/search/{search_id}/results` | Planned: read owner-scoped ranked possible matches |
| DELETE | `/search/{search_id}` | Planned: delete persisted history/results |

`POST /search` currently requires an authenticated, active user; checks a per-account quota; validates the decoded format, byte limit, and pixel limit; re-encodes in memory; and returns 503 because the authorized index is not configured. It does not persist a search or return a `search_id`. Email verification, IP search quotas, async job status, and full request-body limiting remain planned. No additional search fields are accepted. Client-supplied filenames and MIME types are ignored as security authorities.

Example result:

```json
{
  "search_id": "uuid",
  "status": "completed",
  "matches": [
    {
      "profile_id": "uuid",
      "rank": 1,
      "label": "Possible match",
      "confidence_band": "medium",
      "profile": {
        "display_name": "Demo Profile",
        "department": "Computer Science",
        "academic_year": 2,
        "sources": [{ "type": "GITHUB", "url": "https://github.com/example" }]
      },
      "evidence": ["JKLU affiliation", "Consistent profile information"]
    }
  ]
}
```

If no candidate clears the configured threshold, return `matches: []` and `outcome: "NO_RELIABLE_MATCH"`. Confidence is never presented as certainty. Raw vectors, internal features, consent records, and private profile fields are not exposed.

## Profiles

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/profiles/{profile_id}` | Planned: read a visible profile |
| GET | `/profiles/{profile_id}/sources` | Planned: read validated, permitted public sources |

Only active JKLU profiles visible to the caller are returned. External URLs are treated as data and are never fetched by this endpoint.

## Admin

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/admin/profiles` | Planned: paginated profile management |
| POST | `/admin/profiles/import` | Planned: import validated authorized/synthetic records |
| POST | `/admin/ingestion/run` | Planned: queue permitted ingestion run |
| GET | `/admin/audit-logs` | Planned: restricted, paginated security audit view |
| GET | `/admin/system-health` | Planned: operational health summary |

Every admin route enforces `ADMIN`/`SUPER_ADMIN` on the server and emits an audit event. Import rejects unapproved sources and does not accept arbitrary URL fetch instructions.

## Operational endpoints

`GET /health` is liveness only; `GET /ready` checks required dependencies without exposing credentials or internal exception details. Both are separately protected/limited as appropriate in deployment.

## Status and errors

Search status is one of `queued`, `processing`, `completed`, `failed`, `deleted`. Stable error codes include `INVALID_IMAGE`, `UPLOAD_TOO_LARGE`, `RATE_LIMITED`, `SEARCH_NOT_FOUND`, `FORBIDDEN`, `NO_RELIABLE_MATCH`, and `SEARCH_FAILED`. `SEARCH_NOT_FOUND` is used for absent and non-owned resources to avoid resource enumeration.