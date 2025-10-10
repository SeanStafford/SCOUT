"""
Data storage domain.

Handles persistence to PostgreSQL and other storage backends.
"""

from scout.contexts.storage.postgres import (
    db_exists,
    create_db,
    DatabaseWrapper,
    InformationSchema,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
)

__all__ = [
    "db_exists",
    "create_db",
    "DatabaseWrapper",
    "InformationSchema",
    "POSTGRES_PASSWORD",
    "POSTGRES_PORT",
]
