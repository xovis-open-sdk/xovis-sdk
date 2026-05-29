"""
Xovis SDK - Control Plane Exceptions
Defines the custom exception hierarchy for the Xovis API engine.
"""
from typing import Any, Optional


class XovisAPIError(Exception):
    """Base exception for all Xovis SDK API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        base = super().__str__()
        if self.status_code:
            base = f"[HTTP {self.status_code}] {base}"
        if self.response_body:
            base += f" | Details: {self.response_body}"
        return base


class XovisAuthError(XovisAPIError):
    """Raised when authentication fails (HTTP 401/403) or token acquisition fails."""
    pass


class RateLimitError(XovisAPIError):
    """Raised when the API rate limit is exceeded (HTTP 429)."""
    pass


class XovisClientError(XovisAPIError):
    """Raised when the client sends a bad request (HTTP 400-499, excluding 401, 403, 429)."""
    pass


class XovisServerError(XovisAPIError):
    """Raised when the Xovis sensor or HUB encounters an internal error (HTTP 500-599)."""
    pass


class XovisConnectionError(XovisAPIError):
    """Raised when the underlying network connection fails (DNS, Socket timeouts, etc)."""
    pass