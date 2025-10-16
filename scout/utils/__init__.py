"""
Shared utility functions.
"""

from scout.utils.config_helpers import merge_configs
from scout.utils.helpers import flatten_dict, relative_to_project
from scout.utils.text_processing import (
    check_keyword_between_delimiters,
    truncate_between_substrings,
    clean_html_for_markdown,
    clean_after_markdown,
)

__all__ = [
    # Misc utilities
    "relative_to_project",
    "flatten_dict",
    # Text processing
    "check_keyword_between_delimiters",
    "truncate_between_substrings",
    "clean_html_for_markdown",
    "clean_after_markdown",
    # Configuration utilities
    "merge_configs",
]
