"""
Xovis SDK - HUB Cloud Device Management Resource

Provides the implementation for managing fleet-wide device metadata, UI access,
and categorical assignments on the Xovis HUB Cloud. Operates within the
Control Plane and State & Topology Plane.
"""

from typing import TYPE_CHECKING, Optional, Union

from xovis.api.core.http import XovisHTTPClient
from xovis.api.hub.resources.base import HubResourceManager
from xovis.models.hub_auto import (
    DevicesCategoriesAssignment,
    DevicesCustomerAssignment,
    DevicesResponse,
    DeviceUiAccess,
)

if TYPE_CHECKING:
    from xovis.api.hub.cache import HubCacheManager


class HubDevicesManager(HubResourceManager):
    """
    Manages device operations on the Xovis HUB Cloud.

    This manager orchestrates fleet-wide operations, including metadata
    synchronization and secure UI tunneling. It utilizes the HubCacheManager
    to resolve human-readable names to MAC addresses.
    """

    def __init__(self, http_client: XovisHTTPClient, cache: Optional["HubCacheManager"] = None):
        """
        Initializes the HubDevicesManager.

        Args:
            http_client (XovisHTTPClient): The resilient HTTP client.
            cache (Optional[HubCacheManager]): The HUB-level cache manager.
        """
        super().__init__(http_client, cache)
        self._base_path = "/device-management/api/public/v1/devices"

    async def get_devices(self) -> DevicesResponse:
        """
        Retrieves all devices associated with the current HUB tenant.

        Returns:
            DevicesResponse: A collection of device metadata.
        """
        response = await self._http.get(self._base_path)
        return DevicesResponse.model_validate(response.json())

    async def get_device_ui_access(self, id_or_name: Union[str, list[str]]) -> DeviceUiAccess:
        """
        Generates secure, temporary UI access links for specific devices.

        Args:
            id_or_name (Union[str, List[str]]): Target device MAC(s) or name(s).

        Returns:
            DeviceUiAccess: Secure access URLs for the requested devices.
        """
        device_id = self._resolve_mac_address(id_or_name)
        response = await self._http.get(f"{self._base_path}/{device_id}/webui_link")
        return DeviceUiAccess.model_validate(response.json())

    async def assign_customer(self, id_or_name: Union[str, list[str]], customer_name: str) -> dict:
        """
        Assigns a customer identifier to a list of devices.

        Args:
            id_or_name (Union[str, List[str]]): Target device MAC(s) or name(s).
            customer_name (str): The customer name to assign.

        Returns:
            dict: The response from the HUB Cloud.
        """
        device_ids = self._resolve_multiple(id_or_name)
        payload = DevicesCustomerAssignment(device_ids=device_ids, customer_name=customer_name)
        response = await self._http.post(f"{self._base_path}/assign_customer", json=payload.model_dump(mode="json"))
        return response.json() if response.text else {}

    async def update_categories(
        self,
        id_or_name: Union[str, list[str]],
        categories_to_add: Optional[list[str]] = None,
        categories_to_remove: Optional[list[str]] = None,
    ) -> dict:
        """
        Modifies categorical tags for a list of devices.

        Args:
            id_or_name (Union[str, List[str]]): Target device MAC(s) or name(s).
            categories_to_add (Optional[List[str]]): Tags to append.
            categories_to_remove (Optional[List[str]]): Tags to strip.

        Returns:
            dict: The response from the HUB Cloud.
        """
        device_ids = self._resolve_multiple(id_or_name)
        payload = DevicesCategoriesAssignment(
            device_ids=device_ids,
            categories_to_add=categories_to_add,
            categories_to_remove=categories_to_remove,
        )
        response = await self._http.post(
            f"{self._base_path}/manage_categories",
            json=payload.model_dump(mode="json", exclude_unset=True),
        )
        return response.json() if response.text else {}
