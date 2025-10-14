"""
Job filtering domain.

Handles filtering and analysis of scraped job listings based on various criteria.
"""

from scout.contexts.filtering.filters import (
    check_active,
    check_clearance_req,
    check_column_red_flags,
    check_red_flags,  # Deprecated, kept for backward compatibility
    check_title_red_flags,  # Deprecated, kept for backward compatibility
)
from scout.contexts.filtering.pipeline import FilterPipeline

__all__ = [
    "check_active",
    "check_clearance_req",
    "check_column_red_flags",
    "check_red_flags",  # Deprecated
    "check_title_red_flags",  # Deprecated
    "FilterPipeline",
]
