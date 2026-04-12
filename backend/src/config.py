from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """GovFlow configuration loaded from environment variables."""

    govflow_env: str = "local"

    # GDB
    gdb_endpoint: str = "ws://localhost:8182/gremlin"
    gdb_username: str = ""
    gdb_password: str = ""

    # Hologres / PostgreSQL
    hologres_dsn: str = "postgresql://govflow:govflow_dev_2026@localhost:5433/govflow"

    # DashScope
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    # OSS / MinIO
    oss_endpoint: str = "http://localhost:9100"
    oss_access_key_id: str = "minioadmin"
    oss_access_key_secret: str = "minioadmin123"
    oss_bucket: str = "govflow-dev"
    oss_region: str = "us-east-1"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production-2026"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # CORS
    cors_origins: str = "http://localhost:3100"

    # Rate limiting
    rate_limit_default: str = "60/minute"
    rate_limit_search: str = "30/minute"

    # Logging
    log_level: str = "DEBUG"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
