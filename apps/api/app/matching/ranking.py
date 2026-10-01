from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable
from uuid import UUID


@dataclass(frozen=True)
class AuthorizedProfile:
    id: UUID
    display_name: str
    institution_code: str
    consent_active: bool
    is_active: bool
    visibility: str
    department: str | None = None
    academic_year: int | None = None
    skills: frozenset[str] = field(default_factory=frozenset)
    public_username: str | None = None
    sources_consistent: bool = False


@dataclass(frozen=True)
class SearchEvidence:
    name: str | None = None
    department: str | None = None
    academic_year: int | None = None
    skills: frozenset[str] = field(default_factory=frozenset)
    public_username: str | None = None


@dataclass(frozen=True)
class RankingConfig:
    weights: dict[str, float] = field(default_factory=lambda: {
        "name_similarity": 0.30,
        "institution": 0.20,
        "academic_match": 0.15,
        "profile_consistency": 0.15,
        "skills_overlap": 0.10,
        "username_match": 0.10,
    })
    minimum_score: float = 0.62
    high_threshold: float = 0.82
    medium_threshold: float = 0.65

    def __post_init__(self) -> None:
        if any(weight < 0 for weight in self.weights.values()):
            raise ValueError("Ranking weights must not be negative")
        if abs(sum(self.weights.values()) - 1.0) > 1e-6:
            raise ValueError("Ranking weights must sum to 1")
        if not 0 <= self.minimum_score <= 1:
            raise ValueError("Minimum score must be between 0 and 1")


@dataclass(frozen=True)
class RankedCandidate:
    profile: AuthorizedProfile
    rank: int
    score: float
    confidence_band: str
    signals: dict[str, float]
    evidence: tuple[str, ...]


class CandidateMatcher:
    """Rank authorized candidates; weighted scores are not identity probabilities."""

    def __init__(self, config: RankingConfig | None = None) -> None:
        self.config = config or RankingConfig()

    def generate_candidates(self, profiles: Iterable[AuthorizedProfile]) -> list[AuthorizedProfile]:
        return [
            profile
            for profile in profiles
            if profile.institution_code == "JKLU"
            and profile.consent_active
            and profile.is_active
            and profile.visibility in {"PUBLIC", "ENROLLED"}
        ]

    def calculate_features(
        self, evidence: SearchEvidence, profile: AuthorizedProfile
    ) -> dict[str, float]:
        name_similarity = self._similarity(evidence.name, profile.display_name)
        department_match = self._similarity(evidence.department, profile.department)
        year_match = float(
            evidence.academic_year is not None
            and profile.academic_year is not None
            and evidence.academic_year == profile.academic_year
        )
        academic_signals = [
            value for value, available in (
                (department_match, evidence.department is not None and profile.department is not None),
                (year_match, evidence.academic_year is not None and profile.academic_year is not None),
            ) if available
        ]
        shared_skills = evidence.skills & profile.skills
        all_skills = evidence.skills | profile.skills
        skills_overlap = len(shared_skills) / len(all_skills) if all_skills else 0.0
        return {
            "name_similarity": name_similarity,
            "institution": float(profile.institution_code == "JKLU"),
            "academic_match": sum(academic_signals) / len(academic_signals) if academic_signals else 0.0,
            "profile_consistency": float(profile.sources_consistent),
            "skills_overlap": skills_overlap,
            "username_match": self._similarity(evidence.public_username, profile.public_username),
        }

    async def rank_candidates(
        self, evidence: SearchEvidence, profiles: Iterable[AuthorizedProfile]
    ) -> list[RankedCandidate]:
        ranked: list[tuple[AuthorizedProfile, float, dict[str, float]]] = []
        for profile in self.generate_candidates(profiles):
            signals = self.calculate_features(evidence, profile)
            score = sum(self.config.weights[name] * value for name, value in signals.items())
            if score >= self.config.minimum_score:
                ranked.append((profile, score, signals))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return [
            RankedCandidate(
                profile=profile,
                rank=index,
                score=round(score, 4),
                confidence_band=self._confidence_band(score),
                signals=signals,
                evidence=self.explain_match(signals),
            )
            for index, (profile, score, signals) in enumerate(ranked, start=1)
        ]

    @staticmethod
    def explain_match(signals: dict[str, float]) -> tuple[str, ...]:
        evidence: list[str] = []
        if signals["institution"] == 1:
            evidence.append("JKLU affiliation")
        if signals["name_similarity"] >= 0.85:
            evidence.append("Consistent profile name")
        if signals["academic_match"] >= 0.75:
            evidence.append("Consistent academic information")
        if signals["profile_consistency"] == 1:
            evidence.append("Verified public profile information")
        if signals["skills_overlap"] >= 0.5:
            evidence.append("Overlapping public skills")
        if signals["username_match"] >= 0.85:
            evidence.append("Matching public username")
        return tuple(evidence)

    def _confidence_band(self, score: float) -> str:
        if score >= self.config.high_threshold:
            return "HIGH"
        if score >= self.config.medium_threshold:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _similarity(left: str | None, right: str | None) -> float:
        if not left or not right:
            return 0.0
        return SequenceMatcher(None, left.strip().casefold(), right.strip().casefold()).ratio()