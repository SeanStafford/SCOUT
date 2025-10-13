"""
Job filtering domain.

Handles filtering and analysis of scraped job listings based on various criteria.
"""

from scout.contexts.filtering.filters import (
    check_active,
    check_red_flags,
    check_clearance_req,
    check_title_red_flags,
)

__all__ = [
    "check_active",
    "check_red_flags",
    "check_clearance_req",
    "check_title_red_flags",
]
