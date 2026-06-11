"""
Xovis SDK - HTTP Client Engine

This module resides within the Control Plane, providing an enterprise-grade
async HTTP client with automated resilience, retries, and error mapping.
It wraps `httpx.AsyncClient` and integrates `tenacity` for robust handling
of transient failures and rate limits.
"""

import logging
from typing import Any, Optional, Union

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .auth import DeviceAuth, HubAuth
from .exceptions import (
    RateLimitError,
    XovisAPIError,
    XovisAuthError,
    XovisClientError,
    XovisConnectionError,
    XovisServerError,
)

logger = logging.getLogger(__name__)


class XovisHTTPClient:
    """
    High-performance async HTTP client wrapping httpx.AsyncClient.
    Manages connection pooling, authentication injection, and automated retry policies.
    """

    def __init__(
        self,
        base_url: str,
        auth: Union[DeviceAuth, HubAuth, httpx.Auth, None] = None,
        timeout: float = 15.0,
        max_retries: int = 5,
        **kwargs: Any,
    ) -> None:
        """
        Initializes the XovisHTTPClient with automated retry policies.

        Args:
            base_url (str): The target base URL for the API.
            auth (Union[DeviceAuth, HubAuth, httpx.Auth, None], optional):
                The authentication manager. Defaults to None.
            timeout (float, optional): Request timeout in seconds. Defaults to 15.0.
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 5.
            **kwargs (Any): Additional configuration for the HTTP engine (e.g., limits).
        """
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.max_retries = max_retries

        # Extract limits from kwargs if provided, otherwise use defaults
        limits = kwargs.pop("limits", None)
        if limits is None:
            limits = httpx.Limits(max_keepalive_connections=50, max_connections=200)

        # Initialize default headers often required by Xovis WAFs
        headers = kwargs.pop("headers", {})
        headers.setdefault("X-Requested-With", "XmlHttpRequest")
        headers.setdefault("accept", "application/json")

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=self.auth,
            timeout=httpx.Timeout(timeout),
            limits=limits,
            headers=headers,
            **kwargs,
        )

    async def aclose(self) -> None:
        """
        Gracefully releases the connection pool.
        """
        await self.client.aclose()

    async def __aenter__(self) -> "XovisHTTPClient":
        """
        Enters the asynchronous context manager.

        Returns:
            XovisHTTPClient: The active client instance.
        """
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exits the asynchronous context manager and releases resources.

        Args:
            exc_type (Any): The exception type if an error occurred.
            exc_val (Any): The exception value.
            exc_tb (Any): The traceback object.
        """
        await self.aclose()

    def _map_response_to_exception(self, response: httpx.Response) -> httpx.Response:
        """
        Parses the HTTP status code and throws the corresponding Xovis SDK exception.

        Args:
            response (httpx.Response): The received HTTP response.

        Returns:
            httpx.Response: The original response if it indicates success.

        Raises:
            XovisAuthError: For 401 and 403 responses.
            RateLimitError: For 429 responses.
            XovisServerError: For 500+ responses.
            XovisClientError: For other 400-level errors.
            XovisAPIError: For unexpected status codes.
        """
        if response.is_success:
            return response

        status = response.status_code
        text = response.text

        if status == 401:
            raise XovisAuthError("Authentication failed", status_code=status, response_body=text)
        elif status == 403:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" in content_type:
                # Xovis sensors return HTML 403 when hardware features are missing (e.g. WiFi on non-WiFi sensor)
                # OR when the Hub Cloud WAF/Privacy Mode blocks the request.
                raise XovisAuthError(
                    "Access Forbidden: This typically indicates missing hardware capabilities, "
                    "restrictive Edge Privacy Mode, or Hub Cloud Proxy Firewall blocks.",
                    status_code=status,
                    response_body=text,
                )
            raise XovisAuthError("Authorization failed", status_code=status, response_body=text)
        elif status == 429:
            raise RateLimitError("Rate limited by endpoint", status_code=status, response_body=text)
        elif status in (502, 503, 504):
            raise XovisServerError("Service Unavailable", status_code=status, response_body=text)
        elif status >= 500:
            raise XovisServerError("Server-side error", status_code=status, response_body=text)
        elif 400 <= status < 500:
            raise XovisClientError("Client request error", status_code=status, response_body=text)

        raise XovisAPIError("Unexpected API error", status_code=status, response_body=text)

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """
        Internal request execution with built-in tenacity retry mechanics.

        Automatically retries on 429 RateLimitError, 50x XovisServerError,
        or XovisConnectionError (Network Drops) using exponential backoff.

        Args:
            method (str): The HTTP method (e.g., GET, POST).
            path (str): The API endpoint path.
            **kwargs (Any): Additional keyword arguments passed to httpx.request.

        Returns:
            httpx.Response: The validated HTTP response.

        Raises:
            XovisConnectionError: If a network error occurs during the request.
            XovisAPIError: If a critical failure occurs in the retry mechanism.
        """
        max_retries = kwargs.pop("max_retries", self.max_retries)

        def before_sleep(retry_state):
            """Custom retry callback for verbose endpoint diagnostics."""
            exception = retry_state.outcome.exception()
            wait = retry_state.next_action.sleep
            # The URL and method are passed via request, we can build the full URL
            # Note: self.base_url is available.
            full_url = f"{self.base_url}{path}"
            logger.warning(f"Retrying {method} {full_url} in {wait:.2f}s due to {exception}")

        retryer = AsyncRetrying(
            retry=retry_if_exception_type((RateLimitError, XovisServerError, XovisConnectionError, httpx.RequestError)),
            wait=wait_exponential(multiplier=2.0, min=2.0, max=60.0),
            stop=stop_after_attempt(max_retries),
            before_sleep=before_sleep,
            reraise=True,
        )

        async for attempt in retryer:
            with attempt:
                try:
                    response = await self.client.request(method, path, **kwargs)
                    return self._map_response_to_exception(response)
                except (httpx.RequestError, httpx.HTTPStatusError) as e:
                    if isinstance(e, httpx.HTTPStatusError):
                        # Only retry on 429 and 50x as per Xovis resilience rules
                        if e.response.status_code == 429 or 500 <= e.response.status_code < 600:
                            # Re-raise to let tenacity handle it if it matches retry_if_exception_type
                            raise self._map_response_to_exception(e.response)
                        return self._map_response_to_exception(e.response)

                    # For connection errors, wrap in XovisConnectionError
                    raise XovisConnectionError(f"Network error during request: {str(e)}") from e

        raise XovisAPIError("Critical failure in retry mechanism")

    async def get(self, path: str, params: Optional[dict[str, Any]] = None, **kwargs: Any) -> httpx.Response:
        """
        Executes an asynchronous GET request.

        Args:
            path (str): The API endpoint path.
            params (Optional[Dict[str, Any]], optional): Query parameters. Defaults to None.
            **kwargs (Any): Additional keyword arguments passed to the request.

        Returns:
            httpx.Response: The HTTP response.
        """
        return await self.request("GET", path, params=params, **kwargs)

    async def post(self, path: str, data: Any = None, json: Any = None, **kwargs: Any) -> httpx.Response:
        """
        Executes an asynchronous POST request.

        Args:
            path (str): The API endpoint path.
            data (Any, optional): Form data payload. Defaults to None.
            json (Any, optional): JSON data payload. Defaults to None.
            **kwargs (Any): Additional keyword arguments passed to the request.

        Returns:
            httpx.Response: The HTTP response.
        """
        return await self.request("POST", path, data=data, json=json, **kwargs)

    async def put(self, path: str, data: Any = None, json: Any = None, **kwargs: Any) -> httpx.Response:
        """
        Executes an asynchronous PUT request.

        Args:
            path (str): The API endpoint path.
            data (Any, optional): Form data payload. Defaults to None.
            json (Any, optional): JSON data payload. Defaults to None.
            **kwargs (Any): Additional keyword arguments passed to the request.

        Returns:
            httpx.Response: The HTTP response.
        """
        return await self.request("PUT", path, data=data, json=json, **kwargs)

    async def patch(self, path: str, data: Any = None, json: Any = None, **kwargs: Any) -> httpx.Response:
        """
        Executes an asynchronous PATCH request.

        Args:
            path (str): The API endpoint path.
            data (Any, optional): Form data payload. Defaults to None.
            json (Any, optional): JSON data payload. Defaults to None.
            **kwargs (Any): Additional keyword arguments passed to the request.

        Returns:
            httpx.Response: The HTTP response.
        """
        return await self.request("PATCH", path, data=data, json=json, **kwargs)

    async def delete(self, path: str, params: Optional[dict[str, Any]] = None, **kwargs: Any) -> httpx.Response:
        """
        Executes an asynchronous DELETE request.

        Args:
            path (str): The API endpoint path.
            params (Optional[Dict[str, Any]], optional): Query parameters. Defaults to None.
            **kwargs (Any): Additional keyword arguments passed to the request.

        Returns:
            httpx.Response: The HTTP response.
        """
        return await self.request("DELETE", path, params=params, **kwargs)
