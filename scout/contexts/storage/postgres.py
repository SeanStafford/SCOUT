"""
PostgreSQL-specific database operations for SCOUT.

Provides PostgreSQL-specific utilities:
- Database creation and existence checking
- PostgreSQL implementation of DatabaseWrapper
- PostgreSQL implementation of SchemaInspector
"""

import psycopg2
from psycopg2 import sql
import pandas as pd
from typing import List, Tuple

from scout.contexts.storage.database import DatabaseWrapper as BaseDBWrapper, DatabaseConfig
from scout.contexts.storage.schema import SchemaInspector


def postgres_connect(config: DatabaseConfig, name: str = None, host: str = None, user: str = None, port: int = None, password: str = None):
    """Create a new PostgreSQL database connection. Override config parameters if provided."""
    return psycopg2.connect(
        dbname=name if name is not None else config.name,
        host=host if host is not None else config.host,
        user=user if user is not None else config.user,
        port=port if port is not None else config.port,
        password=password if password is not None else config.password,
    )


class PostgreSQLWrapper(BaseDBWrapper):
    """
    PostgreSQL implementation of DatabaseWrapper.

    Provides connection management and common query patterns for PostgreSQL.
    """

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)

    def connect(self):
        """Create a new PostgreSQL database connection."""
        return postgres_connect(self.config)

    def _query(self, query):
        """Execute a query and return first column values."""
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(query)
        values = cur.fetchall()
        cur.close()
        conn.close()
        return [val[0] for val in values]

    def get_column_values(self, table_name: str, column_name: str) -> list:
        """Get all values from a specific column in a table."""
        all_values_query = sql.SQL("SELECT {} FROM {};").format(
            sql.Identifier(column_name), sql.Identifier(table_name)
        )
        return self._query(all_values_query)

    def export_df(self, query: str = None) -> pd.DataFrame:
        """Execute a query and return results as a pandas DataFrame."""
        conn = self.connect()
        query = query if query is not None else "SELECT * from listings"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    @staticmethod
    def _db_exists(config: DatabaseConfig) -> bool:
        """
        Check if a PostgreSQL database exists.

        Uses PostgreSQL system catalog pg_database.

        Args:
            config: DatabaseConfig with connection details

        Returns:
            True if database exists, False otherwise
        """
        conn = postgres_connect(config, name="postgres")
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (config.name,))
        fetched = cursor.fetchone()
        conn.close()
        return fetched is not None

    @staticmethod
    def _create_db(config: DatabaseConfig) -> None:
        """
        Create a new PostgreSQL database (private helper).

        Args:
            config: DatabaseConfig with connection details and database name
        """
        conn = postgres_connect(config, name="postgres")
        conn.autocommit = True
        cursor = conn.cursor()

        sql_cmd = f" CREATE database {config.name} "
        cursor.execute(sql_cmd)
        print(f"Database named '{config.name}' created successfully")
        conn.close()


class PostgreSQLSchemaInspector(SchemaInspector):
    """
    PostgreSQL implementation of schema inspection.

    Uses PostgreSQL's information_schema to query table and column metadata.
    """

    def list_tables(self) -> List[str]:
        """List all tables in the database using PostgreSQL information_schema."""
        conn = self.database.connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
        )
        tables = [table[0] for table in cur.fetchall()]
        conn.close()
        return tables

    def list_columns(self, table: str = None) -> Tuple[str, List[str]]:
        """List all columns in a specific table using PostgreSQL information_schema."""
        tables = self.list_tables()
        if table is None:
            table = self.table
        assert table in tables, (
            f"To list columns, first select a table of interest from {tables}"
        )
        conn = self.database.connect()
        cur = conn.cursor()
        cur.execute(
            f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'"
        )
        columns = [column[0] for column in cur.fetchall()]
        conn.close()
        return table, columns

