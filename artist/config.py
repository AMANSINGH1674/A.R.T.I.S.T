"""
Configuration management for ARTIST application
"""

import os
import sys
from typing import Optional, List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = Field(default="ARTIST", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")

    # CORS — never use ["*"] with allow_credentials=True
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="ALLOWED_ORIGINS"
    )

    # Database Configuration
    database_url: str = Field(default="sqlite:///./artist.db", alias="DATABASE_URL")

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    # Vector Database Configuration
    milvus_host: str = Field(default="localhost", alias="MILVUS_HOST")
    milvus_port: int = Field(default=19530, alias="MILVUS_PORT")
    pinecone_api_key: Optional[str] = Field(default=None, alias="PINECONE_API_KEY")
    pinecone_environment: Optional[str] = Field(default=None, alias="PINECONE_ENVIRONMENT")

    # LLM Configuration
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    default_llm_provider: str = Field(default="groq", alias="DEFAULT_LLM_PROVIDER")
    default_model: str = Field(default="mistralai/mistral-small-3.1-24b-instruct-2503", alias="DEFAULT_MODEL")

    # NVIDIA NIM Configuration
    # API key from https://build.nvidia.com — free credits to start
    nvidia_api_key: Optional[str] = Field(default=None, alias="NVIDIA_API_KEY")
    nim_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        alias="NIM_BASE_URL"
    )
    nim_chat_model: str = Field(
        default="meta/llama-3.1-70b-instruct",
        alias="NIM_CHAT_MODEL"
    )
    nim_embedding_model: str = Field(
        default="nvidia/nv-embedqa-e5-v5",
        alias="NIM_EMBEDDING_MODEL"
    )
    # Set to "nim" to use NVIDIA NIM for embeddings instead of OpenAI
    embedding_provider: str = Field(default="nim", alias="EMBEDDING_PROVIDER")

    # Security Configuration — SECRET_KEY must be set via env; no hardcoded default
    secret_key: str = Field(..., alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    # Max length for user_request inputs (prevents abuse)
    max_request_length: int = Field(default=10000, alias="MAX_REQUEST_LENGTH")

    # Monitoring & Observability
    langsmith_api_key: Optional[str] = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="artist", alias="LANGSMITH_PROJECT")
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")

    # Tool Configuration
    enable_code_execution: bool = Field(default=True, alias="ENABLE_CODE_EXECUTION")
    code_execution_timeout: int = Field(default=30, alias="CODE_EXECUTION_TIMEOUT")
    max_concurrent_executions: int = Field(default=5, alias="MAX_CONCURRENT_EXECUTIONS")

    # Workflow Configuration
    max_workflow_steps: int = Field(default=20, alias="MAX_WORKFLOW_STEPS")
    workflow_timeout: int = Field(default=300, alias="WORKFLOW_TIMEOUT")

    # RLHF Configuration
    enable_rlhf: bool = Field(default=False, alias="ENABLE_RLHF")
    feedback_collection_endpoint: Optional[str] = Field(default=None, alias="FEEDBACK_COLLECTION_ENDPOINT")

    # Additional Production Settings
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, alias="RATE_LIMIT_WINDOW")

    # Web Search Configuration
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    google_search_engine_id: Optional[str] = Field(default=None, alias="GOOGLE_SEARCH_ENGINE_ID")

    # Postgres credentials (used by docker-compose env substitution)
    postgres_password: Optional[str] = Field(default=None, alias="POSTGRES_PASSWORD")
    minio_access_key: Optional[str] = Field(default=None, alias="MINIO_ACCESS_KEY")
    minio_secret_key: Optional[str] = Field(default=None, alias="MINIO_SECRET_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        # Block the old leaked default
        if v == "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7":
            raise ValueError(
                "SECRET_KEY is set to the insecure repository default. "
                "Generate a new key: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}")
        return v.upper()

    def python_version(self) -> str:
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
