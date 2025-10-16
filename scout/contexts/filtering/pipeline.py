"""
Job filtering pipeline with configuration support.

Provides FilterPipeline class for consolidated filtering controlled by YAML config.
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Union

import pandas as pd
from dotenv import load_dotenv
from omegaconf import OmegaConf
from omegaconf.dictconfig import DictConfig

from scout.contexts.filtering.filters import (
    check_active,
    check_clearance_req,
    check_column_red_flags,
)

load_dotenv()
filter_config = Path(os.getenv("filter_config"))

class FilterPipeline:
    """
    Unified job filtering pipeline controlled by configuration file.

    Applies filters sequentially with progress reporting at each step.
    Combines SQL-based filtering (fast, database-side) with pandas-based
    filtering (flexible, memory-side).
    """

    def __init__(self, filter_config: Union[Path, str, DictConfig] = filter_config / "filters.yaml"):
        """
        Initialize pipeline with configuration.

        Args:
            filter_config: Either a path to YAML config file or a DictConfig object.

        Raises:
            TypeError: If filter_config is not Path, str, or DictConfig

        Examples:
            >>> from scout.utils.config_helpers import merge_configs
            >>> config = merge_configs(["config/default.yaml", "config/test.yaml"])
            >>> pipeline = FilterPipeline(config)

            >>> # Altertnative simpler usage
            >>> pipeline = FilterPipeline("config/default.yaml")
        """
        if isinstance(filter_config, (Path, str)):
            self.config = OmegaConf.load(filter_config)
        elif isinstance(filter_config, DictConfig):
            self.config = filter_config
        else:
            raise TypeError(
                f"filter_config must be Path, str, or DictConfig, got {type(filter_config)}"
            )

    def build_sql_query(self, table_name: str = "listings") -> str:
        """
        Generate SQL WHERE clause from configuration.

        Args:
            table_name: Name of database table to query

        Returns:
            Complete SQL SELECT query with WHERE conditions
        """
        sql_config = self.config.sql_filters

        conditions = []

        # Salary filter
        if sql_config.min_salary: # No filter if 0 is used
            conditions.append(
                f"( max_salary >= {sql_config.min_salary} OR max_salary = 0 )"
            )

        # Date filter
        if sql_config.max_age_days: # No filter if 0 is used
            cutoff_date = (datetime.today() - timedelta(days=sql_config.max_age_days)).date()
            conditions.append(f"( date_posted >= '{cutoff_date}' )")

        # Location filter (state codes OR remote)
        if sql_config.onsite_locations or sql_config.remote or sql_config.hybrid_locations:
            location_conditions = []

            if sql_config.onsite_locations:
                onsite_clause = " OR ".join([f"location LIKE '%{loc}%'" for loc in sql_config.onsite_locations])
                location_conditions.append(f" ( {onsite_clause} ) ")

            if sql_config.hybrid_locations:
                hybrid_clause = " OR ".join([f"location LIKE '%{loc}%'" for loc in sql_config.hybrid_locations])
                hybrid_clause = f"( {hybrid_clause} ) AND remote = 'Hybrid'"
                location_conditions.append(f" ( {hybrid_clause} ) ")

            if sql_config.remote:
                location_conditions.append("( remote = 'Yes' )")

            # Combine with OR
            location_clause = " OR ".join(location_conditions)
            conditions.append(f"( {location_clause} )")

        # Status filter
        if sql_config.get("status_filter", False):
            conditions.append(
                f"(status = '{sql_config.status_filter}' OR status IS NULL)"
            )

        # Build complete query
        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        return query

    def apply_filters(self, df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
        """
        Apply all configured filters to DataFrame sequentially.

        Args:
            df: DataFrame to filter
            verbose: If True, print progress after each filter step

        Returns:
            Filtered DataFrame
        """
        initial_count = len(df)

        if verbose:
            print(f"Starting with {initial_count} jobs")

        # Keyword filters
        if self.config.keyword_filters.required_keywords:
            keywords = self.config.keyword_filters.required_keywords
            desc_col = self.config.keyword_filters.description_column

            keyword_pattern = "|".join(keywords)
            white_list_mask = df[desc_col].str.contains(keyword_pattern, case=False, na=False)
            df = df[white_list_mask]

            if verbose:
                print(f"After keyword filtering: {len(df)} jobs")

        # Red flag filtering (generic, applies to any column)
        if hasattr(self.config, 'red_flags') and self.config.red_flags:
            for filter_config in self.config.red_flags:
                column = filter_config.column
                flags = filter_config.flags

                if filter_config.get('bool_out_column'):
                    output_col = filter_config.bool_out_column
                else:
                    # Output column name is auto-generated as {column}_OK
                    sanitized_column = column.replace(" ", "_").replace("-", "_")
                    output_col = f"{sanitized_column}_OK"

                df = check_column_red_flags(
                    df,
                    red_flags=flags,
                    column=column,
                    output_column=output_col
                )

                df = df[df[output_col]]

                if verbose:
                    print(f"After '{column}' red flag filtering: {len(df)} jobs")

        # Clearance requirement
        if self.config.get("clearance", False):
            clearance_config = self.config.clearance
            if clearance_config.exclude_required:
                df = check_clearance_req(
                    df,
                    description_column=clearance_config.description_column,
                    start_delimiter=clearance_config.start_delimiter,
                    end_delimiter=clearance_config.end_delimiter,
                )
                df = df[~df["Clearance Required"]]

                if verbose:
                    print(f"After clearance filtering: {len(df)} jobs")

        # Active URL check (slow, optional)
        active_config = self.config.active_check
        if active_config.enabled:
            df = check_active(df, url_column=active_config.url_column)
            df = df[~df["Inactive"]]

            if verbose:
                print(f"After activity check: {len(df)} jobs")

        if verbose:
            filtered_count = initial_count - len(df)
            print(f"\nFiltered out {filtered_count} jobs ({filtered_count/initial_count*100:.1f}%)")

        return df
