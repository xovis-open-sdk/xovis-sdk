"""
Xovis SDK - Network Management Resource

Operates within the Control Plane.
Provides comprehensive implementation for managing edge sensor networking,
including IPv4/IPv6, Remote Tunnels (Cloud Hub), 802.1X (EAPoL) Enterprise
Security, X.509 Truststores, and advanced Wireless scanning.
"""

from typing import TYPE_CHECKING, Any, Optional

from xovis.api.core.http import XovisHTTPClient
from xovis.models.device_auto import stable_models

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient


class NetworkManager:
    """
    Manages physical and logical network configurations on a Xovis device.

    Provides deep orchestration capabilities for Autonomous Maintenance (Module D),
    allowing agents to rebuild dropped Cloud Hub tunnels, rotate expiring X.509
    certificates, probe local Wi-Fi environments, and manage 802.1X authentication.
    """

    def __init__(self, http_client: XovisHTTPClient, client: Optional["DeviceClient"] = None) -> None:
        """
        Initializes the NetworkManager.

        Args:
            http_client (XovisHTTPClient): The resilient HTTP client.
            client (Optional[DeviceClient]): The parent DeviceClient instance.
        """
        self._http = http_client
        self._client = client
        self._base_path = "/api/v5/network"

    @property
    def models(self):
        """Returns the strictly validated Pydantic models for the current firmware."""
        return self._client.models if self._client else stable_models

    # --- GENERAL NETWORK STATE & HOSTNAME ---
    async def get_state(self) -> Any:
        """Retrieves the comprehensive operational state of all network interfaces."""
        response = await self._http.get(f"{self._base_path}/state")
        return self.models.NetworkState.model_validate(response.json())

    async def get_hostname(self) -> Any:
        """Retrieves the current hostname configuration."""
        response = await self._http.get(f"{self._base_path}/hostname")
        return self.models.Hostname.model_validate(response.json())

    async def update_hostname(self, hostname: Any) -> None:
        """Updates the sensor's logical hostname."""
        payload = hostname.model_dump(by_alias=True, exclude_unset=True, mode="json")
        await self._http.put(f"{self._base_path}/hostname", json=payload)

    async def reset_hostname(self) -> None:
        """Resets the hostname to the factory default (XS-SENSOR-[MAC])."""
        await self._http.delete(f"{self._base_path}/hostname")

    async def get_gigabit(self) -> Any:
        """Retrieves the Gigabit Ethernet enablement capability."""
        response = await self._http.get(f"{self._base_path}/gigabit")
        return self.models.GigabitEnabled.model_validate(response.json())

    async def update_gigabit(self, gigabit: Any) -> None:
        """Enables or disables Gigabit Ethernet capability."""
        payload = gigabit.model_dump(by_alias=True, exclude_unset=True, mode="json")
        await self._http.put(f"{self._base_path}/gigabit", json=payload)

    # --- IPV4 & IPV6 CONFIGURATION ---
    async def get_ipv4(self) -> Any:
        """Retrieves the current IPv4 network configuration (Static/DHCP)."""
        response = await self._http.get(f"{self._base_path}/ipv4")
        return self.models.NetworkIpv4Settings.model_validate(response.json())

    async def update_ipv4(self, settings: Any) -> None:
        """CRITICAL: Updates IPv4 configuration. May sever active connections."""
        payload = settings.model_dump(by_alias=True, exclude_unset=True, mode="json")
        await self._http.put(f"{self._base_path}/ipv4", json=payload)

    async def reset_ipv4(self) -> None:
        """CRITICAL: Resets IPv4 to factory defaults (DHCP enabled)."""
        await self._http.delete(f"{self._base_path}/ipv4")

    async def get_ipv6(self) -> Any:
        """Retrieves the current IPv6 network configuration."""
        response = await self._http.get(f"{self._base_path}/ipv6")
        return self.models.NetworkIpv6Settings.model_validate(response.json())

    async def update_ipv6(self, settings: Any) -> None:
        """CRITICAL: Updates IPv6 configuration."""
        payload = settings.model_dump(by_alias=True, exclude_unset=True, mode="json")
        await self._http.put(f"{self._base_path}/ipv6", json=payload)

    async def reset_ipv6(self) -> None:
        """CRITICAL: Resets IPv6 to factory defaults (Disabled)."""
        await self._http.delete(f"{self._base_path}/ipv6")

    # --- REMOTE CONNECTIONS (HUB TUNNELS) ---
    async def get_all_remotes(self) -> Any:
        """Retrieves configurations for all defined remote connections (Cloud Tunnels)."""
        response = await self._http.get(f"{self._base_path}/remotes")
        # We use a custom parser to handle relative URLs in the 'uri' field,
        # which Pydantic's AnyUrl strictly rejects even in non-strict mode.
        data = response.json()
        if "remotes" in data:
            for remote in data["remotes"]:
                if "uri" in remote and isinstance(remote["uri"], str) and remote["uri"].startswith("/"):
                    remote["uri"] = f"http://localhost{remote['uri']}"
        return self.models.RemoteConnections.model_validate(data)

    async def create_remote(self, remote: Any) -> Any:
        """
        Creates a new remote connection (e.g., establishing a new Hub Tunnel).
        Automatically starts the connection upon creation.
        """
        payload = remote.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.post(f"{self._base_path}/remotes", json=payload)
        data = response.json()
        if "uri" in data and isinstance(data["uri"], str) and data["uri"].startswith("/"):
            data["uri"] = f"http://localhost{data['uri']}"
        return self.models.IndexedRemoteConnection.model_validate(data)

    async def create_remote_from_config(self, config: Any) -> Any:
        """Creates a new remote connection using a base64-encoded configuration payload."""
        payload = config.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.post(f"{self._base_path}/remotes/configuration", json=payload)
        data = response.json()
        if "uri" in data and isinstance(data["uri"], str) and data["uri"].startswith("/"):
            data["uri"] = f"http://localhost{data['uri']}"
        return self.models.IndexedRemoteConnection.model_validate(data)

    async def get_remote(self, remote_id: int) -> Any:
        """Retrieves a specific remote connection configuration."""
        response = await self._http.get(f"{self._base_path}/remotes/{remote_id}")
        data = response.json()
        if "uri" in data and isinstance(data["uri"], str) and data["uri"].startswith("/"):
            data["uri"] = f"http://localhost{data['uri']}"
        return self.models.IndexedRemoteConnection.model_validate(data)

    async def update_remote(self, remote_id: int, remote: Any) -> Any:
        """Updates an existing remote connection."""
        payload = remote.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put(f"{self._base_path}/remotes/{remote_id}", json=payload)
        data = response.json()
        if "uri" in data and isinstance(data["uri"], str) and data["uri"].startswith("/"):
            data["uri"] = f"http://localhost{data['uri']}"
        return self.models.IndexedRemoteConnection.model_validate(data)

    async def delete_remote(self, remote_id: int) -> None:
        """BLOCKED: Deletes a remote connection, severing the management tunnel."""
        await self._http.delete(f"{self._base_path}/remotes/{remote_id}")

    async def get_all_remotes_state(self) -> Any:
        """Retrieves the connectivity status for all remote tunnels."""
        response = await self._http.get(f"{self._base_path}/remotes/state")
        return self.models.RemoteConnectionStates.model_validate(response.json())

    async def get_remote_state(self, remote_id: int) -> Any:
        """Retrieves the connectivity status of a specific remote tunnel."""
        response = await self._http.get(f"{self._base_path}/remotes/{remote_id}/state")
        return self.models.RemoteConnectionState.model_validate(response.json())

    # --- XOVIS SUPPORT & REMOTE SERVICES ---
    async def get_xovis_support_state(self) -> Any:
        """Retrieves the state of the Xovis Tier 3 Support Remote Connection."""
        response = await self._http.get(f"{self._base_path}/remotes/xovissupport")
        return self.models.XovisRemoteSupportState.model_validate(response.json())

    async def update_xovis_support(self, ctrl: Any) -> None:
        """Controls the enablement of the Xovis Support Remote Connection."""
        payload = ctrl.model_dump(by_alias=True, exclude_unset=True, mode="json")
        await self._http.put(f"{self._base_path}/remotes/xovissupport", json=payload)

    async def get_remote_services_config(self) -> Any:
        """Retrieves the overarching configuration for Xovis Remote Services (IoT)."""
        response = await self._http.get(f"{self._base_path}/remotes/services/config")
        return self.models.RemoteServicesSettings.model_validate(response.json())

    async def update_remote_services_config(self, settings: Any) -> None:
        """Updates the Xovis Remote Services configuration."""
        payload = settings.model_dump(by_alias=True, exclude_unset=True, mode="json")
        await self._http.put(f"{self._base_path}/remotes/services/config", json=payload)

    async def reset_remote_services_config(self) -> None:
        """Resets the Xovis Remote Services configuration."""
        await self._http.delete(f"{self._base_path}/remotes/services/config")

    async def get_remote_services_state(self) -> Any:
        """Retrieves the connectivity status of Xovis Remote Services."""
        response = await self._http.get(f"{self._base_path}/remotes/services/state")
        return self.models.RemoteServicesState.model_validate(response.json())

    # --- 802.1X EAPoL & IDENTITY ---
    async def get_eapol_config(self) -> Any:
        """Retrieves the 802.1X EAPoL Supplicant configuration."""
        response = await self._http.get(f"{self._base_path}/eapol/config")
        return self.models.EapolConfig.model_validate(response.json())

    async def update_eapol_config(self, config: Any) -> Any:
        """CRITICAL: Updates 802.1X configuration. May cause network drops."""
        payload = config.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put(f"{self._base_path}/eapol/config", json=payload)
        return self.models.EapolConfig.model_validate(response.json())

    async def reset_eapol_config(self) -> Any:
        """CRITICAL: Resets 802.1X configuration to factory defaults."""
        response = await self._http.delete(f"{self._base_path}/eapol/config")
        return self.models.EapolConfig.model_validate(response.json())

    async def get_eapol_state(self) -> Any:
        """Retrieves the authentication state of the 802.1X Supplicant."""
        response = await self._http.get(f"{self._base_path}/eapol/state")
        return self.models.EapolState.model_validate(response.json())

    async def get_eapol_keystore(self) -> Any:
        """Retrieves the configured X.509 client identity for 802.1X."""
        response = await self._http.get(f"{self._base_path}/eapol/x509/keystore")
        if response.status_code == 204:
            return None
        return self.models.X509Certificate.model_validate(response.json())

    async def update_eapol_keystore(self, pem_binary: bytes) -> Any:
        """
        Uploads a new X.509 client identity (Certificate + RSA Key).
        Must be formatted as PEM. Uses strict binary streaming.
        """
        headers = {"Content-Type": "application/octet-stream"}
        response = await self._http.put(f"{self._base_path}/eapol/x509/keystore", content=pem_binary, headers=headers)
        return self.models.X509Certificate.model_validate(response.json())

    async def delete_eapol_keystore(self) -> None:
        """Removes the X.509 client identity from the EAPoL Supplicant."""
        await self._http.delete(f"{self._base_path}/eapol/x509/keystore")

    # --- X.509 TRUSTSTORE ---
    async def get_truststore_certs(self) -> Any:
        """Retrieves all installed X.509 certificates in the truststore."""
        response = await self._http.get(f"{self._base_path}/x509/truststore")
        return self.models.X509Certificates.model_validate(response.json())

    async def install_truststore_cert(self, cert_binary: bytes) -> Any:
        """Installs a new X.509 certificate to the truststore."""
        headers = {"Content-Type": "application/octet-stream"}
        response = await self._http.post(f"{self._base_path}/x509/truststore", content=cert_binary, headers=headers)
        return self.models.X509Certificate.model_validate(response.json())

    async def reset_truststore(self) -> None:
        """Resets the truststore to factory default certificates."""
        await self._http.delete(f"{self._base_path}/x509/truststore")

    async def get_truststore_config(self) -> Any:
        """Retrieves the truststore configuration (e.g., use defaults)."""
        response = await self._http.get(f"{self._base_path}/x509/truststore/config")
        return self.models.X509TruststoreConfig.model_validate(response.json())

    async def update_truststore_config(self, config: Any) -> Any:
        """Updates the truststore configuration."""
        payload = config.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put(f"{self._base_path}/x509/truststore/config", json=payload)
        return self.models.X509TruststoreConfig.model_validate(response.json())

    async def get_truststore_cert(self, fingerprint: str) -> Any:
        """Retrieves details of a specific X.509 certificate by its SHA-1 fingerprint."""
        response = await self._http.get(f"{self._base_path}/x509/truststore/{fingerprint}")
        return self.models.X509Certificate.model_validate(response.json())

    async def delete_truststore_cert(self, fingerprint: str) -> None:
        """Removes a specific X.509 certificate from the truststore."""
        await self._http.delete(f"{self._base_path}/x509/truststore/{fingerprint}")

    # --- WIRELESS (WLAN) SCANNING & CONFIGURATION ---
    async def get_wireless(self) -> Any:
        """Retrieves the global wireless networking configuration."""
        response = await self._http.get(f"{self._base_path}/wireless")
        return self.models.WlanSettings.model_validate(response.json())

    async def update_wireless(self, settings: Any) -> Any:
        """Updates the global wireless networking configuration."""
        payload = settings.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put(f"{self._base_path}/wireless", json=payload)
        return self.models.WlanSettings.model_validate(response.json())

    async def reset_wireless(self) -> Any:
        """Resets global wireless networking configuration to factory defaults."""
        response = await self._http.delete(f"{self._base_path}/wireless")
        return self.models.WlanSettings.model_validate(response.json())

    async def get_wireless_state(self) -> Any:
        """Retrieves the current state and connection metrics of wireless networking."""
        response = await self._http.get(f"{self._base_path}/wireless/state")
        return self.models.StateResult.model_validate(response.json())

    async def get_wireless_networks(self) -> Any:
        """Retrieves all configured wireless network profiles."""
        response = await self._http.get(f"{self._base_path}/wireless/networks")
        return self.models.WlanNetworks.model_validate(response.json())

    async def create_wireless_network(self, network: Any) -> Any:
        """Adds a new wireless network profile."""
        payload = network.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.post(f"{self._base_path}/wireless/networks", json=payload)
        return self.models.WlanNetwork.model_validate(response.json())

    async def delete_all_wireless_networks(self) -> Any:
        """Removes all configured wireless network profiles."""
        response = await self._http.delete(f"{self._base_path}/wireless/networks")
        return self.models.WlanNetworks.model_validate(response.json())

    async def get_wireless_network(self, network_id: int) -> Any:
        """Retrieves a specific wireless network profile."""
        response = await self._http.get(f"{self._base_path}/wireless/networks/{network_id}")
        return self.models.WlanNetwork.model_validate(response.json())

    async def update_wireless_network(self, network_id: int, network: Any) -> Any:
        """Updates a specific wireless network profile."""
        payload = network.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put(f"{self._base_path}/wireless/networks/{network_id}", json=payload)
        return self.models.WlanNetwork.model_validate(response.json())

    async def delete_wireless_network(self, network_id: int) -> Any:
        """Removes a specific wireless network profile."""
        response = await self._http.delete(f"{self._base_path}/wireless/networks/{network_id}")
        return self.models.WlanNetwork.model_validate(response.json())

    async def test_wireless_network(self, network_id: int) -> None:
        """Triggers a connection test for a specific wireless profile."""
        await self._http.post(f"{self._base_path}/wireless/networks/{network_id}/test")

    async def get_wireless_test_result(self, network_id: int) -> Any:
        """Retrieves the result of a wireless connection test."""
        response = await self._http.get(f"{self._base_path}/wireless/networks/{network_id}/test")
        return self.models.ScanResult.model_validate(response.json())

    async def trigger_wireless_scan(self) -> None:
        """Triggers an active scan for nearby IEEE 802.11 Access Points."""
        await self._http.post(f"{self._base_path}/wireless/scan")

    async def get_wireless_scan_results(self) -> Any:
        """Retrieves the results of the latest wireless network scan."""
        response = await self._http.get(f"{self._base_path}/wireless/scan")
        return self.models.ScanResults.model_validate(response.json())

    # --- PROXY & MDNS ---
    async def get_proxy(self) -> Any:
        """Retrieves the current network proxy configuration."""
        response = await self._http.get(f"{self._base_path}/proxy")
        return self.models.NetworkProxy.model_validate(response.json())

    async def update_proxy(self, proxy: Any) -> None:
        """Updates the network proxy configuration."""
        payload = proxy.model_dump(by_alias=True, exclude_unset=True, mode="json")
        await self._http.put(f"{self._base_path}/proxy", json=payload)

    async def reset_proxy(self) -> None:
        """Deletes the current proxy configuration."""
        await self._http.delete(f"{self._base_path}/proxy")

    async def get_mdns_config(self) -> Any:
        """Retrieves the mDNS (Multicast DNS) configuration."""
        response = await self._http.get(f"{self._base_path}/mdns/config")
        return self.models.MdnsConfig.model_validate(response.json())

    async def update_mdns_config(self, config: Any) -> None:
        """Updates the mDNS configuration."""
        payload = config.model_dump(by_alias=True, exclude_unset=True, mode="json")
        await self._http.put(f"{self._base_path}/mdns/config", json=payload)

    async def get_mdns_state(self) -> Any:
        """Retrieves the currently discovered mDNS services in the local network."""
        response = await self._http.get(f"{self._base_path}/mdns/state")
        return self.models.MdnsState.model_validate(response.json())

    # --- PIP (Product Improvement Program) ---
    async def get_pip_config(self) -> Any:
        """Retrieves the Xovis PIP (Product Improvement Program) configuration."""
        response = await self._http.get(f"{self._base_path}/pip")
        return self.models.PipSettings.model_validate(response.json())

    async def update_pip_config(self, settings: Any) -> None:
        """Updates the Xovis PIP configuration."""
        payload = settings.model_dump(by_alias=True, exclude_unset=True, mode="json")
        await self._http.put(f"{self._base_path}/pip", json=payload)

    async def get_pip_state(self) -> Any:
        """Retrieves the state and quota usage of the Xovis PIP service."""
        response = await self._http.get(f"{self._base_path}/pip/status")
        return self.models.PipState.model_validate(response.json())

    async def reset_pip_quota(self) -> None:
        """Resets the monthly used PIP quota."""
        await self._http.post(f"{self._base_path}/pip_quota_reset")
