import os
from dotenv import load_dotenv

from scout.contexts.storage.database import DatabaseWrapper, DatabaseConfig
from scout.contexts.storage.postgres import PostgreSQLWrapper

# Load environment variables from .env file
load_dotenv()
DATABASE_BACKEND = os.getenv("DATABASE_BACKEND")

# Supported database backends
backend_class_map = {"postgres": PostgreSQLWrapper}
ALLOWED_BACKENDS = list(backend_class_map.keys())


def get_database_wrapper(config: DatabaseConfig, ensure_exists: bool = False) -> DatabaseWrapper:
    """
    Factory function to create appropriate DatabaseWrapper based on DATABASE_BACKEND env var.

    Args:
        config: DatabaseConfig with connection details
        ensure_exists: If True, create database if it doesn't exist

    Returns:
        DatabaseWrapper implementation for the configured backend

    Raises:
        ValueError: If DATABASE_BACKEND is not set or is unsupported
    """
    if not DATABASE_BACKEND:
        raise ValueError(
            "DATABASE_BACKEND environment variable not set. "
            f"Set it in your .env file to one of: {', '.join(ALLOWED_BACKENDS)}"
        )

    backend = DATABASE_BACKEND.lower()

    if backend in ALLOWED_BACKENDS:
        # Import here to avoid circular dependency
        return backend_class_map[backend].from_config(config, ensure_exists=ensure_exists)
    else:
        raise ValueError(
            f"Unsupported database backend: '{DATABASE_BACKEND}'. "
            f"Supported backends: {', '.join(ALLOWED_BACKENDS)}"
        )
