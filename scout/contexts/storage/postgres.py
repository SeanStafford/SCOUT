"""
PostgreSQL-specific database operations for SCOUT.

Provides PostgreSQL-specific utilities:
- Database creation and existence checking
- PostgreSQL implementation of DatabaseWrapper
- Schema inspection via InformationSchema
"""

import psycopg2
from psycopg2 import sql
import numpy as np
import pandas as pd

from scout.contexts.storage.database import DatabaseWrapper as BaseDBWrapper
from scout.contexts.storage.config import get_postgres_credentials


class PostgreSQLWrapper(BaseDBWrapper):
    """
    PostgreSQL implementation of DatabaseWrapper.

    Provides connection management and common query patterns for PostgreSQL.
    """

    def __init__(
        self,
        name: str,
        host: str = None,
        user: str = None,
        port: int = None,
        password: str = None,
    ):
        super().__init__(name)

        # Get credentials from environment if not provided
        creds = get_postgres_credentials()
        self.host = host or creds["host"]
        self.user = user or creds["user"]
        self.port = port or creds["port"]
        self.password = password or creds["password"]

    def connect(self):
        """Create a new PostgreSQL database connection."""
        return psycopg2.connect(
            dbname=self.name,
            host=self.host,
            user=self.user,
            port=self.port,
            password=self.password,
        )

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


def db_exists(name: str) -> bool:
    """
    Check if a PostgreSQL database exists.

    Args:
        name: Database name to check

    Returns:
        True if database exists, False otherwise
    """
    creds = get_postgres_credentials()
    conn = psycopg2.connect(
        database="postgres",
        user=creds["user"],
        password=creds["password"],
        host=creds["host"],
        port=creds["port"],
    )
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (name,))
    fetched = cursor.fetchone()
    conn.close()
    return fetched is not None


def create_db(name: str) -> None:
    """
    Create a new PostgreSQL database.

    Args:
        name: Name of the database to create
    """
    creds = get_postgres_credentials()
    conn = psycopg2.connect(
        database="postgres",
        user=creds["user"],
        password=creds["password"],
        host=creds["host"],
        port=creds["port"],
    )

    conn.autocommit = True
    cursor = conn.cursor()

    sql_cmd = f" CREATE database {name} "
    cursor.execute(sql_cmd)
    print(f"Database named '{name}' created successfully")
    conn.close()


def draw_db_tree(tree, branch, last=True, header=""):
    """
    Recursively draw a tree visualization of database schema.

    Adapted from: https://stackoverflow.com/a/76691030
    """
    elbow = "└── "
    pipe = "│   "
    tee = "├── "
    blank = "    "
    print(header + (elbow if last else tee) + branch)
    assert type(tree) is np.ndarray
    if tree.shape[1] > 0:
        branches = np.unique(tree[:, 0])
        for i, branch in enumerate(branches):
            draw_db_tree(
                tree[np.where(tree[:, 0] == branch)][:, 1:],
                branch=branch,
                header=header + (blank if last else pipe),
                last=i == len(branches) - 1,
            )


class InformationSchema:
    """
    Utility for inspecting PostgreSQL database schema.

    Provides methods to list tables, columns, and visualize schema structure.
    """

    def __init__(self, database: PostgreSQLWrapper, table: str = None):
        self.database = database
        self.table = table

    def list_tables(self):
        """List all tables in the database."""
        conn = self.database.connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
        )
        tables = [table[0] for table in cur.fetchall()]
        conn.close()
        return tables

    def list_columns(self, table: str = None):
        """List all columns in a specific table."""
        tables = self.list_tables()
        if table is None:
            table = self.table
        assert table in tables, (
            f"To list columns, first select a table of interest from {tables}"
        )
        conn = self.database.connect()
        cur = conn.cursor()
        cur.execute(
            f"SELECT column_name FROM information_schema.columns where table_name='{table}'"
        )
        columns = [column[0] for column in cur.fetchall()]
        conn.close()
        return table, columns

    def tree(self, draw=True):
        """
        Generate a tree structure of database schema (tables and columns).

        Args:
            draw: If True, print the tree visualization. If False, just return data.

        Returns:
            List of [table, column] pairs
        """
        tree_out = []

        tables = self.list_tables()
        for table in tables:
            _, cols = self.list_columns(table)
            for col in cols:
                tree_out.append([table, col])
        if draw:
            assert len(tables), (
                "No tables exist. Cannot draw empty tree. Set draw=False to avoid this error."
            )
            draw_db_tree(np.array(tree_out), self.database.name)
        return tree_out


# Backward compatibility alias
DatabaseWrapper = PostgreSQLWrapper
