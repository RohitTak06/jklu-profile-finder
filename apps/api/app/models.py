from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('USER', 'ADMIN', 'SUPER_ADMIN')"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="USER", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        Index("ix_profiles_institution_active", "institution_id", "is_active"),
        CheckConstraint("academic_year IS NULL OR academic_year BETWEEN 1 AND 10"),
        CheckConstraint("visibility IN ('PRIVATE', 'ENROLLED', 'PUBLIC')"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str | None] = mapped_column(String(160))
    program: Mapped[str | None] = mapped_column(String(160))
    academic_year: Mapped[int | None] = mapped_column(Integer)
    bio: Mapped[str | None] = mapped_column(Text)
    profile_image_url: Mapped[str | None] = mapped_column(String(2048))
    visibility: Mapped[str] = mapped_column(String(16), default="PRIVATE", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProfileSource(Base):
    __tablename__ = "profile_sources"
    __table_args__ = (
        Index("ix_profile_sources_type_status", "source_type", "verification_status"),
        CheckConstraint("source_type IN ('LINKEDIN', 'INSTAGRAM', 'GITHUB', 'PORTFOLIO', 'JKLU', 'OTHER')"),
        CheckConstraint("verification_status IN ('UNVERIFIED', 'VERIFIED', 'INVALID', 'REVOKED')"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_identifier: Mapped[str | None] = mapped_column(String(256))
    verification_status: Mapped[str] = mapped_column(String(24), default="UNVERIFIED", nullable=False)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )


class EnrolledIdentityRecord(Base):
    __tablename__ = "enrolled_identity_records"
    __table_args__ = (
        CheckConstraint("consent_status IN ('PENDING', 'ACTIVE', 'REVOKED', 'EXPIRED')"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    identity_reference: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    consent_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    consent_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str | None] = mapped_column(String(64))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )


class Search(Base):
    __tablename__ = "searches"
    __table_args__ = (
        Index("ix_searches_status_expiry", "status", "expires_at"),
        CheckConstraint("status IN ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'DELETED')"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="QUEUED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), default=uuid4, nullable=False)


class SearchResult(Base):
    __tablename__ = "search_results"
    __table_args__ = (
        UniqueConstraint("search_id", "rank", name="uq_search_results_rank"),
        UniqueConstraint("search_id", "profile_id", name="uq_search_results_profile"),
        CheckConstraint("ranking_score >= 0 AND ranking_score <= 1"),
        CheckConstraint("confidence_band IN ('LOW', 'MEDIUM', 'HIGH')"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    search_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("searches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    ranking_score: Mapped[float] = mapped_column(nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(12), nullable=False)
    matching_signals: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(96), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    user_agent_hash: Mapped[str | None] = mapped_column(String(128))
    event_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )