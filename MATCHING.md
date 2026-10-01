# Matching and Ranking

## Safety boundary

Candidate retrieval is restricted to profiles where institution is `JKLU`, profile is active, visibility is `PUBLIC` or `ENROLLED`, and explicit identity consent is active. The service does not query general web/social sources and does not access private accounts. Synthetic fixtures are used for tests.

There is no image-to-evidence extractor or biometric matcher in this snapshot. The upload processor only validates, decodes, strips metadata through re-encoding, and discards its in-memory result when no index is configured. It does not turn the photo into a person identity. The current endpoint returns 503 after validation instead of manufacturing a no-match or possible match.

## Independent metadata ranker

`app/matching/ranking.py` exposes candidate filtering, feature calculation, weighted ranking, and safe evidence explanations. The default experimental weights are:

| Feature | Weight |
| --- | ---: |
| Name similarity | 30% |
| JKLU institution evidence | 20% |
| Academic match | 15% |
| Verified profile consistency | 15% |
| Skills overlap | 10% |
| Public username similarity | 10% |

This is a heuristic ranking score, not a calibrated probability of identity. Thresholds are placeholders and have no production validation. Exact test inputs can produce a score of 1.0; callers must not label that as “100% match.” The consumer language remains “Possible match” with a confidence band and evidence, or “No reliable match” only after a real index-backed search.

## Evaluation required before enablement

Use only synthetic or explicitly authorized holdout identities. Measure Precision@1, Precision@3, Recall@K, false-positive rate, no-match accuracy, calibration, subgroup/error behavior where legally and ethically approved, and latency. Version the feature and ranking configuration. Set a conservative threshold based on measured false-positive cost; keep no-match as a first-class outcome. Do not tune on private or non-consenting student data.

The current tests cover consent filtering, ordering, explanation signals, and a synthetic high-scoring example. They do not establish identity accuracy or production thresholds.