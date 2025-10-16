"""
Text processing utilities for SCOUT.

Contains soem functions for parsing/cleaning text that I have found useful.
"""

from dataclasses import dataclass
from typing import Iterable, Iterator, Pattern, Union

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


@dataclass(frozen=True)
class RegexSnippet:
    """Container for a regex match snippet with surrounding context."""

    source_index: int
    start: int
    end: int
    snippet: str


def iter_regex_snippets(
    pattern: Union[str, Pattern[str]],
    text_or_texts: Union[str, Iterable[str]],
    *,
    context: int = 20,
    merge_overlaps: bool = True,
    flags: int = 0,
    normalize_whitespace: bool = True,
) -> Iterator[RegexSnippet]:
    """Yield snippets surrounding regex matches across one or many strings.

    Args:
        pattern: Regex pattern string or compiled Pattern.
        text_or_texts: Single string or iterable of strings to search.
        context: Number of characters of context on each side of a match.
        merge_overlaps: Merge overlapping context windows when True.
        flags: Optional re module flags when compiling string patterns.
        normalize_whitespace: Replace newlines with spaces in snippets when True.

    Yields:
        RegexSnippet instances describing each context window.
    """

    if context < 0:
        raise ValueError("context must be non-negative")

    # Handle both string patterns and pre-compiled regex objects
    compiled: Pattern[str]
    if isinstance(pattern, str):
        compiled = re.compile(pattern, flags)
    else:
        # Pattern already compiled; flags parameter is ignored in this case
        compiled = pattern

    # Normalize input to iterable: wrap single string in tuple for uniform processing
    if isinstance(text_or_texts, str):
        texts: Iterable[str] = (text_or_texts,)
    else:
        texts = text_or_texts

    # Process each text independently, tracking source index for multi-document searches
    for idx, text in enumerate(texts):
        if not text:
            continue

        # Collect all match spans with context for this text
        spans = []
        for match in compiled.finditer(text):
            # Expand match boundaries by context chars, clamped to text boundaries
            span_start = max(0, match.start() - context)
            span_end = min(len(text), match.end() + context)
            spans.append((span_start, span_end))

        if not spans:
            continue

        # Merge overlapping spans to avoid redundant/overlapping snippets
        if merge_overlaps:
            spans.sort()  # Sort by start position for linear merge algorithm
            merged_spans = []
            for span_start, span_end in spans:
                # Check if current span overlaps with the last merged span
                # (span_start > merged_spans[-1][1] means no overlap)
                if not merged_spans or span_start > merged_spans[-1][1]:
                    # No overlap: start new merged span (mutable list for end extension)
                    merged_spans.append([span_start, span_end])
                else:
                    # Overlap: extend the last merged span's end to include current span
                    merged_spans[-1][1] = max(merged_spans[-1][1], span_end)
        else:
            # Keep all spans separate even if they overlap
            merged_spans = spans

        # Yield snippets for all (merged or unmerged) spans
        for span_start, span_end in merged_spans:
            snippet_text = text[span_start:span_end]
            if normalize_whitespace:
                # Convert newlines to spaces for cleaner single-line display
                snippet_text = snippet_text.replace("\n", " ")
            yield RegexSnippet(
                source_index=idx,
                start=span_start,
                end=span_end,
                snippet=snippet_text,
            )
