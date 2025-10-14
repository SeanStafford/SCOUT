
"""
Job listing filtering and analysis functions.
Provides functions to filter job listings based on various criteria.
"""

import re
import time
import requests
import pandas as pd

from scout.utils.text_processing import check_keyword_between_delimiters


def check_active(df: pd.DataFrame, url_column: str = "url") -> pd.DataFrame:
    """
    Check if job listing URLs are still active. Currently, a URL is considered inactive if it redirects to a different URL.

    Args:
        df: DataFrame containing job listings
        url_column: Name of column containing URLs to check (default: "url")

    Returns:
        DataFrame with new "Inactive" boolean column added
    """
    inactives = []
    for url in df[url_column].to_list():
        try:
            resp = requests.get(url, timeout=10)
            # If URL redirected, consider it inactive
            active = url == resp.url
            inactives.append(not active)
        except requests.RequestException:
            # If request fails, consider inactive
            inactives.append(True)
        time.sleep(0.5)  # Be polite to servers

    df["Inactive"] = inactives
    return df


def check_column_red_flags(
    df: pd.DataFrame,
    red_flags: list,
    column: str,
    output_column: str = None
) -> pd.DataFrame:
    """
    Check any column for undesirable keywords (generic red flag filter).

    Args:
        df: DataFrame containing job listings
        red_flags: List of keywords to flag (e.g., ["Manager",])
        column: Name of column to check for red flags (e.g., "Job Title")
        output_column: Name of output boolean column (default: "{column}_OK")

    Returns:
        DataFrame with new boolean column (True if no red flags found)
    """

    if output_column is None:
        # Sanitize column name for output (remove spaces, special chars)
        sanitized_column = column.replace(" ", "_").replace("-", "_")
        output_column = f"{sanitized_column}_OK"

    red_flag_bool_col = []

    for _, row in df.iterrows():
        has_red_flag = any(flag in row[column] for flag in red_flags)
        red_flag_bool_col.append(not has_red_flag)

    df[output_column] = red_flag_bool_col
    return df


def check_red_flags(df: pd.DataFrame, red_flags: list, description_column: str = "Description") -> pd.DataFrame:
    """
    Check job descriptions for undesireable keywords.

    DEPRECATED: Use check_column_red_flags() instead for more flexibility.

    Args:
        df: DataFrame containing job listings
        red_flags: List of keywords to flag
        description_column: Name of column containing job descriptions (default: "Description")

    Returns:
        DataFrame with new boolean column (True if no red flag keywords found)
    """
    return check_column_red_flags(
        df,
        red_flags=red_flags,
        column=description_column,
        output_column="Description_OK"
    )


def check_clearance_req(
    df: pd.DataFrame,
    description_column: str = "Description",
    start_delimiter: str = "You Have",
    end_delimiter: str = "Nice If You Have",
) -> pd.DataFrame:
    """
    Check if cearance is a required qualification (not robustly implemented yet)
    """
    clearance_required_list = []

    for i, row in df.iterrows():
        clearance_required = check_keyword_between_delimiters(
            row[description_column],
            "clearance",  # Case-insensitive search (regex uses re.IGNORECASE)
            start_delimiter,
            end_delimiter,
        )
        clearance_required_list.append(clearance_required)

    df["Clearance Required"] = clearance_required_list
    return df


def check_title_red_flags(
    df: pd.DataFrame,
    red_flags: list,
    title_column: str = "Job Title",
) -> pd.DataFrame:
    """
    Check job titles for undesirable keywords.

    DEPRECATED: Use check_column_red_flags() instead for more flexibility.

    Args:
        red_flags: List of keywords to flag (e.g., ["Manager",])
        df: DataFrame containing job listings
        title_column: Name of column containing job titles (default: "Job Title")

    Returns:
        DataFrame with new "Title_OK" boolean column (True if no red flags found)
    """
    return check_column_red_flags(
        df,
        red_flags=red_flags,
        column=title_column,
        output_column="Title_OK"
    )
