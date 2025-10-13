"""
Data storage domain.

Handles persistence to PostgreSQL and other storage backends.

Public API exports only the interfaces needed by other contexts.
Credentials and implementation details remain private.
"""

from scout.contexts.storage.database import (
    DatabaseConfig,
    DatabaseWrapper,
)
from scout.contexts.storage.schema import (
    SchemaInspector,
    draw_db_tree,
)
from scout.contexts.storage.getter import (
    get_database_wrapper,
)

__all__ = [
    # Factory function (primary interface)
    "get_database_wrapper",
    # Generic interfaces
    "DatabaseWrapper",
    "DatabaseConfig",
    "SchemaInspector",
    # Utilities
    "draw_db_tree",
]


