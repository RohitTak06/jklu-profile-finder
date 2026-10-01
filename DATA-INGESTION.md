# Data Ingestion

## Allowed data

Only synthetic records or records with documented, active enrollment consent may enter the identity-matching index. JKLU is a fixed institution boundary. Public professional profile fields may be displayed only where their visibility permits it; public availability alone is not permission to use a photo for identity matching.

No general social-media scraper is included. Do not bypass authentication, CAPTCHAs, robots restrictions, rate limits, access controls, private profiles, or provider terms. Prefer official APIs and permitted access. Search requests must never fetch stored profile URLs.

## Adapter contract

Future adapters implement four independent async stages:

```python
class ProfileSourceAdapter:
    async def discover(self, cursor=None): ...
    async def fetch(self, source_reference): ...
    async def normalize(self, source_record): ...
    async def validate(self, normalized_record): ...
```

The intended pipeline is `discover -> fetch -> normalize -> validate -> deduplicate -> persist -> index -> quality report`. Adapter code must declare permitted source, quotas, provenance, retrieved timestamp, and failure handling. The interface and ingestion worker are not implemented in the current snapshot.

## Validation and deduplication

Pin institution to JKLU in the API, not importer input. Validate profile field lengths, year ranges, visibility, consent state, source type, URL scheme/host, and canonical link shape. Never fetch an arbitrary imported URL; any future fetcher needs domain allowlists, redirect/IP validation, and egress restrictions to mitigate SSRF. Keep provenance (`source`, source URL, retrieved time, last verified time) and surface conflicting values for administrator review rather than silently choosing one.

Deduplication should use stable provider IDs when permitted, then normalized verified identifiers; names alone are not unique keys. Do not merge profiles automatically on face similarity. Record the reason and provenance for reviewed merges.

## Consent lifecycle

Before an enrollment can participate, record the affirmative consent version and timestamp, make its matching reference active, and disclose purpose/retention/deletion. Revocation must immediately exclude the record from candidate generation and queue destruction of any isolated matching artifact. Production enrollment UI, consent capture, revocation workflow, source adapters, and data-quality dashboard remain unimplemented.