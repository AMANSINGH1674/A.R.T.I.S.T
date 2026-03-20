"""
Pytest configuration — sets required environment variables before any
module-level import of `artist.config.settings` occurs.
"""

import os

# Set required env vars before artist modules are imported.
# Use safe values that are only valid for testing.
os.environ.setdefault(
    "SECRET_KEY",
    "test_only_secret_key_not_for_production_use_at_all_x"  # 52 chars, not the leaked default
)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_artist.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ENVIRONMENT", "test")
