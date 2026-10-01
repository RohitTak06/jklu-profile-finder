from contextlib import asynccontextmanager
from hmac import compare_digest
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    access_token_ttl,
    create_access_token,
    decode_access_token,
    hash_password,
    token_fingerprint,
    verify_password,
)
from app.db import Base, engine, get_session
from app.models import User
from app.schemas import Credentials, UserResponse
from app.services.audit import record_audit
from app.services.image_processor import InvalidImageError, normalize_image

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    if settings.app_env == "development":
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    yield
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="JKLU Profile Finder API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin != settings.web_origin:
            return Response(status_code=status.HTTP_403_FORBIDDEN)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


async def enforce_rate_limit(request: Request, key: str, limit: int, window_seconds: int) -> None:
    try:
        redis: Redis = request.app.state.redis
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Rate limiting is unavailable") from error
    if count > limit:
        raise HTTPException(status_code=429, detail="Too many requests")


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get("access_token")
    user_id = decode_access_token(token) if token else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        revoked = await request.app.state.redis.exists(f"auth:revoked:{token_fingerprint(token)}")
    except Exception as error:
        raise HTTPException(status_code=503, detail="Session validation is unavailable") from error
    if revoked:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_csrf(request: Request) -> None:
    cookie = request.cookies.get("csrf_token", "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or not compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready(request: Request, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    try:
        await session.execute(select(1))
        await request.app.state.redis.ping()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Dependencies are not ready") from error
    return {"status": "ready"}


@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=201)
async def register(
    credentials: Credentials,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> User:
    await enforce_rate_limit(request, f"auth:register:{request.client.host if request.client else 'unknown'}", 5, 3600)
    user = User(email=str(credentials.email).lower(), password_hash=hash_password(credentials.password))
    session.add(user)
    try:
        await session.flush()
        await record_audit(session, request, "auth.register.succeeded", "user", user.id, user.id)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Account could not be created") from error
    response.set_cookie(
        "access_token",
        create_access_token(user.id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=1200,
        path="/",
    )
    from secrets import token_urlsafe

    response.set_cookie(
        "csrf_token", token_urlsafe(32), httponly=False, secure=settings.cookie_secure,
        samesite="lax", max_age=1200, path="/",
    )
    return user


@app.post("/api/v1/auth/login", response_model=UserResponse)
async def login(
    credentials: Credentials,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> User:
    await enforce_rate_limit(request, f"auth:login:{request.client.host if request.client else 'unknown'}", 10, 900)
    result = await session.execute(select(User).where(User.email == str(credentials.email).lower()))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(credentials.password, user.password_hash):
        await record_audit(session, request, "auth.login.failed", "session")
        await session.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await record_audit(session, request, "auth.login.succeeded", "session", user.id, user.id)
    await session.commit()
    response.set_cookie(
        "access_token", create_access_token(user.id), httponly=True,
        secure=settings.cookie_secure, samesite="lax", max_age=1200, path="/",
    )
    from secrets import token_urlsafe

    response.set_cookie(
        "csrf_token", token_urlsafe(32), httponly=False, secure=settings.cookie_secure,
        samesite="lax", max_age=1200, path="/",
    )
    return user


@app.post("/api/v1/auth/logout", status_code=204)
async def logout(
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    require_csrf(request)
    token = request.cookies.get("access_token")
    user_id = decode_access_token(token) if token else None
    if token and user_id:
        try:
            await request.app.state.redis.set(
                f"auth:revoked:{token_fingerprint(token)}", "1", ex=access_token_ttl(token)
            )
        except Exception as error:
            raise HTTPException(status_code=503, detail="Session revocation is unavailable") from error
        await record_audit(session, request, "auth.logout", "session", user_id, user_id)
        await session.commit()
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    response.status_code = 204
    return response


@app.get("/api/v1/auth/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@app.post("/api/v1/search", status_code=503)
async def search(
    request: Request,
    image: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    require_csrf(request)
    await enforce_rate_limit(request, f"search:user:{user.id}", settings.searches_per_hour, 3600)
    client_ip = request.client.host if request.client else "unknown"
    await enforce_rate_limit(
        request, f"search:ip:{client_ip}", settings.searches_per_ip_per_hour, 3600
    )
    data = await image.read(settings.max_upload_bytes + 1)
    try:
        normalize_image(data, settings.max_upload_bytes, settings.max_image_pixels)
    except InvalidImageError as error:
        raise HTTPException(status_code=422, detail="Image is invalid or unsupported") from error
    finally:
        await image.close()
    await record_audit(session, request, "search.rejected.index_unavailable", "search", user.id)
    await session.commit()
    raise HTTPException(status_code=503, detail="Authorized matching index is not configured")