from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "veridian"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    api_cors_origins: str = "http://localhost:3000"

    jwt_secret: str = "change-me-to-a-random-64-char-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""

    @staticmethod
    def _frontend_oauth_redirect(app_url: str, provider: str) -> str:
        return f"{app_url.rstrip('/')}/auth/callback/{provider}"

    @property
    def google_oauth_redirect_uri(self) -> str:
        legacy = "/api/v1/auth/google/callback"
        if self.google_redirect_uri and legacy not in self.google_redirect_uri:
            return self.google_redirect_uri
        return self._frontend_oauth_redirect(self.app_url, "google")

    @property
    def github_oauth_redirect_uri(self) -> str:
        legacy = "/api/v1/auth/github/callback"
        if self.github_redirect_uri and legacy not in self.github_redirect_uri:
            return self.github_redirect_uri
        return self._frontend_oauth_redirect(self.app_url, "github")

    database_url: str = "postgresql+asyncpg://veridian:veridian@localhost:5432/veridian"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "amqp://veridian:veridian@localhost:5672//"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "veridian"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    health_check_infra: bool = True

    rate_limit_requests_per_minute: int = 60
    rate_limit_ai_requests_per_minute: int = 20
    rate_limit_enabled: bool = True

    openai_api_key: str = ""
    ai_model: str = "gpt-4o"
    ai_max_context_tokens: int = 32000

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key.strip())

    auth_max_login_attempts: int = 5
    auth_lockout_minutes: int = 15
    auth_min_password_length: int = 8
    admin_emails: str = ""

    @property
    def admin_email_list(self) -> set[str]:
        return {email.strip().lower() for email in self.admin_emails.split(",") if email.strip()}

    @property
    def cors_origins(self) -> list[str]:
        origins: list[str] = []
        seen: set[str] = set()
        for raw in (self.app_url, self.api_cors_origins):
            for part in raw.split(","):
                origin = part.strip().rstrip("/")
                if origin and origin not in seen:
                    seen.add(origin)
                    origins.append(origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
