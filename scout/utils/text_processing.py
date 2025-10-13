"""
Text processing utilities for SCOUT.

Contains soem functions for parsing/cleaning text that I have found useful.
"""

import re


def check_keyword_between_delimiters(
    text: str, keyword: str, start_delimiter: str, end_delimiter: str
) -> bool:
    """
    Check if keyword appears between start_delimiter and end_delimiter in text.

    Args:
        text: The multi-line string to search
        keyword: The keyword to find (e.g., "Javascript")
        start_delimiter: The starting delimiter (e.g., "Basic Qualifications")
        end_delimiter: The ending delimiter (e.g., "Preferred Qualifications")

    Returns:
        True if keyword is found between delimiters, False otherwise
    """
    # Build regex pattern that captures text between delimiters
    # (?s) enables DOTALL mode so . matches newlines
    # .*? is non-greedy matching
    pattern = f"(?s){re.escape(start_delimiter)}(.*?){re.escape(end_delimiter)}"

    # Find the match
    match = re.search(pattern, text)

    if match:
        # Check if keyword exists in the captured group (between delimiters)
        between_text = match.group(1)
        # Case-insensitive search for keyword
        return re.search(keyword, between_text, re.IGNORECASE) is not None

    return False


def truncate_between_substrings(
    text: str, start_substr: str, end_substr: str
) -> str:
    """
    Truncate string after the last occurrence of start_substr and before
    the first occurrence of end_substr that follows it.

    Args:
        text: The string to truncate
        start_substr: The substring to find the last occurrence of
        end_substr: The substring to find the first occurrence of after start

    Returns:
        The truncated string, or original if substrings not found

    Example:
        >>> text = "Header\\nContent here\\nFooter"
        >>> truncate_between_substrings(text, "Header", "Footer")
        "\\nContent here\\n"
    """
    result = text

    # Find the last occurrence of start_substr
    start_index = result.rfind(start_substr)
    if start_index != -1:
        # Truncate from after the start_substr
        result = result[start_index + len(start_substr) :]

    # Find the first occurrence of end_substr (in the truncated text)
    end_index = result.find(end_substr)
    if end_index != -1:
        # Truncate before the end_substr
        result = result[:end_index]

    return result


def clean_html_for_markdown(html_string: str) -> str:
    """
    Clean problematic HTML patterns before markdownify conversion.

    Standardizes various BR tag formats to ensure consistent markdown output.

    Args:
        html_string: HTML string to clean

    Returns:
        Cleaned HTML string, or empty string if input is None/empty
    """
    if not html_string:
        return ""

    # Fix mixed BR tag formats - standardize to <br>
    html_string = html_string.replace("<br />", "<br>")
    html_string = html_string.replace("<br/>", "<br>")

    return html_string


def clean_after_markdown(markdown_text: str) -> str:
    """
    Remove excessive H3 headers from markdown text.

    If more than 50% of lines start with ###, removes the ### prefix from all lines.
    This handles cases where markdown conversion over-uses header formatting.

    Args:
        markdown_text: Markdown string to clean

    Returns:
        Cleaned markdown string with excessive headers removed
    """
    lines = markdown_text.split("\n")
    h3_lines = sum(1 for line in lines if line.strip().startswith("###"))

    if h3_lines > len(lines) * 0.5:  # More than half are H3
        # Remove the ### prefix from all lines
        return "\n".join(
            line[4:] if line.startswith("### ") else line for line in lines
        )
    return markdown_text
