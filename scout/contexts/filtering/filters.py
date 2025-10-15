"""
Job listing filtering and analysis functions.
Provides functions to filter job listings based on various criteria.
"""

import re
import time
import requests
import pandas as pd

from scout.utils.text_processing import check_keyword_between_delimiters
from scout.contexts.filtering.events import log_inactive_event


def check_active(df: pd.DataFrame, url_column: str = "url", status_column: str = "Status") -> pd.DataFrame:
    """
    Check if job listing URLs are still active and log status changes.

    Inspired by the broadcast-subscribe pattern. This acts like the producer side:
    - Checks URL validity
    - Logs events when status changes
    - Does not update database

    Args:
        df: DataFrame containing job listings
        url_column: Name of column containing URLs to check (default: "url")
        status_column: Name of column with current status (expected: "Status")

    Returns:
        DataFrame with new "Inactive" boolean column added
    """
    inactives = []
    has_status_column = status_column in df.columns

    for _, row in df.iterrows():
        url = row[url_column]

        # If column doesn't exist, assumes a status of 'unknown'
        old_status = row[status_column] if has_status_column else 'unknown'

        try:
            resp = requests.get(url, timeout=10)

            # Check for link-level issues that indicate the listing is inactive
            # e.g. 404 meants the link doesn't exist
            if 400 <= resp.status_code < 500 or url != resp.url:
                new_status = 'inactive'
            elif 200 <= resp.status_code < 300:
                new_status = 'active'
            else:
                new_status = 'unknown'               
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.RequestException):
            # Network-level issues or ambiguous issues
            new_status = 'unknown'

        if new_status != old_status:
            log_inactive_event(url, old_status, new_status)
        
        inactive_status_bool_map = {"active": False, "inactive": True, "unknown": None}
        inactives.append(inactive_status_bool_map[new_status])

        time.sleep(0.5)  # Be "polite"

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
    # Work with a copy to avoid SettingWithCopyWarning
    df = df.copy()

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
