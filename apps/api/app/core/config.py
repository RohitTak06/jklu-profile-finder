from functools import lru_cache

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://profile_finder:local_dev_only@localhost:5432/profile_finder"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: SecretStr = SecretStr("local-development-secret-change-this-value")
    web_origin: str = "http://localhost:3000"
    cookie_secure: bool = False
    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 20_000_000
    searches_per_hour: int = 10
    searches_per_ip_per_hour: int = 30

    @field_validator("jwt_secret")
    @classmethod
    def require_production_secret(cls, value: SecretStr, info: object) -> SecretStr:
        if getattr(info, "data", {}).get("app_env") == "production":
            secret = value.get_secret_value()
            if len(secret) < 32 or secret == "local-development-secret-change-this-value":
                raise ValueError("JWT_SECRET must be an explicit random value of at least 32 characters")
        return value

    @model_validator(mode="after")
    def require_secure_production_transport(self) -> "Settings":
        if self.app_env == "production":
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be enabled in production")
            if not self.web_origin.startswith("https://"):
                raise ValueError("WEB_ORIGIN must use HTTPS in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()