
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


def check_red_flags(red_flags: list, df: pd.DataFrame, description_column: str = "Description") -> pd.DataFrame:
    """
    Check job descriptions for undesireable keywords.

    Args:
        df: DataFrame containing job listings
        description_column: Name of column containing job descriptions (default: "Description")

    Returns:
        DataFrame with new "No_Red_Flags" boolean column (True if no red flag keywords found)
    """
    no_red_flags = []

    for _, row in df.iterrows():
        is_red_flag = False
        for red_flag_kw in red_flags:
            if red_flag_kw in row[description_column]:
                is_red_flag = True
                break
        no_red_flags.append(not is_red_flag)

    df["No_Red_Flags"] = no_red_flags
    return df


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
    red_flags: list,
    df: pd.DataFrame,
    title_column: str = "Job Title",
) -> pd.DataFrame:
    """
    Check job titles for undesirable keywords.

    Args:
        red_flags: List of keywords to flag (e.g., ["Manager",])
        df: DataFrame containing job listings
        title_column: Name of column containing job titles (default: "Job Title")

    Returns:
        DataFrame with new "Title_OK" boolean column (True if no red flags found)
    """
    no_red_flags = []

    for _, row in df.iterrows():
        has_red_flag = any(flag in row[title_column] for flag in red_flags)
        no_red_flags.append(not has_red_flag)

    df["Title_OK"] = no_red_flags
    return df
