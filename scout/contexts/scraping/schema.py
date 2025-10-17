"""
Schema utilities for scrapers.

Scrapers own their data transformation. These utilities help scrapers
understand what the canonical schema expects, but scrapers decide
how to map their data to it.

This respects bounded contexts: Storage defines schema expectations,
Scraping decides how to meet them.
"""

import os
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from omegaconf import OmegaConf

# Load environment variables
load_dotenv()
CONFIG_PATH = Path(os.getenv("CONFIG_PATH"))


class CanonicalSchema:
    """
    Load and query the canonical data schema.

    Scrapers use this to understand what fields Storage context expects,
    but scrapers decide how to map their data to these expectations.
    """

    def __init__(self, schema_path: Path = CONFIG_PATH / "data_schema.yaml"):
        """
        Load schema from YAML file using OmegaConf.

        Args:
            schema_path: Path to canonical schema YAML file (default: from CONFIG_PATH env var)
        """
        self.schema = OmegaConf.load(schema_path)
        self.canonical = self.schema.canonical_schema

    def get_canonical_fields(self) -> List[str]:
        """
        Get list of all canonical field names.
        """
        return list(self.canonical.keys())

    def get_required_fields(self) -> List[str]:
        """
        Get list of required canonical fields.
        """
        return [name for name, spec in self.canonical.items() if spec.required]

    def get_optional_fields(self) -> List[str]:
        """
        Get list of optional canonical fields.
        """
        return [name for name, spec in self.canonical.items() if not spec.required]

    def get_df_column_names(self) -> Dict[str, str]:
        """
        Get mapping of canonical field names to DataFrame column names.

        Returns:
            Dict mapping field → DataFrame column name
        """
        return {name: spec.df_name for name, spec in self.canonical.items()}

    def get_db_column_names(self) -> Dict[str, str]:
        """
        Get mapping of canonical field names to database column names.

        Returns:
            Dict mapping field → database column name
        """
        return {name: spec.db_name for name, spec in self.canonical.items()}

    def get_field_info(self, field_name: str) -> Dict:
        """
        Get complete information for a canonical field.

        Args:
            field_name: Canonical field name (e.g., "title", "min_salary")

        Returns:
            Dict with field information:
            {
                'df_name': 'Title',
                'db_name': 'title',
                'type': 'VARCHAR(255)',
                'required': True,
                'default': None,
                'description': 'Job title or position name'
            }

        Raises:
            KeyError: If field_name not in canonical schema

        Example:
            >>> info = schema.get_field_info('min_salary')
            >>> print(f"Type: {info['type']}, Default: {info['default']}")
            Type: INTEGER, Default: 0
        """
        if field_name not in self.canonical:
            raise KeyError(
                f"Field '{field_name}' not in canonical schema. "
                f"Available fields: {list(self.canonical.keys())}"
            )
        return dict(self.canonical[field_name])
