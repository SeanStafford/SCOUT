"""
Generic database wrapper for SCOUT.

Provides database-agnostic interfaces that can work with any SQL database backend.
"""

import pandas as pd
from abc import ABC, abstractmethod


class DatabaseWrapper(ABC):
    """
    Abstract base class for database operations.

    Provides a common interface for different database backends (PostgreSQL, MySQL, etc.)
    """

    def __init__(self, name: str):
        """
        Initialize database wrapper.

        Args:
            name: Database name
        """
        self.name = name

    @abstractmethod
    def connect(self):
        """Create and return a database connection."""
        pass

    @abstractmethod
    def get_column_values(self, table_name: str, column_name: str) -> list:
        """
        Get all values from a specific column in a table.

        Args:
            table_name: Name of the table
            column_name: Name of the column

        Returns:
            List of column values
        """
        pass

    @abstractmethod
    def export_df(self, query: str = None) -> pd.DataFrame:
        """
        Execute a query and return results as a pandas DataFrame.

        Args:
            query: SQL query string (default: SELECT * from listings)

        Returns:
            DataFrame with query results
        """
        pass
