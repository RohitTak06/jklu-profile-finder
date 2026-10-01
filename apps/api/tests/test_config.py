import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_requires_secure_cookies_and_https_origin() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="a-random-production-secret-value-long-enough",
            cookie_secure=False,
            web_origin="https://profiles.example.edu",
        )

    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="a-random-production-secret-value-long-enough",
            cookie_secure=True,
            web_origin="http://profiles.example.edu",
        )

    settings = Settings(
        app_env="production",
        jwt_secret="a-random-production-secret-value-long-enough",
        cookie_secure=True,
        web_origin="https://profiles.example.edu",
    )
    assert settings.cookie_secure