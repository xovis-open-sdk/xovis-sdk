"""
Xovis SDK - Hub Device Models

Operates within the Control Plane.
Provides strictly validated Pydantic V2 RootModels and enumerations directly derived
from the Xovis HUB Cloud OpenAPI specification, incorporating strict AI privacy tags.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, RootModel, StringConstraints

MACAddress = Annotated[str, StringConstraints(pattern=r"^([0-9A-Fa-f]{2}[:]){5}([0-9A-Fa-f]{2})$")]


class Uuid(RootModel[UUID]):
    """Strictly validated UUID payload."""

    root: UUID = Field(..., examples=["c7b27fe9-53d8-43f4-8654-c37effeb8908"])


class DeviceId(RootModel[MACAddress]):
    """Strictly validated MAC Address wrapper."""

    root: MACAddress = Field(..., examples=["12:34:56:78:9A:BC"])


class DeviceState(Enum):
    """Lifecycle state of a device within the HUB."""

    MANAGED = "MANAGED"
    UNMANAGED = "UNMANAGED"


class DeviceStatus(Enum):
    """Network connection status of the edge sensor."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class Device(BaseModel):
    """Comprehensive hardware, telemetry, and network state of a managed sensor."""

    device_name: str | None = Field(None, examples=["Xovis Kitchen"], json_schema_extra={"ai_privacy": "HASH"})
    device_group: str | None = Field(None, examples=["Office Xovis"], json_schema_extra={"ai_privacy": "HASH"})
    customer: str | None = Field(None, examples=["Xovis"], json_schema_extra={"ai_privacy": "HASH"})
    categories: list[str] | None = None
    type: str | None = Field(None, examples=["PC2S"])
    id: DeviceId | None = Field(None, json_schema_extra={"ai_privacy": "HASH"})
    ip: str | None = Field(None, examples=["10.10.10.2"], json_schema_extra={"ai_privacy": "BLOCK"})
    firmware_version: str | None = Field(None, examples=["5.0.3-9738700b2d"])
    device_status: DeviceStatus | None = None
    tilt_measured_alpha_deg: float | None = Field(None, examples=[-1.4])
    tilt_measured_beta_deg: float | None = Field(None, examples=[-2.4])
    tilt_active_alpha_deg: float | None = Field(None, examples=[-1.3])
    tilt_active_beta_deg: float | None = Field(None, examples=[-2.3])
    mounting_height_m: float | None = Field(None, examples=[2.42])
    privacy_mode: int | None = Field(None, examples=[1])
    last_config_refresh: AwareDatetime | None = Field(None, examples=["2023-02-08T18:04:28Z"])


class DeviceUiAccess(BaseModel):
    """Temporary authenticated access token for tunneling into a remote sensor."""

    device_ui_link: str | None = Field(
        None,
        examples=["https://sensor-connect.cloudapp.azure.com/api/tunnel/AA:BB/fullui?otp=ompOlGw..."],
    )


class DevicesCustomerAssignment(BaseModel):
    """Payload for executing bulk customer assignments across a fleet."""

    device_ids: list[DeviceId]
    customer_name: str = Field(..., examples=["customer name"])


class DevicesRequest(BaseModel):
    """Standardized fleet array payload for bulk requests."""

    device_ids: list[DeviceId]


class DevicesCategoriesAssignment(BaseModel):
    """Payload for modifying organizational categories across multiple devices."""

    device_ids: list[DeviceId]
    categories_to_add: list[str] | None = None
    categories_to_remove: list[str] | None = None


class DevicesResponse(BaseModel):
    """Paginated or bulk array response containing managed device states."""

    items: list[Device] | None = None


class HubDevice(BaseModel):
    """
    Represents a managed edge sensor provisioned within a Xovis HUB Cloud tenant.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    device_id: str = Field(alias="deviceId", json_schema_extra={"ai_privacy": "BLOCK"})
    state: str = Field(description="Connection state, e.g., 'MANAGED' or 'OFFLINE'")
    sw_version: str = Field(alias="swVersion", default="Unknown")
    customer_name: str | None = Field(alias="customerName", default=None, json_schema_extra={"ai_privacy": "BLOCK"})
