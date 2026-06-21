"""
HubFleetDirectory - Parses the Hub fleet state and provides IDE-autosuggested device accessors.
"""

import json
import re
from pathlib import Path
from typing import Any, Generic, TypeVar

T = TypeVar("T")

class DictAccessor(Generic[T]):
    """Dynamic accessor exposing dictionary keys as properties for IDE autocomplete."""
    
    def __init__(self, items: dict[str, T]):
        self._items = items
        
    def __getattr__(self, name: str) -> T:
        if name in self._items:
            return self._items[name]
        raise AttributeError(f"Resource '{name}' not found. Available: {list(self._items.keys())}")
        
    def __dir__(self) -> list[str]:
        return super().__dir__() + list(self._items.keys())
        
    def __getitem__(self, key: str) -> T:
        return self._items[key]

class HubFleetDirectory:
    """Parses the Hub fleet state and provides IDE-autosuggested device accessors."""

    def __init__(self, devices_state: list[dict[str, Any]]):
        """
        Initializes the HubFleetDirectory.

        Args:
            devices_state (list[dict[str, Any]]): The list of device dictionaries from the Hub state.
        """
        self._devices = devices_state

        # Build indexes
        self._by_mac = {self._sanitize(str(d.get("id", ""))): d for d in devices_state if "id" in d}
        self._by_name = {self._sanitize(str(d.get("device_name", ""))): d for d in devices_state if "device_name" in d}

        # For groups that contain multiple devices, we store lists of device dicts
        self._by_customer = self._group_by_key("customer")
        self._by_category = self._group_by_list_key("categories")
        self._by_device_group = self._group_by_key("device_group")

        # Expose via DictAccessor for IDE auto-completion
        self.by_mac = DictAccessor(self._by_mac)
        self.by_name = DictAccessor(self._by_name)
        self.by_customer = DictAccessor(self._by_customer)
        self.by_category = DictAccessor(self._by_category)
        self.by_device_group = DictAccessor(self._by_device_group)

    @classmethod
    def from_file(cls, path: str | Path = "_local_resources/states/hub_fleet_state.json") -> "HubFleetDirectory":
        """
        Loads the Hub fleet directory from a local JSON state file.

        Args:
            path (str | Path): The path to the JSON file. Defaults to "_local_resources/states/hub_fleet_state.json".

        Returns:
            HubFleetDirectory: A fully indexed directory of devices.
            
        Raises:
            FileNotFoundError: If the specified state file does not exist.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Hub state file not found at: {file_path}")
            
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            
        devices = data.get("devices", []) if isinstance(data, dict) else data
        if not isinstance(devices, list):
            devices = []
            
        return cls(devices)

    @classmethod
    async def from_hub(cls, hub_client: Any, sync_cache: bool = True) -> "HubFleetDirectory":
        """
        Loads the Hub fleet directory from an active HubClient connection.

        Args:
            hub_client (Any): An active HubClient instance.
            sync_cache (bool): Whether to force a cache sync before extracting state. Defaults to True.

        Returns:
            HubFleetDirectory: A fully indexed directory of devices.
        """
        if sync_cache:
            await hub_client.cache.sync()
            
        devices = getattr(hub_client.cache._state, "devices", [])
        
        # Convert Pydantic models to dicts if necessary
        raw_devices = []
        for dev in devices:
            if hasattr(dev, "model_dump"):
                raw_devices.append(dev.model_dump())
            elif isinstance(dev, dict):
                raw_devices.append(dev)
                
        return cls(raw_devices)

    def _sanitize(self, val: str) -> str:
        """Sanitizes a string to be a valid Python attribute name."""
        safe_val = re.sub(r"[^0-9a-zA-Z_]", "_", val)
        if safe_val and safe_val[0].isdigit():
            safe_val = "_" + safe_val
        return safe_val

    def _group_by_key(self, key: str) -> dict[str, list[dict[str, Any]]]:
        """Groups devices by a single key."""
        result: dict[str, list[dict[str, Any]]] = {}
        for d in self._devices:
            val = d.get(key)
            if val:
                safe_val = self._sanitize(str(val))
                result.setdefault(safe_val, []).append(d)
        return result

    def _group_by_list_key(self, key: str) -> dict[str, list[dict[str, Any]]]:
        """Groups devices by a list of keys."""
        result: dict[str, list[dict[str, Any]]] = {}
        for d in self._devices:
            vals = d.get(key, [])
            if isinstance(vals, list):
                for val in vals:
                    if val:
                        safe_val = self._sanitize(str(val))
                        result.setdefault(safe_val, []).append(d)
        return result
