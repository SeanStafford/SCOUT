"""
Database-agnostic schema inspection and visualization utilities.

Provides abstract interfaces and utilities that work with any SQL database.
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import List, Tuple

from scout.contexts.storage.database import DatabaseWrapper


def draw_db_tree(tree, branch, last=True, header=""):
    """
    Recursively draw a tree visualization of database schema.

    Works with any numpy array of [table, column] pairs.
    Database-agnostic - pure visualization logic.

    Adapted from: https://stackoverflow.com/a/76691030

    Args:
        tree: Numpy array of [table, column] pairs
        branch: Current branch name to draw
        last: Whether this is the last branch at current level
        header: Accumulated header string for indentation
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


class SchemaInspector(ABC):
    """
    Abstract base class for database schema inspection.

    Different database systems implement information_schema differently,
    but the logic for organizing and visualizing schema is the same.
    """

    def __init__(self, database: DatabaseWrapper, table: str = None):
        """
        Initialize schema inspector.

        Args:
            database: DatabaseWrapper instance
            table: Optional default table name for operations
        """
        self.database = database
        self.table = table

    @abstractmethod
    def list_tables(self) -> List[str]:
        """
        List all tables in the database.

        Returns:
            List of table names
        """
        pass

    @abstractmethod
    def list_columns(self, table: str = None) -> Tuple[str, List[str]]:
        """
        List all columns in a specific table.

        Args:
            table: Table name (uses self.table if None)

        Returns:
            Tuple of (table_name, list_of_column_names)
        """
        pass

    def tree(self, draw=True):
        """
        Generate a tree structure of database schema (tables and columns).

        This method is database-agnostic - only the queries in list_tables()
        and list_columns() need to be implemented per database.

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
            draw_db_tree(np.array(tree_out), self.database.config.name)

        return tree_out
