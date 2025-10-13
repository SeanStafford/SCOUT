"""
Data storage domain.

Handles persistence to PostgreSQL and other storage backends.

Public API exports only the interfaces needed by other contexts.
Credentials and implementation details remain private.
"""

from scout.contexts.storage.postgres import (
    db_exists,
    create_db,
    DatabaseWrapper,
    InformationSchema,
)
from scout.contexts.storage.config import (
    DatabaseConfig,
    create_database_config,
)

__all__ = [
    # PostgreSQL operations
    "db_exists",
    "create_db",
    "DatabaseWrapper",
    "InformationSchema",
    # Configuration
    "DatabaseConfig",
    "create_database_config",
]
