import logging
import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings

_config_logger = logging.getLogger("govflow.config")

_DEFAULT_JWT_SECRET = "dev-secret-change-in-production-2026"


class Settings(BaseSettings):
    """GovFlow configuration loaded from environment variables."""

    govflow_env: str = "local"

    # GDB
    gdb_endpoint: str = "ws://localhost:8182/gremlin"
    gdb_username: str = ""
    gdb_password: str = ""

    # Hologres / PostgreSQL
    hologres_dsn: str = "postgresql://govflow:govflow_dev_2026@localhost:5433/govflow"

    # DashScope (REQUIRED for embeddings and agent LLM calls)
    # Set via DASHSCOPE_API_KEY env var or .env file
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    # OSS / MinIO
    oss_endpoint: str = "http://localhost:9100"
    oss_access_key_id: str = "minioadmin"
    oss_access_key_secret: str = "minioadmin123"
    oss_bucket: str = "govflow-dev"
    oss_region: str = "us-east-1"

    # JWT
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # CORS
    cors_origins: str = "http://localhost:3100"

    # Rate limiting
    rate_limit_default: str = "60/minute"
    rate_limit_search: str = "30/minute"

    # Logging
    log_level: str = "DEBUG"

    # OpenTelemetry (3.6)
    otel_endpoint: str | None = None

    # Sentry (3.7)
    sentry_dsn: str | None = None

    # Rate limiting — Redis (3.9)
    redis_url: str | None = None

    # DashScope token budget per user per day (3.9)
    dashscope_tokens_per_user_per_day: int = 100_000

    # OSS hardening (3.10)
    oss_sts_role_arn: str | None = None
    oss_kms_key_id: str | None = None
    oss_presign_get_ttl_s: int = 300
    oss_presign_put_ttl_s: int = 3600

    # --- Demo mode ---
    # Enables deterministic cached LLM responses + relaxed rate limits for the
    # pitch demo. All three flags must be set via env vars (DEMO_MODE=true, etc.)
    demo_mode: bool = False
    demo_cache_enabled: bool = False
    demo_cache_dir: str = ".cache/llm_responses"
    demo_cache_offline_only: bool = False  # True: raise on cache miss (pure offline)
    demo_user_rate_limit: str = "1000/minute"
    demo_timeout_seconds: int = 60

    # --- Assistant / Chat ---
    chat_rate_limit_per_minute: int = 20
    chat_session_ttl_hours: int = 24
    # daily_salt: computed from date if empty
    daily_salt: str = ""
    # OSS domain allowlist for SSRF guard on file_url inputs
    oss_allowed_domains: list[str] = ["aliyuncs.com", "oss-cn-", "oss-ap-", "localhost"]
    assistant_max_tool_iterations: int = 4
    assistant_history_limit: int = 20

    # --- Upload limits ---
    max_upload_mb_default: int = 20
    max_upload_mb_privileged: int = 50

    # --- Prometheus metrics scrape allowlist ---
    # Comma-separated IPs allowed to scrape /metrics.
    # Empty string = allow all (default for local dev).
    # In production, set to the Prometheus server IP(s).
    prometheus_allow_ips: str = ""

    # --- Qwen model routing (override defaults per tier) ---
    qwen_reasoning: str = "qwen-plus-latest"
    qwen_reasoning_max: str = "qwen-max-latest"
    qwen_reasoning_lite: str = "qwen-turbo-latest"
    qwen_vision: str = "qwen-vl-plus-latest"
    qwen_vision_max: str = "qwen-vl-max-latest"

    # --- Qwen task-type timeouts (seconds) ---
    qwen_timeout_vision_s: int = 180
    qwen_timeout_reasoning_s: int = 120
    qwen_timeout_embedding_s: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def _validate_jwt_secret(self) -> "Settings":
        """Enforce JWT secret strength.

        - cloud mode: raise RuntimeError if secret is default OR shorter than 32 chars.
        - local/dev mode: emit a WARNING log but continue.
        """
        is_weak = self.jwt_secret == _DEFAULT_JWT_SECRET or len(self.jwt_secret) < 32
        if is_weak:
            if self.govflow_env == "cloud":
                raise RuntimeError(
                    "INSECURE: JWT_SECRET is too weak or still using the default value. "
                    "Set a strong JWT_SECRET (>=32 chars) before deploying to cloud."
                )
            else:
                _config_logger.warning(
                    "JWT_SECRET is weak or using the default dev value — "
                    "do NOT use this in production."
                )
        return self

    @model_validator(mode="after")
    def _remove_localhost_from_oss_domains_in_cloud(self) -> "Settings":
        """Strip 'localhost' from OSS allowed domains when running in cloud mode."""
        if self.govflow_env == "cloud":
            self.oss_allowed_domains = [d for d in self.oss_allowed_domains if d != "localhost"]
        return self


settings = Settings()

# Startup warnings for missing critical configuration
if not settings.dashscope_api_key:
    warnings.warn(
        "DASHSCOPE_API_KEY is not set. Embedding generation and agent LLM calls will fail. "
        "Set it via DASHSCOPE_API_KEY env var or in .env file.",
        stacklevel=1,
    )
    _config_logger.warning(
        "DASHSCOPE_API_KEY is not set — embedding pipeline and agent LLM calls are disabled"
    )
