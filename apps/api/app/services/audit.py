import hashlib
import hmac
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import AuditLog


def _hash_value(value: str | None) -> str | None:
    if not value:
        return None
    key = get_settings().jwt_secret.get_secret_value().encode("utf-8")
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


async def record_audit(
    session: AsyncSession,
    request: Request,
    action: str,
    resource_type: str,
    actor_id: UUID | None = None,
    resource_id: UUID | None = None,
) -> None:
    client_ip = request.client.host if request.client else None
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_hash=_hash_value(client_ip),
            user_agent_hash=_hash_value(request.headers.get("user-agent")),
            event_metadata={},
        )
    )