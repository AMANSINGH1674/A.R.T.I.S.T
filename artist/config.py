"""
Configuration management for ARTIST application
"""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = Field(default="ARTIST", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    
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
    default_llm_provider: str = Field(default="openai", alias="DEFAULT_LLM_PROVIDER")
    default_model: str = Field(default="gpt-4", alias="DEFAULT_MODEL")
    
    # Security Configuration
    secret_key: str = Field(default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
