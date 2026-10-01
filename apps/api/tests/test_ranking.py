import asyncio
from uuid import uuid4

from app.matching.ranking import AuthorizedProfile, CandidateMatcher, SearchEvidence


def profile(**overrides: object) -> AuthorizedProfile:
    values: dict[str, object] = {
        "id": uuid4(),
        "display_name": "Aarav Sharma",
        "institution_code": "JKLU",
        "consent_active": True,
        "is_active": True,
        "visibility": "PUBLIC",
        "department": "Computer Science",
        "academic_year": 2,
        "skills": frozenset({"python", "design"}),
        "public_username": "aarav-dev",
        "sources_consistent": True,
    }
    values.update(overrides)
    return AuthorizedProfile(**values)


def test_only_active_consented_visible_jklu_profiles_are_candidates() -> None:
    matcher = CandidateMatcher()
    profiles = [
        profile(),
        profile(consent_active=False),
        profile(is_active=False),
        profile(institution_code="OTHER"),
        profile(visibility="PRIVATE"),
    ]

    assert len(matcher.generate_candidates(profiles)) == 1


def test_ranker_orders_supported_candidate_and_explains_signals() -> None:
    matcher = CandidateMatcher()
    expected = profile()
    unrelated = profile(
        display_name="Meera Joshi",
        department="Architecture",
        academic_year=4,
        skills=frozenset({"accounting"}),
        public_username="meera-j",
        sources_consistent=False,
    )
    evidence = SearchEvidence(
        name="Aarav Sharma",
        department="Computer Science",
        academic_year=2,
        skills=frozenset({"python", "design"}),
        public_username="aarav-dev",
    )

    results = asyncio.run(matcher.rank_candidates(evidence, [unrelated, expected]))

    assert [result.profile.id for result in results] == [expected.id]
    assert results[0].confidence_band == "HIGH"
    assert "JKLU affiliation" in results[0].evidence
    assert results[0].score == 1.0