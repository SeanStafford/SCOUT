"""
Shared utility functions.
"""

from scout.utils.helpers import flatten_dict
from scout.utils.text_processing import (
    check_keyword_between_delimiters,
    truncate_between_substrings,
    clean_html_for_markdown,
    clean_after_markdown,
)

__all__ = [
    # Dictionary utilities
    "flatten_dict",
    # Text processing
    "check_keyword_between_delimiters",
    "truncate_between_substrings",
    "clean_html_for_markdown",
    "clean_after_markdown",
]
