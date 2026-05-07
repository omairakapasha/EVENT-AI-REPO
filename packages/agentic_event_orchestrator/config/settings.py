from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database — accepts plain postgresql:// and auto-converts to asyncpg driver
    database_url: str = ""
    app_database_url: str = ""  # pooled URL from .env (APP_DATABASE_URL)

    @property
    def async_database_url(self) -> str:
        """Return asyncpg-compatible URL, preferring APP_DATABASE_URL.

        SQLAlchemy's asyncpg dialect does NOT forward query params like
        ``sslmode`` to asyncpg's ``connect()``.  We strip ``sslmode`` here
        and expose ``ssl_required`` so the engine can pass SSL via
        ``connect_args={"ssl": "require"}`` instead.
        """
        url = self.app_database_url or self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)

        # Strip sslmode from query params — handled via connect_args
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params.pop("sslmode", None)
        new_query = urlencode({k: v[0] for k, v in params.items()})
        return urlunparse(parsed._replace(query=new_query))

    @property
    def ssl_required(self) -> bool:
        """True when the original DB URL includes sslmode=require (or stricter)."""
        url = self.app_database_url or self.database_url
        return "sslmode=require" in url or "sslmode=verify" in url

    # Gemini / LLM
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_model: str = "gemini-3-flash-preview"  # matches GEMINI_MODEL in .env

    # Backend API
    backend_api_url: str = "http://localhost:3001/api/v1"

    # Mem0
    mem0_api_key: str = ""

    # Service auth
    ai_service_api_key: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003"

    # Rate limiting
    rate_limit_per_minute: int = 30

    # Session
    session_ttl_days: int = 30

    # Agent safety
    max_handoff_depth: int = 5
    max_response_chars: int = 2000  # tighter cap — keeps responses concise

    # Prompt injection firewall
    injection_blocklist_path: str = "data/injection_blocklist.yaml"
    max_input_chars: int = 2000
    promptguard_threshold: float = 0.85
    alignment_threshold: float = 0.80

    # TruLens RAG evaluation
    trulens_enabled: bool = False
    trulens_groundedness_threshold: float = 0.70

    # Look for .env in the package dir first, then fall back to the monorepo root
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
