import asyncio
from io import BytesIO

import httpx
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base, get_session
from app.main import app
from app.models import AuditLog


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.values: set[str] = set()

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        return None

    async def exists(self, key: str) -> int:
        return int(key in self.values)

    async def set(self, key: str, value: str, ex: int) -> None:
        self.values.add(key)


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (20, 20), color=(70, 100, 80)).save(output, format="PNG")
    return output.getvalue()


def test_registration_search_and_logout_flow_fails_closed_without_index() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        original_overrides = app.dependency_overrides.copy()

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async def get_test_session():
            async with session_factory() as session:
                yield session

        app.dependency_overrides[get_session] = get_test_session
        app.state.redis = FakeRedis()

        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                unauthorized = await client.post(
                    "/api/v1/search", files={"image": ("photo.png", image_bytes(), "image/png")}
                )
                assert unauthorized.status_code == 401

                registered = await client.post(
                    "/api/v1/auth/register",
                    json={"email": "student@example.edu", "password": "long-test-password"},
                )
                assert registered.status_code == 201
                assert registered.json()["email"] == "student@example.edu"
                assert "access_token" in client.cookies
                assert "csrf_token" in client.cookies

                current_user = await client.get("/api/v1/auth/me")
                assert current_user.status_code == 200

                unavailable = await client.post(
                    "/api/v1/search",
                    files={"image": ("photo.png", image_bytes(), "image/png")},
                    headers={"X-CSRF-Token": client.cookies["csrf_token"]},
                )
                assert unavailable.status_code == 503
                assert "index is not configured" in unavailable.json()["detail"]
                assert any(key.startswith("search:user:") for key in app.state.redis.counts)
                assert any(key.startswith("search:ip:") for key in app.state.redis.counts)

                previous_token = client.cookies["access_token"]
                logged_out = await client.post(
                    "/api/v1/auth/logout",
                    headers={"X-CSRF-Token": client.cookies["csrf_token"]},
                )
                assert logged_out.status_code == 204
                client.cookies.set("access_token", previous_token)
                assert (await client.get("/api/v1/auth/me")).status_code == 401

            async with session_factory() as session:
                result = await session.execute(select(AuditLog))
                audit_events = result.scalars().all()
                actions = {event.action for event in audit_events}
                assert {"auth.register.succeeded", "search.rejected.index_unavailable", "auth.logout"} <= actions
                assert all(event.ip_hash and event.user_agent_hash for event in audit_events)
                assert all(not event.event_metadata for event in audit_events)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)
            await engine.dispose()

    asyncio.run(exercise())