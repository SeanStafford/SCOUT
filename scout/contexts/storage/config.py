"""
Database configuration for SCOUT storage context.

Handles loading credentials from environment and creating connection configurations.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _get_required_env(key: str) -> str:
    """Get required environment variable or raise clear error."""
    try:
        return os.environ[key]
    except KeyError:
        raise EnvironmentError(
            f"Required environment variable '{key}' not found. "
            f"Ensure .env file exists and contains {key}."
        )


# Load database credentials from environment (private to this module)
_POSTGRES_HOST = _get_required_env("POSTGRES_HOST")
_POSTGRES_PORT = int(_get_required_env("POSTGRES_PORT"))
_POSTGRES_USER = _get_required_env("POSTGRES_USER")
_POSTGRES_PASSWORD = _get_required_env("POSTGRES_PASSWORD")


@dataclass
class DatabaseConfig:
    """Generic database connection configuration."""

    host: str
    port: int
    user: str
    password: str
    name: str
    table: str = "listings"

    def __post_init__(self):
        if not self.name:
            raise ValueError("Database name is required")

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


def get_postgres_credentials() -> dict:
    """
    Get PostgreSQL credentials from environment.

    Returns:
        Dictionary with host, port, user, password
    """
    return {
        "host": _POSTGRES_HOST,
        "port": _POSTGRES_PORT,
        "user": _POSTGRES_USER,
        "password": _POSTGRES_PASSWORD,
    }


def create_database_config(database_name: str, table: str = "listings") -> DatabaseConfig:
    """
    Create a DatabaseConfig using environment credentials.

    Args:
        database_name: Name of the database
        table: Name of the table (default: "listings")

    Returns:
        DatabaseConfig instance
    """
    creds = get_postgres_credentials()
    return DatabaseConfig(
        host=creds["host"],
        port=creds["port"],
        user=creds["user"],
        password=creds["password"],
        name=database_name,
        table=table,
    )
