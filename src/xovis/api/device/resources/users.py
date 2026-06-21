"""
Xovis SDK - User Management Resource

Provides the implementation for managing user accounts, passwords, sessions,
and activation states on local edge sensors. Operates within the Control Plane.
"""

from typing import TYPE_CHECKING, Any

from xovis.api.core.http import XovisHTTPClient
from xovis.models.device_auto import stable_models

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient


class UsersManager:
    """
    Manages user accounts and security settings on a Xovis device.

    This manager handles the full user lifecycle, including session management,
    password updates, account activation, and factory reset authorization (SMK).
    """

    def __init__(self, http_client: XovisHTTPClient, client: "DeviceClient" = None) -> None:
        """
        Initializes the UsersManager.

        Args:
            http_client (XovisHTTPClient): The resilient HTTP client.
            client (DeviceClient): The parent DeviceClient instance.
        """
        self._http = http_client
        self._client = client
        self._base_path = "/api/v5/users"

    @property
    def models(self):
        """Returns the appropriate Pydantic models for the current device firmware."""
        return self._client.models if self._client else stable_models

    async def get_all(self) -> Any:
        """
        Retrieves the list of all configured user accounts.

        Returns:
            UserDetails: A collection of user account details.
        """
        response = await self._http.get(self._base_path)
        return self.models.UserDetails.model_validate(response.json())

    async def apply_factory_defaults(self) -> None:
        """Applies factory default user configurations."""
        await self._http.delete(self._base_path)

    async def get_current(self) -> Any:
        """
        Retrieves details for the currently authenticated user.

        Returns:
            UserDetail: The active user's account details.
        """
        response = await self._http.get(f"{self._base_path}/current")
        return self.models.UserDetail.model_validate(response.json())

    async def update_current_password(self, credentials: Any) -> None:
        """
        Updates the password for the current user.

        Args:
            credentials (UserCredentials): The new password details.
        """
        await self._http.put(f"{self._base_path}/current/password", json=credentials)

    async def login(self) -> Any:
        """
        Authenticates the user and creates a new session.

        Returns:
            UserSession: The details of the newly created session.
        """
        response = await self._http.post(f"{self._base_path}/login")
        return self.models.UserSession.model_validate(response.json())

    async def logout(self) -> None:
        """Terminates the current user session."""
        await self._http.post(f"{self._base_path}/logout")

    async def reset(self, smk: Any) -> None:
        """
        Applies factory defaults using a Secure Management Key (SMK).

        Args:
            smk (UserSmk): The SMK authorization payload.
        """
        await self._http.post(f"{self._base_path}/reset", json=smk)

    async def get_user(self, user_id: str) -> Any:
        """
        Retrieves details for a specific user account.

        Args:
            user_id (str): The identifier of the user.

        Returns:
            UserDetail: The requested user's account details.
        """
        response = await self._http.get(f"{self._base_path}/{user_id}")
        return self.models.UserDetail.model_validate(response.json())

    async def update_activation(self, user_id: str, activation: Any) -> Any:
        """
        Updates the activation state of a specific user account.

        Args:
            user_id (str): The identifier of the user.
            activation (UserActivation): The new activation state.

        Returns:
            UserActivation: The updated activation state.
        """
        response = await self._http.put(f"{self._base_path}/{user_id}/activation", json=activation)
        return self.models.UserActivation.model_validate(response.json())

    async def reset_password(self, user_id: str) -> None:
        """
        Resets a user's password to the factory default.

        Args:
            user_id (str): The identifier of the user.
        """
        await self._http.delete(f"{self._base_path}/{user_id}/password")
