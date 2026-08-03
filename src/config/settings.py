from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ──────────────────────────────────────────────────────────
    llm_provider: str = Field(default="gemini")   # deepseek | gemini | anthropic | anthropic_aws
    anthropic_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")
    deepseek_api_key: str = Field(default="")
    llm_model_anthropic: str = Field(default="claude-sonnet-4-20250514")
    llm_model_gemini: str = Field(default="gemini-2.0-flash")
    llm_model_deepseek: str = Field(default="deepseek-chat")
    llm_timeout_ms: int = Field(default=15000)

    # ── Claude Platform on AWS (IAM/SigV4 — no API key) ─────────────────────────
    # Left unset by default: the workspace region only scopes IAM/billing, not
    # where inference runs, so it must be chosen deliberately rather than
    # inherited from aws_region below (see llm_client.py docstring).
    claude_aws_region: str = Field(default="")
    claude_aws_workspace_id: str = Field(default="")

    # ── Image Extraction ──────────────────────────────────────────────────────
    image_extraction_provider: str = Field(default="gemini")  # gemini | anthropic
    image_extraction_ttl_seconds: int = Field(default=1800)

    # ── Cognito ───────────────────────────────────────────────────────────────
    cognito_user_pool_id: str = Field(default="af-south-1_AnsxEBThZ")
    cognito_region: str = Field(default="af-south-1")
    cognito_client_id: str = Field(default="")
    student_id_field: str = Field(default="sub")

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://host.docker.internal:6379")
    redis_password: str = Field(default="")
    session_ttl_seconds: int = Field(default=86400)

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(default="")
    database_pool_size: int = Field(default=10)

    # ── S3 ────────────────────────────────────────────────────────────────────
    image_storage_provider: str = Field(default="s3")
    image_bucket_name: str = Field(default="learnairium-bucket")
    image_s3_prefix: str = Field(default="HOMEWORK_IMAGE")
    image_max_size_mb: int = Field(default=5)
    aws_region: str = Field(default="af-south-1")

    # ── Usage Limits ──────────────────────────────────────────────────────────
    daily_session_limit: int = Field(default=5)
    max_steps_default: int = Field(default=5)
    max_steps_hard_cap: int = Field(default=7)

    # ── Service ───────────────────────────────────────────────────────────────
    environment: str = Field(default="development")
    port: int = Field(default=2095)
    log_level: str = Field(default="info")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
