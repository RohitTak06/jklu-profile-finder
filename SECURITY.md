# Security and Threat Model

## Security principles

Least privilege, defense in depth, privacy by design, and explicit consent govern every boundary. Search requires authentication; matching is restricted to synthetic or explicitly enrolled records; JKLU is fixed server-side. No face-based search across arbitrary students, internet-wide identity lookup, private social access, or platform-control bypass is supported.

## Assets

User accounts and sessions; profile details and social links; consent and enrollment records; temporary uploaded images; any separately protected matching artifacts; search history/results; admin credentials; database and backup; audit records; API and infrastructure secrets.

## Threats and mitigations

| Threat | Likelihood | Impact | Mitigations | Residual risk |
| --- | --- | --- | --- | --- |
| Unauthorized identity matching or consent misuse | Medium | Critical | Active consent required in candidate query; fixed JKLU scope; enrollment audit; revocation/deletion; restricted matcher access; synthetic evaluation | Consent provenance or process failure remains possible; periodic review required |
| Account takeover / credential stuffing | Medium | High | Argon2id, verified email, throttling, suspicious-login controls, secure cookies, refresh rotation/revocation, MFA for admins | Phishing and compromised email remain possible |
| IDOR / profile or search enumeration | Medium | High | Owner-scoped repository queries, indistinguishable not-found behavior, server-side RBAC, authorization tests | Application logic regressions remain possible |
| Malicious image upload / parser exploit / decompression bomb | Medium | High | Byte signature and decoder validation, format allowlist, byte/pixel limits, re-encode, metadata stripping, randomized temp path, restricted worker, cleanup, optional malware scan | Image parser vulnerabilities remain possible; patching/isolation needed |
| Bulk lookup, scraping, or targeted harassment | Medium | High | Authenticated searches, per-user and IP quotas, no bulk endpoint, anomaly alerts, suspension/review, audit trail | Distributed low-rate abuse may evade thresholds |
| SQL injection | Low | High | SQLAlchemy parameterization, schema validation, least-privilege DB role, injection tests | Unsafe future raw SQL could reintroduce risk |
| SSRF through imported profile URLs | Medium | High | Never fetch arbitrary URLs in request path; allowlist approved adapters/domains; egress restrictions; redirect/IP validation where fetching is approved | DNS/redirect edge cases in future integrations |
| XSS via profile bios or external data | Medium | Medium | Render as text, escape by framework, URL scheme validation, CSP, no unsafe HTML | Browser/framework vulnerabilities remain possible |
| CSRF / session theft | Medium | High | HTTPS, HttpOnly/Secure/SameSite cookies, CSRF tokens, origin checks, short sessions, rotation | Endpoint or deployment misconfiguration remains possible |
| Secret leakage / database compromise | Low | Critical | Secret manager, separate environments, least privilege, TLS, encrypted backups, rotation, no secrets in logs/source | Privileged compromise and backup key exposure remain possible |
| Insider access to consent or matching artifacts | Low | Critical | Separate restricted store, minimum access, access audit, encryption, deletion and approval controls | Authorized insiders can still misuse access |
| DoS / API abuse | Medium | High | Reverse-proxy request limits, bounded image decoding, rate limits, queue limits, timeouts, quotas, monitoring | Large distributed attacks require provider-level protection |
| Stale, incorrect, or overconfident result | Medium | High | Source provenance, confidence threshold, no-match state, clear “Possible match” wording, holdout evaluation, disable stale sources | Model/data shift and incomplete public data remain possible |

## Image and matching data controls

- Reject unsupported or malformed data based on actual bytes and decoding, not filename or `Content-Type`.
- Enforce byte, dimension, and total-pixel limits before expensive work. Re-encode accepted images and strip EXIF/metadata.
- Use randomized temporary names, private filesystem permissions, no public static serving, and deletion in `finally` plus a scheduled orphan cleanup.
- Never put raw images or matching vectors in application logs, audit metadata, database search results, or analytics.
- Any approved identity artifact requires a separate access-controlled and encrypted store, documented key management, explicit retention, deletion/revocation behavior, and privacy review before production.

## API and platform controls

Validate requests with Pydantic; use parameterized SQL; enforce owner and role authorization server-side; cap request bodies; apply CORS allowlists, security headers, CSP, HSTS in HTTPS production, and structured redacted errors. Use request IDs and log security-relevant outcomes while hashing/minimizing IP and user-agent values. Never dereference untrusted profile URLs in a search request.

## Operational requirements

Pin and scan dependencies; build minimal non-root containers; keep PostgreSQL/Redis private; use TLS and least-privilege service accounts; manage secrets outside source control; test backups and restoration; monitor authentication, quotas, worker failures, and admin actions. CI must include lint/type checks, unit/integration tests, dependency audit, and authorization/upload security tests. Production launch requires a privacy impact review and institution approval.