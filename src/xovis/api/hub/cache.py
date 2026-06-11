"""
Xovis SDK - Hub Configuration Cache Manager

This module resides within the State & Topology Plane, providing a client-side
cache for the Xovis HUB Cloud fleet. It manages device and license state
synchronization, implementing robust client-side filtering and dot-notation
accessors for interactive environments.
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from xovis.api.core.http import XovisHTTPClient
from xovis.api.device.cache import REPLAccessor
from xovis.models.hub_auto import Device, DevicesResponse
from xovis.models.hub_license_auto import LicenseStatus, LicenseStatusResponse


class HubStateBucket(BaseModel):
    """
    Root state container for the Xovis HUB Cloud fleet.

    Aggregates collections of devices and their corresponding license statuses
    fetched from the Hub API, enabling efficient client-side filtering and lookup.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")
    devices: list[Device] = Field(default_factory=list)
    licenses: list[LicenseStatus] = Field(default_factory=list)
    # Volatile topological state (Master/Child/Standalone mapping) discovered during Deep Dive.
    # Keyed by MAC address.
    topology_roles: dict[str, str] = Field(default_factory=dict)
    topology_parents: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("topology_roles", mode="before")
    @classmethod
    def normalize_roles_keys(cls, v: Any) -> Any:
        """
        Ensures all topology role keys are normalized to uppercase MAC addresses.

        Args:
            v (Any): Raw role mapping.

        Returns:
            Any: Normalized role dictionary.
        """
        if isinstance(v, dict):
            return {str(k).upper(): v2 for k, v2 in v.items()}
        if v is None:
            return {}
        return v

    @field_validator("topology_parents", mode="before")
    @classmethod
    def normalize_parents(cls, v: Any) -> Any:
        """
        Normalizes parent MAC address lists to consistent uppercase formats.

        Args:
            v (Any): Raw parent mapping.

        Returns:
            Any: Normalized parent dictionary.
        """
        if v is None:
            return {}
        if not isinstance(v, dict):
            return v
        normalized = {}
        for k, val in v.items():
            key = str(k).upper()
            if isinstance(val, list):
                normalized[key] = [str(i).upper() for i in val]
            else:
                normalized[key] = [str(val).upper()]
        return normalized


class HubCacheManager:
    """
    Client-side cache manager for the Xovis HUB Cloud fleet.

    Coordinates the synchronization of fleet-wide metadata (devices, licenses)
    from the HUB Cloud API. Supports high-performance client-side filtering
    via `fleet_filter` and provides dot-notation accessors for rapid
    discovery in REPL environments.
    """

    def __init__(self, http_client: XovisHTTPClient, fleet_filter: Optional[dict[str, Any]] = None) -> None:
        """
        Initializes the HubCacheManager.

        Args:
            http_client (XovisHTTPClient): The resilient Hub API engine.
            fleet_filter (Optional[Dict[str, Any]], optional): A dictionary of
                attributes and values to filter the fleet by (e.g., {"group": "EMEA"}).
                Supports list-based "any-of" matching.
        """
        self._http = http_client
        self.fleet_filter = fleet_filter or {}
        self._state = HubStateBucket()

    @property
    def devices(self) -> REPLAccessor[Device]:
        """
        Accessor for devices mapped by their human-readable name.

        Returns:
            REPLAccessor[Device]: A dynamic accessor for name-based device discovery.
        """
        return REPLAccessor(self._state.devices, key_attr="device_name")

    @property
    def devices_by_mac(self) -> REPLAccessor[Device]:
        """
        Accessor for devices mapped by their unique MAC address.

        Returns:
            REPLAccessor[Device]: A dynamic accessor for MAC-based device discovery.
        """

        class DeviceMacWrapper:
            """Internal wrapper to flatten device IDs for REPL access."""

            def __init__(self, device: Device):
                """
                Initializes the MAC wrapper.

                Args:
                    device (Device): The Hub device model to wrap.
                """
                self._device = device
                self.id = device.id.root if hasattr(device.id, "root") else device.id
                self.device_name = device.device_name

            def __getattr__(self, name):
                return getattr(self._device, name)

        wrappers = [DeviceMacWrapper(d) for d in self._state.devices if d.id]
        return REPLAccessor(wrappers, key_attr="id")

    @property
    def licenses(self) -> REPLAccessor[LicenseStatus]:
        """
        Accessor for licenses mapped by device ID.

        Returns:
            REPLAccessor[LicenseStatus]: A dynamic accessor for license status.
        """
        return REPLAccessor(self._state.licenses, key_attr="device_id")

    async def sync(self, preserve_topology: bool = True) -> None:
        """
        Synchronizes the Hub fleet state with the Cloud API.

        Fetches all devices and licenses, applies client-side filtering based on
        the `fleet_filter` configuration, and populates the internal state bucket.
        Warns if the filter is overly restrictive (dropping >90% of devices).

        Args:
            preserve_topology (bool, optional): If True, retains any topological
                roles and parents discovered during the current session's Deep Dive.
                Defaults to True.

        Raises:
            httpx.HTTPError: If the Hub API is unreachable or returns an error.
        """

        # Save volatile state if requested
        saved_roles = self._state.topology_roles.copy() if preserve_topology else {}
        saved_parents = self._state.topology_parents.copy() if preserve_topology else {}
        try:
            # We try the standard path from documentation first
            # The OpenAPI spec indicates that /devices requires a 'state' parameter or 'customer'
            devices_res = await self._http.get("/devices", params={"state": "MANAGED"})
            if devices_res.status_code == 400:
                # If MANAGED fails, try UNMANAGED as fallback
                devices_res = await self._http.get("/devices", params={"state": "UNMANAGED"})

            devices_res.raise_for_status()
            devices_data = DevicesResponse.model_validate(devices_res.json())
        except Exception as e:
            logging.debug(f"Failed to fetch devices from primary /devices path: {e}")
            # Fallback to the device-management prefixed path
            try:
                devices_res = await self._http.get("/device-management/api/public/v1/devices")
                logging.debug(f"Fallback 1 response: {devices_res.status_code}")
                devices_res.raise_for_status()
                devices_data = DevicesResponse.model_validate(devices_res.json())
            except Exception as e1:
                logging.debug(f"Failed fallback 1: {e1}")
                # Try with the ONLINE status filter
                try:
                    devices_res = await self._http.get(
                        "/device-management/api/public/v1/devices",
                        params={"deviceStatus": "ONLINE"},
                    )
                    logging.debug(f"Fallback 2 response: {devices_res.status_code}")
                    devices_res.raise_for_status()
                    devices_data = DevicesResponse.model_validate(devices_res.json())
                except Exception as e2:
                    logging.debug(f"Failed all device fetch paths: {e2}")
                    devices_data = DevicesResponse(items=[])

        raw_count = len(devices_data.items or [])
        logging.info(f"Hub Sync: Fetched {raw_count} devices from cloud.")
        filtered_devices = []
        if devices_data.items:
            for device in devices_data.items:
                # DEBUG: Print device structure if needed
                # logging.debug(f"Syncing device: {device}")
                if self._matches_filter(device):
                    filtered_devices.append(device)

        logging.info(f"Hub Sync: {len(filtered_devices)} devices remaining after fleet_filter.")
        self._state.devices = filtered_devices

        # ARCHITECTURAL FIX: Enforce uppercase MAC normalization for all Hub devices
        for d in self._state.devices:
            if d.id:
                mac = d.id.root if hasattr(d.id, "root") else str(d.id)
                if hasattr(d.id, "root"):
                    d.id.root = mac.upper()
                else:
                    d.id = mac.upper()

        if raw_count > 0:
            dropped_ratio = (raw_count - len(filtered_devices)) / raw_count
            if dropped_ratio > 0.9 and len(filtered_devices) == 0:
                logging.error(f"Hub fleet_filter dropped ALL fetched devices ({raw_count}). Filter criteria: {self.fleet_filter}")
            elif dropped_ratio > 0.9:
                logging.warning(
                    f"Hub fleet_filter dropped {dropped_ratio:.1%} of fetched devices ({len(filtered_devices)}/{raw_count}). "
                    "Consider refining the filter to improve efficiency."
                )

        try:
            licenses_res = await self._http.get("/license/api/public/v1/licenses/status")
            licenses_res.raise_for_status()
            licenses_data = LicenseStatusResponse.model_validate(licenses_res.json())
        except Exception:
            try:
                licenses_res = await self._http.get("/api/public/v1/licenses/status")
                licenses_res.raise_for_status()
                licenses_data = LicenseStatusResponse.model_validate(licenses_res.json())
            except Exception:
                try:
                    licenses_res = await self._http.get("/licenses/status")
                    licenses_res.raise_for_status()
                    licenses_data = LicenseStatusResponse.model_validate(licenses_res.json())
                except Exception:
                    # If licenses fail, we continue with empty licenses but valid devices
                    licenses_data = LicenseStatusResponse(license_status_list=[])

        # Filter devices for selected customer and group
        device_macs = set()
        for d in filtered_devices:
            if not d.id:
                continue
            mac = d.id.root if hasattr(d.id, "root") else str(d.id)
            device_macs.add(mac)

        filtered_licenses = []
        if hasattr(licenses_data, "license_status_list") and licenses_data.license_status_list:
            for lic in licenses_data.license_status_list:
                mac = lic.device_id.root if hasattr(lic.device_id, "root") else str(lic.device_id)
                if mac in device_macs:
                    filtered_licenses.append(lic)

        self._state.licenses = filtered_licenses

        # Restore volatile topological state
        if preserve_topology:
            self._state.topology_roles.update(saved_roles)
            self._state.topology_parents.update(saved_parents)

    def export_to_file(self, file_path: str, custom_bucket: Optional[HubStateBucket] = None) -> None:
        """
        Writes the current hub state or a custom bucket to an offline JSON file.

        Args:
            file_path (str): The target file path for the JSON workspace.
            custom_bucket (Optional[HubStateBucket], optional): A filtered bucket to
                export instead of the full internal state. Defaults to None.
        """
        bucket = custom_bucket or self._state
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(bucket.model_dump_json(by_alias=True, exclude_none=True))

    def load_from_file(self, file_path: str, merge: bool = False) -> None:
        """
        Reads a JSON workspace file and replaces or merges the internal state.

        Args:
            file_path (str): The source file path to load from.
            merge (bool, optional): If True, merges the loaded state into the
                current state instead of replacing it. Defaults to False.
        """
        with open(file_path, encoding="utf-8") as f:
            data = f.read()
            new_state = HubStateBucket.model_validate_json(data)

            if not merge:
                self._state = new_state
            else:
                # Merge devices (deduplicate by ID)
                existing_macs = {(d.id.root if hasattr(d.id, "root") else d.id).upper() for d in self._state.devices if d.id}
                for d in new_state.devices:
                    mac = (d.id.root if hasattr(d.id, "root") else d.id).upper() if d.id else None
                    if mac and mac not in existing_macs:
                        self._state.devices.append(d)
                        existing_macs.add(mac)

                # Merge topology
                self._state.topology_roles.update(new_state.topology_roles)
                for k, v in new_state.topology_parents.items():
                    if k in self._state.topology_parents:
                        for p in v:
                            if p not in self._state.topology_parents[k]:
                                self._state.topology_parents[k].append(p)
                    else:
                        self._state.topology_parents[k] = v

                # Merge licenses (if any)
                existing_lic_macs = {(l.device_id.root if hasattr(l.device_id, "root") else l.device_id).upper() for l in self._state.licenses}
                for l in new_state.licenses:
                    mac = (l.device_id.root if hasattr(l.device_id, "root") else l.device_id).upper()
                    if mac not in existing_lic_macs:
                        self._state.licenses.append(l)
                        existing_lic_macs.add(mac)

    def _matches_filter(self, device: Device) -> bool:
        """
        Evaluates if a device matches the configured fleet filter.

        Args:
            device (Device): The device model to evaluate.

        Returns:
            bool: True if the device matches all filter criteria, False otherwise.
        """
        for key, value in self.fleet_filter.items():
            device_val = getattr(device, key, None)

            if isinstance(value, list):
                if isinstance(device_val, list):
                    if not any(item in value for item in device_val):
                        return False
                elif device_val not in value:
                    return False
            elif device_val != value:
                return False
        return True
