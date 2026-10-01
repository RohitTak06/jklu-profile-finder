# Privacy Notes

## Data purpose and scope

The service is intended to find possible JKLU profile matches from one photo, but the current build has no image-to-identity matcher and no authorized profile index. It does not identify arbitrary people, search the open internet for identities, scrape social accounts, or access private accounts. Matching records must be synthetic or explicitly consented; a public social URL alone is not identity-matching consent.

## Current data handling

- Account registration stores a normalized email and Argon2id password hash.
- Login state is held in short-lived signed cookies; logout revokes that access token in Redis until expiry.
- Audit records store action/resource IDs and keyed hashes of IP/user-agent values; they do not store credentials, image bytes, or request body metadata.
- Search images are read with byte limits, decoded, re-encoded to JPEG, and metadata is stripped in memory. When the authorized index is unavailable, the API returns 503 and does not persist the image or search record.
- The database models include profile, consent, search, result, and audit structures, but deletion/export/enrollment workflows are not implemented.

## Retention and user controls

The product target is immediate deletion of upload bytes after processing and short, documented retention for search metadata. Current upload handling does not persist the image. Search-history expiry, account export/deletion, profile deletion, consent revocation UI, and matching-artifact cleanup are not yet implemented; do not promise them to users until verified end-to-end.

Before production, publish purpose-specific consent, retention periods, data-subject request process, source visibility policy, access controls, incident contact, and institutional/privacy review. Do not retain raw photos or biometric artifacts by default. Any approved matching artifacts require a separate encrypted, access-logged store and tested revocation/deletion path.