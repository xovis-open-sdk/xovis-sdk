"""
Xovis SDK - Authentication Managers

Operates within the Control Plane.
Provides robust authentication handlers for local sensors (Basic/NTLM) and
the Xovis HUB Cloud (OAuth2). Ensures secure access across the fleet while
managing token persistence and strictly adhering to Auth0 form-encoded
payload requirements.
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Optional

import httpx

from .exceptions import XovisAuthError


class DeviceAuth(httpx.Auth):
    """
    Handles Basic and NTLM Authentication for direct local network connections
    to Xovis Sensors.
    """

    def __init__(self, username: str, password: str, use_ntlm: bool = False) -> None:
        """
        Initializes the DeviceAuth manager for local sensor communication.

        Args:
            username (str): The username for authentication.
            password (str): The password for authentication.
            use_ntlm (bool, optional): Whether to use NTLM authentication.
                Defaults to False.

        Raises:
            ImportError: If NTLM is requested but the 'httpx-ntlm' package is missing.
        """
        self.username = username
        self.password = password
        self.use_ntlm = use_ntlm

        if self.use_ntlm:
            try:
                from httpx_ntlm import HttpNtlmAuth  # type: ignore

                self._auth: httpx.Auth = HttpNtlmAuth(self.username, self.password)
            except ImportError as exc:
                raise ImportError(
                    "The 'httpx-ntlm' package is required for NTLM authentication. Please install it via `pip install httpx-ntlm`."
                ) from exc
        else:
            self._auth = httpx.BasicAuth(self.username, self.password)

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """
        Executes the synchronous authentication flow.

        Args:
            request (httpx.Request): The outgoing HTTP request.

        Yields:
            Generator[httpx.Request, httpx.Response, None]: The request/response sequence.
        """
        yield from self._auth.auth_flow(request)

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        """
        Executes the asynchronous authentication flow.

        Handles both native async flows and wrapped synchronous flows for compatibility.

        Args:
            request (httpx.Request): The outgoing HTTP request.

        Yields:
            AsyncGenerator[httpx.Request, httpx.Response]: The request/response sequence.
        """
        if hasattr(self._auth, "async_auth_flow"):
            async for req in self._auth.async_auth_flow(request):
                yield req
        else:
            for req in self._auth.auth_flow(request):
                yield req


class HubAuth(httpx.Auth):
    """
    Handles OAuth2 Client Credentials flow for the Xovis HUB Cloud.

    Caches the bearer token to disk and memory, and automatically intercepts
    and refreshes on 401 Unauthorized responses. Enforces form-encoded payloads
    for Auth0 compatibility.
    """

    requires_response_body = True

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token_url: str = "https://login.xovis.cloud/oauth/token",
        cache_file: Optional[str] = None,
        token: Optional[str] = None,
    ) -> None:
        """
        Initializes the HubAuth manager for Xovis HUB Cloud communication.

        Checks for a cache file in the current directory (Project Root) first,
        falling back to the user's home directory if not found.

        Args:
            client_id (str, optional): The Auth0 Client ID.
            client_secret (str, optional): The Auth0 Client Secret.
            token_url (str, optional): The OAuth2 token endpoint URL.
            cache_file (Optional[str], optional): Custom path for token caching.
                Defaults to .xovis_hub_token.json.
            token (Optional[str], optional): Static pre-authorized token.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self._static_token = token
        
        self.access_token: Optional[str] = token
        self.expires_at: float = float('inf') if token else 0.0
        self._lock = asyncio.Lock()
        self.cache_path = None

        if not token:
            if cache_file is None:
                local_cache = Path(".xovis_hub_token.json")
                if local_cache.exists():
                    self.cache_path = local_cache
                else:
                    self.cache_path = Path.home() / ".xovis_hub_token.json"
            else:
                self.cache_path = Path(cache_file)
    
            self._load_from_cache()

    def _load_from_cache(self) -> None:
        """
        Loads a valid token from the local disk cache if it exists.

        Ensures that the cached token belongs to the currently configured client_id
        to prevent cross-account leakage.
        """
        if self.cache_path and self.cache_path.exists():
            try:
                with open(self.cache_path) as f:
                    data = json.load(f)
                    if data.get("client_id") == self.client_id:
                        self.access_token = data.get("access_token")
                        self.expires_at = data.get("expires_at", 0.0)
            except Exception:
                pass

    def _save_to_cache(self) -> None:
        """
        Saves the current token and expiration to local disk.

        Handles directory creation and failures for read-only environments.
        """
        if self.cache_path:
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_path, "w") as f:
                    json.dump(
                        {
                            "client_id": self.client_id,
                            "access_token": self.access_token,
                            "expires_at": self.expires_at,
                        },
                        f,
                    )
            except Exception:
                pass

    async def _fetch_token_unlocked(self) -> None:
        """
        Reaches out to the OAuth endpoint to fetch a new Bearer token.

        Xovis Hub Auth0 explicitly requires form-encoded data (`data=`) rather
        than JSON payloads (`json=`) for certain grant types or audiences. This
        method strictly enforces that networking requirement.

        Raises:
            XovisAuthError: If the token acquisition fails due to HTTP errors or
                invalid response structures.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "audience": "https://api.xovis.cloud/",
                    },
                    timeout=10.0,
                )
                if not response.is_success:
                    raise XovisAuthError(
                        f"Failed to fetch Hub access token (HTTP {response.status_code}): {response.text}",
                        status_code=response.status_code,
                    )
                data = response.json()

                self.access_token = data.get("access_token")
                if not self.access_token:
                    raise XovisAuthError("Invalid OAuth2 response: missing 'access_token'")

                self.expires_at = time.time() + data.get("expires_in", 86400) - 60

                self._save_to_cache()

            except XovisAuthError:
                raise
            except Exception as e:
                raise XovisAuthError(f"Error fetching Hub access token: {str(e)}") from e

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        """
        Executes the asynchronous OAuth2 authentication flow.

        Includes automated token refresh, thread-safe locking during acquisition,
        and immediate retry on 401 Unauthorized responses.

        Args:
            request (httpx.Request): The outgoing HTTP request.

        Yields:
            AsyncGenerator[httpx.Request, httpx.Response]: The request/response sequence.
        """
        print("ASYNC AUTH FLOW CALLED")
        if not self.access_token or time.time() >= self.expires_at:
            print("NEED TOKEN")
            async with self._lock:
                if not self.access_token or time.time() >= self.expires_at:
                    await self._fetch_token_unlocked()

        current_token = self.access_token
        request.headers["Authorization"] = f"Bearer {current_token}"
        print(f"ADDED AUTH HEADER: Bearer {current_token[:10]}... headers now: {request.headers.keys()}")

        response = yield request

        if response.status_code == 401:
            print("GOT 401, REFRESHING")
            async with self._lock:
                if self.access_token == current_token:
                    await self._fetch_token_unlocked()

            request.headers["Authorization"] = f"Bearer {self.access_token}"
            yield request
