"""
Xovis SDK - HTTP Client Engine
Enterprise-grade async HTTP client with automated resilience, retries, and error mapping.
"""
import logging
from typing import Any, Dict, Optional, Union

import httpx
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
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
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.max_retries = max_retries

        # Generous connection pool limits designed for high-concurrency Layer 2 ingestion
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=200)

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=self.auth,
            timeout=httpx.Timeout(timeout),
            limits=limits
        )

    async def aclose(self) -> None:
        """Gracefully release the connection pool."""
        await self.client.aclose()

    async def __aenter__(self) -> "XovisHTTPClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()

    def _map_response_to_exception(self, response: httpx.Response) -> httpx.Response:
        """Parses the HTTP status code and throws the corresponding Xovis SDK exception."""
        if response.is_success:
            return response

        status = response.status_code
        text = response.text

        if status in (401, 403):
            raise XovisAuthError(f"Authentication/Authorization failed", status_code=status, response_body=text)
        elif status == 429:
            raise RateLimitError(f"Rate limited by endpoint", status_code=status, response_body=text)
        elif status in (502, 503, 504):
            raise XovisServerError(f"Service Unavailable", status_code=status, response_body=text)
        elif status >= 500:
            raise XovisServerError(f"Server-side error", status_code=status, response_body=text)
        elif 400 <= status < 500:
            raise XovisClientError(f"Client request error", status_code=status, response_body=text)

        raise XovisAPIError(f"Unexpected API error", status_code=status, response_body=text)

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """
        Internal request execution with built-in tenacity retry mechanics.
        Automatically retries on 429, 502/503/504, or Network Drops.
        """
        retryer = AsyncRetrying(
            retry=retry_if_exception_type((RateLimitError, XovisServerError, XovisConnectionError)),
            wait=wait_exponential(multiplier=1.0, min=1.0, max=30.0),
            stop=stop_after_attempt(self.max_retries),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

        async for attempt in retryer:
            with attempt:
                try:
                    response = await self.client.request(method, path, **kwargs)
                except httpx.RequestError as e:
                    raise XovisConnectionError(f"Network error during request: {str(e)}") from e

                # Will raise mapped exceptions, triggering tenacity if it's a RateLimitError or XovisServerError
                return self._map_response_to_exception(response)

        # Fallback (Should be unreachable due to reraise=True in Tenacity)
        raise XovisAPIError("Critical failure in retry mechanism")

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", path, params=params, **kwargs)

    async def post(self, path: str, data: Any = None, json: Any = None, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", path, data=data, json=json, **kwargs)

    async def put(self, path: str, data: Any = None, json: Any = None, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", path, data=data, json=json, **kwargs)

    async def delete(self, path: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", path, params=params, **kwargs)