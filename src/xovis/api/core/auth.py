"""
Xovis SDK - Authentication Managers
Provides robust auth handlers for local sensors (Basic/NTLM) and Xovis HUB (OAuth2).
"""
import asyncio
import time
from typing import AsyncGenerator, Generator, Optional

import httpx

from .exceptions import XovisAuthError


class DeviceAuth(httpx.Auth):
    """
    Handles Basic and NTLM Authentication for direct local network connections to Xovis Sensors.
    Note: NTLM requires the `httpx-ntlm` package.
    """

    def __init__(self, username: str, password: str, use_ntlm: bool = False) -> None:
        self.username = username
        self.password = password
        self.use_ntlm = use_ntlm

        if self.use_ntlm:
            try:
                from httpx_ntlm import HttpNtlmAuth  # type: ignore
                self._auth: httpx.Auth = HttpNtlmAuth(self.username, self.password)
            except ImportError as exc:
                raise ImportError(
                    "The 'httpx-ntlm' package is required for NTLM authentication. "
                    "Please install it via `pip install httpx-ntlm`."
                ) from exc
        else:
            self._auth = httpx.BasicAuth(self.username, self.password)

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        yield from self._auth.auth_flow(request)

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        # Handle underlying synchronous or asynchronous generators smoothly
        if hasattr(self._auth, "async_auth_flow"):
            async for req in self._auth.async_auth_flow(request):
                yield req
        else:
            for req in self._auth.auth_flow(request):
                yield req


class HubAuth(httpx.Auth):
    """
    Handles OAuth2 Client Credentials flow for the Xovis Cloud HUB.
    Caches the bearer token in memory and automatically intercepts and refreshes on 401.
    """
    requires_response_body = True

    def __init__(self, client_id: str, client_secret: str, token_url: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url

        self.access_token: Optional[str] = None
        self.expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def _fetch_token_unlocked(self) -> None:
        """Reach out to the OAuth endpoint to fetch a new Bearer token."""
        # Use an isolated client to bypass the authenticated HTTP client pool
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                self.access_token = data.get("access_token")
                if not self.access_token:
                    raise XovisAuthError("Invalid OAuth2 response: missing 'access_token'")

                # Apply a 60-second safety buffer to preemptively refresh right before hard expiration
                self.expires_at = time.time() + data.get("expires_in", 3600) - 60

            except httpx.HTTPStatusError as e:
                raise XovisAuthError(
                    f"Failed to fetch Hub access token (HTTP {e.response.status_code}): {e.response.text}",
                    status_code=e.response.status_code
                ) from e
            except Exception as e:
                raise XovisAuthError(f"Error fetching Hub access token: {str(e)}") from e

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        # 1. Check if token is missing or expired, fetch if necessary
        if not self.access_token or time.time() >= self.expires_at:
            async with self._lock:
                # Double-check inside lock to prevent race conditions
                if not self.access_token or time.time() >= self.expires_at:
                    await self._fetch_token_unlocked()

        current_token = self.access_token
        request.headers["Authorization"] = f"Bearer {current_token}"

        response = yield request

        # 2. If the API rejects our token despite caching logic, immediately refresh and retry
        if response.status_code == 401:
            async with self._lock:
                # Only fetch if another concurrent task hasn't already refreshed it
                if self.access_token == current_token:
                    await self._fetch_token_unlocked()

            request.headers["Authorization"] = f"Bearer {self.access_token}"
            yield request