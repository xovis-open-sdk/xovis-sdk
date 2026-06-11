"""
Xovis SDK - Control Plane Exceptions

This module defines the custom exception hierarchy for the Xovis SDK API engine.
It categorizes errors into authentication, rate-limiting, client-side,
server-side, and connectivity issues to provide precise error handling
across the Control and State & Topology Planes.
"""

from typing import Any, Optional


class XovisAPIError(Exception):
    """
    Base exception for all Xovis SDK API errors.

    Args:
        message (str): A descriptive error message.
        status_code (Optional[int], optional): The HTTP status code associated with the error.
        response_body (Any, optional): The raw response body from the server.
    """

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Any = None):
        """
        Initializes the Xovis API error.

        Args:
            message (str): A descriptive error message.
            status_code (Optional[int]): The HTTP status code associated with the error.
            response_body (Any): The raw response body from the server.
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        """
        Returns a formatted string representation of the error.

        Returns:
            str: The formatted error message including status code and details if available.
        """
        base = super().__str__()
        if self.status_code:
            base = f"[HTTP {self.status_code}] {base}"
        if self.response_body:
            base += f" | Details: {self.response_body}"
        return base


class XovisAuthError(XovisAPIError):
    """
    Raised when authentication fails (HTTP 401/403) or token acquisition fails.
    """

    pass


class RateLimitError(XovisAPIError):
    """
    Raised when the API rate limit is exceeded (HTTP 429).
    """

    pass


class XovisClientError(XovisAPIError):
    """
    Raised when the client sends a bad request (HTTP 400-499, excluding 401, 403, 429).
    """

    pass


class XovisServerError(XovisAPIError):
    """
    Raised when the Xovis sensor or HUB encounters an internal error (HTTP 500-599).
    """

    pass


class XovisConnectionError(XovisAPIError):
    """
    Raised when the underlying network connection fails (DNS, Socket timeouts, etc).
    """

    pass


# --- DX / SMART RESOLVER EXCEPTIONS ---


class ResourceNotFoundError(XovisClientError):
    """
    Raised when the Smart Resolver attempts to look up a resource by its string name,
    but no matching resource exists on the device.
    """

    pass


class MultipleResourcesFoundError(XovisClientError):
    """
    Raised when the Smart Resolver attempts to look up a resource by its string name,
    but multiple resources share the exact same name. Forces the developer to use the exact ID.
    """

    pass


class HardwareNotSupportedError(XovisAPIError):
    """
    Raised when a context or operation is attempted on incompatible hardware.
    """

    pass


class SDKFirmwareDriftError(XovisAPIError):
    """
    Raised when the firmware's payload cannot be safely parsed into the SDK's baseline models.
    """

    pass
