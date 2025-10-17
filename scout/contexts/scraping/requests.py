"""HTTP helpers shared by scraping contexts."""

from typing import Optional

import requests
import time

PermanentCodeSet = (401, 403, 404, 410)
TransientCodeSet = (408, 425, 429, 500, 502, 503, 504) 

PermanentErrorTypes = (requests.exceptions.InvalidURL, requests.exceptions.TooManyRedirects)

LINK_GOOD = "success"
LINK_BAD = "failure"
LINK_UNKNOWN = "transient failure"

def classify_http_outcome(
    url: str,
    exception: Optional[requests.RequestException] = None,
    response: Optional[requests.Response] = None,
) -> str:
    if response is None and exception is not None:
        response = getattr(exception, "response", None)

    if response is not None: # We received a response object.
        status = response.status_code
        response_success_condition = (200 <= status < 300)
        response_failure_condition = (
            response.url.rstrip("/") != url.rstrip("/") or
            status in PermanentCodeSet
        )

        if response_success_condition:
            return LINK_GOOD
        elif response_failure_condition:
            return LINK_BAD
        else:
            return LINK_UNKNOWN

    elif exception is not None: # We didn't receive a response object, but we did receive an exception.
        if isinstance(exception, PermanentErrorTypes):
            return LINK_BAD
        else:
            return LINK_UNKNOWN
    else:
        # We received nothing. We know nothing about the link.
        return LINK_UNKNOWN

def html_request_with_retry(url, method="GET", max_attempts=3, delay=1.0, **kwargs):
    """
    Make an HTTP request with automatic retry on failure.

    Args:
        url (str): The URL to request
        method (str): HTTP method - either 'GET' or 'POST' (default: 'GET')
        max_attempts (int): How many times to try the request (default: 3)
        delay (float): Initial delay in seconds between retries (default: 1.0)
        **kwargs: Any additional arguments to pass to requests.get() or requests.post()

    Returns:
        requests.Response: The response object from successful request

    Raises:
        requests.RequestException: If all retry attempts fail
    """
    most_recent_exception = None

    for attempt in range(max_attempts):
        try:
            if method == "GET":
                response = requests.get(url, **kwargs)
            elif method == "POST":
                response = requests.post(url, **kwargs)
            response.raise_for_status()
            return response

        except requests.RequestException as e:
            most_recent_exception = e

            if attempt < max_attempts - 1:
                wait_time = delay * (2**attempt)
                print(f"Request failed, retrying in {wait_time}s...")
                time.sleep(wait_time)

    raise most_recent_exception


class NetworkCircuitBreakerException(Exception):
    pass


class URLFetcher:
    def __init__(self, max_consecutive_failures=5, request_delay=1.0, max_retries=3):
        self.max_consecutive_failures = max_consecutive_failures
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.consecutive_failures = 0

    def fetch(self, url, method="GET", **kwargs):
        """
        Fetch URL with retry, classification, and circuit breaking.

        Returns:
            tuple: (response or None, classification string, error_msg or None)

        Raises:
            NetworkCircuitBreakerException: If consecutive transient failures exceed threshold
        """
        error_msg = None

        try:
            response = html_request_with_retry(
                url,
                method=method,
                max_attempts=self.max_retries,
                delay=self.request_delay,
                **kwargs
            )
            classification = classify_http_outcome(url, response=response)
        except requests.RequestException as e:
            classification = classify_http_outcome(url, exception=e)
            response = None
            error_msg = str(e)

        if classification == LINK_UNKNOWN:
            self.consecutive_failures += 1

            if self.consecutive_failures >= self.max_consecutive_failures:
                raise NetworkCircuitBreakerException(
                    f"Circuit breaker: {self.consecutive_failures} consecutive transient failures"
                )
        else:
            self.consecutive_failures = 0

        return response, classification, error_msg 