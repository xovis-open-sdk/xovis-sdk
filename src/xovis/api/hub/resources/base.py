"""
Xovis SDK - HUB Cloud Base Resource
"""

import re
from typing import TYPE_CHECKING, Optional, Union

from xovis.api.core.exceptions import MultipleResourcesFoundError, ResourceNotFoundError
from xovis.api.core.http import XovisHTTPClient

if TYPE_CHECKING:
    from xovis.api.hub.cache import HubCacheManager


class HubResourceManager:
    """
    Base class for HUB resource managers providing shared resolution logic.
    """

    def __init__(self, http_client: XovisHTTPClient, cache: Optional["HubCacheManager"] = None):
        """
        Initializes the HubResourceManager.

        Args:
            http_client (XovisHTTPClient): The resilient HTTP client.
            cache (Optional[HubCacheManager]): The HUB-level cache manager.
        """
        self._http = http_client
        self._cache = cache

    def _resolve_mac_address(self, id_or_name: str) -> str:
        """
        Resolves a device's MAC address from either a name or the address itself.

        Prioritizes exact MAC address matching. Falls back to the HubCacheManager
        for name lookups.

        Args:
            id_or_name (str): The MAC address or human-readable device name.

        Returns:
            str: The resolved MAC address.

        Raises:
            ResourceNotFoundError: If the name cannot be resolved.
            MultipleResourcesFoundError: If the name is ambiguous.
        """
        is_mac = re.match(r"^([0-9A-Fa-f]{2}[:]){5}([0-9A-Fa-f]{2})$", id_or_name)

        if not self._cache:
            return id_or_name

        if is_mac:
            return id_or_name

        matches = [d for d in self._cache._state.devices if d.device_name == id_or_name]

        if not matches:
            raise ResourceNotFoundError(f"Device name '{id_or_name}' not found in cache.")

        if len(matches) > 1:
            conflicts = [f"{d.id.root if hasattr(d.id, 'root') else d.id} (Customer: {d.customer or 'N/A'})" for d in matches]
            raise MultipleResourcesFoundError(f"Multiple devices found with name '{id_or_name}': {', '.join(conflicts)}")

        d = matches[0]
        return d.id.root if hasattr(d.id, "root") else d.id

    def _resolve_multiple(self, ids_or_names: Union[str, list[str]]) -> list[str]:
        """
        Resolves multiple MAC addresses from a list of identifiers.

        Args:
            ids_or_names (Union[str, List[str]]): A single ID/name or a list.

        Returns:
            List[str]: A list of resolved MAC addresses.
        """
        if isinstance(ids_or_names, str):
            ids_or_names = [ids_or_names]
        return [self._resolve_mac_address(x) for x in ids_or_names]
