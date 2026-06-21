"""
Xovis SDK - ITxPT Management Resource

Operates within the Control Plane.
Provides comprehensive implementation for managing Information Technology
for Public Transport (ITxPT) configurations. Orchestrates Automatic Passenger
Counting (APC) doors, Time Discovery (SNTP), mDNS TXT broadcasts, and extracts
raw inventory/APC telemetry directly from the edge sensor.
"""

from typing import TYPE_CHECKING, Any

from xovis.api.core.http import XovisHTTPClient
from xovis.models.device_auto import stable_models

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient


class ITxPTManager:
    """
    Manages ITxPT configurations, networking discovery, and APC doors.

    This manager orchestrates public transport services on the sensor. It allows
    autonomous agents to diagnose vehicle time synchronization (SNTP), configure
    mDNS broadcasts, and fetch real-time passenger counts directly from the
    ITxPT service endpoints.
    """

    def __init__(self, http_client: XovisHTTPClient, client: "DeviceClient" = None) -> None:
        """
        Initializes the ITxPTManager.

        Args:
            http_client (XovisHTTPClient): The resilient HTTP client.
            client (DeviceClient): The parent DeviceClient instance.
        """
        self._http = http_client
        self._client = client
        self._base_path = "/api/v5/itxpt"

    @property
    def models(self):
        """Returns the strictly validated Pydantic models for the current firmware."""
        return self._client.models if self._client else stable_models

    # --- GLOBAL CONFIGURATION & STATE ---
    async def get_config(self) -> Any:
        """
        Retrieves the global ITxPT configuration (e.g., protocol version, vehicle ID source).
        """
        response = await self._http.get(f"{self._base_path}/config")
        return self.models.ItxptConfig.model_validate(response.json())

    async def update_config(self, config: Any) -> Any:
        """
        Updates the global ITxPT configuration.
        """
        response = await self._http.put(f"{self._base_path}/config", json=config)
        return self.models.ItxptConfig.model_validate(response.json())

    async def get_state(self) -> Any:
        """
        Retrieves the current ITxPT operational state and resolved Vehicle ID.
        """
        response = await self._http.get(f"{self._base_path}/state")
        return self.models.ItxptState.model_validate(response.json())

    async def get_services_state(self) -> Any:
        """
        Retrieves the runtime networking state of all ITxPT sub-services,
        including current consumers subscribed to the APC feed.
        """
        response = await self._http.get(f"{self._base_path}/services/state")
        return self.models.ItxptServicesState.model_validate(response.json())

    # --- TIME DISCOVERY (SNTP) ---
    async def get_time_config(self) -> Any:
        """
        Retrieves the ITxPT time discovery configuration (SNTP enable toggle).
        """
        response = await self._http.get(f"{self._base_path}/config/time")
        return self.models.ItxptTimeConfig.model_validate(response.json())

    async def update_time_config(self, config: Any) -> Any:
        """
        Updates the ITxPT time discovery configuration.
        """
        response = await self._http.put(f"{self._base_path}/config/time", json=config)
        return self.models.ItxptTimeConfig.model_validate(response.json())

    async def get_time_status(self) -> Any:
        """
        Retrieves the runtime status of the vehicle time discovery.
        Crucial for agents to verify if the sensor has found an SNTP server.
        """
        response = await self._http.get(f"{self._base_path}/time/sntp_server")
        return self.models.ItxptTime.model_validate(response.json())

    # --- mDNS TXT RECORDS ---
    async def get_txt_records(self) -> Any:
        """
        Retrieves the extra TXT records published in the ITxPT mDNS broadcast.
        """
        response = await self._http.get(f"{self._base_path}/config/txt")
        return self.models.ItxptConfigTxt.model_validate(response.json())

    async def update_txt_records(self, txt_records: Any) -> Any:
        """
        Updates the extra TXT records for the mDNS broadcast.
        """
        response = await self._http.put(f"{self._base_path}/config/txt", json=txt_records)
        return self.models.ItxptConfigTxt.model_validate(response.json())

    # --- CUSTOM CONFIGURATIONS (BLOB) ---
    async def get_custom_configurations(self) -> Any:
        """
        Retrieves custom free text configurations specific to ITxPT deployments.
        """
        response = await self._http.get("/api/v5/blob/store/itxpt_custom_configurations.json")
        return self.models.ItxptCustomConfigurations.model_validate(response.json())

    async def update_custom_configurations(self, custom_configs: Any) -> Any:
        """
        Updates the custom free text configurations blob.
        """
        await self._http.put("/api/v5/blob/store/itxpt_custom_configurations.json", json=custom_configs)

    # --- APC DOOR MANAGEMENT ---
    async def get_all_doors(self) -> Any:
        """Retrieves all defined ITxPT APC door configurations."""
        response = await self._http.get(f"{self._base_path}/config/doors")
        return self.models.ItxptConfigDoorCollection.model_validate(response.json())

    async def create_door(self, door: Any) -> Any:
        """Creates a new ITxPT APC door configuration."""
        response = await self._http.post(f"{self._base_path}/config/doors", json=door)
        return self.models.ItxptConfigDoorApcPathRequired.model_validate(response.json())

    async def delete_all_doors(self) -> None:
        """Deletes all existing ITxPT APC door configurations."""
        await self._http.delete(f"{self._base_path}/config/doors")

    async def get_door(self, door_id: int) -> Any:
        """Retrieves a specific APC door configuration."""
        response = await self._http.get(f"{self._base_path}/config/doors/{door_id}")
        return self.models.ItxptConfigDoorApcPathRequired.model_validate(response.json())

    async def update_door(self, door_id: int, door: Any) -> Any:
        """Updates an existing APC door configuration."""
        response = await self._http.put(f"{self._base_path}/config/doors/{door_id}", json=door)
        return self.models.ItxptConfigDoorApcPathRequired.model_validate(response.json())

    async def delete_door(self, door_id: int) -> None:
        """Deletes a specific APC door configuration."""
        await self._http.delete(f"{self._base_path}/config/doors/{door_id}")

    # --- RAW DATA ENDPOINTS (TELEMETRY) ---
    async def get_apc_data(self) -> Any:
        """
        Retrieves the raw PassengerDoorCountDelivery telemetry directly
        from the ITxPT APC service endpoint.

        Note: The return format is XML/dictated by ITxPT standards. Pydantic
        validation relies on the translated JSON schema.
        """
        # The ITxPT standard specifies this endpoint for APC polling
        response = await self._http.get(f"{self._base_path}/services/apc/passengerdoorcount")

        # Depending on content negotiation, this may return XML. Assuming the client
        # handles standard JSON decoding if application/json is requested.
        try:
            return self.models.PassengerDoorCountDelivery.model_validate(response.json())
        except Exception:
            return response.text

    async def get_inventory_info(self) -> Any:
        """
        Retrieves the raw ModuleDelivery inventory telemetry (Hardware/Services info)
        directly from the ITxPT inventory service endpoint.
        """
        response = await self._http.get(f"{self._base_path}/services/inventory/moduleinfo.xml")

        try:
            return self.models.ModulesDelivery.model_validate(response.json())
        except Exception:
            return response.text
