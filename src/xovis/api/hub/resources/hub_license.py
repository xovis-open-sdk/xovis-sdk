"""
Xovis SDK - HUB Cloud License Management Resource

Provides the implementation for managing fleet-wide license status and
provisioning on the Xovis HUB Cloud. Operates within the Control Plane
and State & Topology Plane.
"""

from typing import TYPE_CHECKING, Optional, Union

from xovis.api.core.http import XovisHTTPClient
from xovis.api.hub.resources.base import HubResourceManager
from xovis.models.hub_license_auto import BundleType, LicenseCreate, LicenseStatusResponse

if TYPE_CHECKING:
    from xovis.api.hub.cache import HubCacheManager


class HubLicensesManager(HubResourceManager):
    """
    Manages license provisioning and status on the Xovis HUB Cloud.

    This manager orchestrates the distribution and verification of software
    licenses across the device fleet. It utilizes the HubCacheManager to
    resolve human-readable names to MAC addresses.
    """

    def __init__(self, http_client: XovisHTTPClient, cache: Optional["HubCacheManager"] = None):
        """
        Initializes the HubLicensesManager.

        Args:
            http_client (XovisHTTPClient): The resilient HTTP client.
            cache (Optional[HubCacheManager]): The HUB-level cache manager.
        """
        super().__init__(http_client, cache)
        self._base_path = "/license/api/public/v1/licenses"

    async def get_status(self) -> LicenseStatusResponse:
        """
        Retrieves the license status for all devices in the current HUB tenant.

        Returns:
            LicenseStatusResponse: A collection of license status metadata.
        """
        response = await self._http.get(f"{self._base_path}/status")
        return LicenseStatusResponse.model_validate(response.json())

    async def create(self, id_or_name: Union[str, list[str]], bundle_types: list[BundleType]) -> dict:
        """
        Provisions new license bundles to a set of devices.

        Args:
            id_or_name (Union[str, List[str]]): Target device MAC(s) or name(s).
            bundle_types (List[BundleType]): The license bundles to provision.

        Returns:
            dict: The response from the HUB Cloud.
        """
        device_ids = self._resolve_multiple(id_or_name)
        payload = LicenseCreate(device_ids=device_ids, bundle_types=bundle_types)
        response = await self._http.post(self._base_path, json=payload.model_dump(mode="json", exclude_unset=True))
        return response.json() if response.text else {}
