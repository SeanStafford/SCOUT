"""
Generic database wrapper for SCOUT.

Provides database-agnostic interfaces that can work with any SQL database backend.
"""

import os
import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
DATABASE_BACKEND = os.getenv("DATABASE_BACKEND")


@dataclass
class DatabaseConfig:
    """Generic database connection configuration."""

    host: str
    port: int
    user: str
    password: str
    name: str
    table: str = "listings"

    # def __post_init__(self):
    #     if not self.name:
    #         raise ValueError("Database name is required")
        
    @classmethod
    def from_env(cls, name: str, table: str = "listings"):
        """Create DatabaseConfig from environment variables."""

        db_env_setting_keys = ["port", "user", "password", "host"]

        db_settings = {setting: os.getenv(f"POSTGRES_{setting.upper()}") for setting in db_env_setting_keys}

        # Cast port to int
        db_settings["port"] = int(db_settings["port"])

        return cls(name=name, table=table, **db_settings)

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class DatabaseWrapper(ABC):
    """
    Abstract base class for database operations.

    Provides a common interface for different database backends (PostgreSQL, MySQL, etc.)
    """

    def __init__(self, config: DatabaseConfig):
        """
        Initialize database wrapper.

        Args:
            config: Database config
        """
        self.config = config

    @abstractmethod
    def connect(self):
        """Create and return a database connection."""
        pass

    @abstractmethod
    def _query(self, query):
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

    @staticmethod
    @abstractmethod
    def _db_exists(config: DatabaseConfig) -> bool:
        """
        Check if a database exists.

        Args:
            config: DatabaseConfig with connection details

        Returns:
            True if database exists, False otherwise
        """
        pass

    @staticmethod
    @abstractmethod
    def _create_db(config: DatabaseConfig) -> None:
        pass

    @classmethod
    def from_config(cls, config: DatabaseConfig, ensure_exists: bool = False):
        if ensure_exists and not cls._db_exists(config):
            cls._create_db(config)
        return cls(config)

