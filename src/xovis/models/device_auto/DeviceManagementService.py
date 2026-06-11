"""
Xovis SDK - Device Management Service Models

Operates within the Control Plane.
Provides auto-generated Pydantic V2 models for local edge sensor
device management, status reporting, and service configuration.
"""

from __future__ import annotations

from pydantic import BaseModel, RootModel

from . import (
    GetDeviceConfigurationResponseData,
    GetDeviceInformationResponseData,
    GetDeviceStatusResponseData,
    GetServiceInformationResponseData,
    GetServiceStatusResponseData,
    IBISIPInt,
    OperationErrorMessage,
)


class SetDeviceConfigurationRequest(BaseModel):
    """Payload for updating device-wide configuration parameters."""

    DeviceID: IBISIPInt | None = None


class GetDeviceConfigurationResponse(
    RootModel[GetDeviceConfigurationResponseData | OperationErrorMessage]
):
    """Envelope for device configuration retrieval, supporting error polymorphic responses."""

    root: GetDeviceConfigurationResponseData | OperationErrorMessage


class GetDeviceInformationResponse(
    RootModel[GetDeviceInformationResponseData | OperationErrorMessage]
):
    """Envelope for static device hardware and identity metadata."""

    root: GetDeviceInformationResponseData | OperationErrorMessage


class GetDeviceStatusResponse(RootModel[GetDeviceStatusResponseData | OperationErrorMessage]):
    """Envelope for real-time device health and operational state."""

    root: GetDeviceStatusResponseData | OperationErrorMessage


class GetServiceInformationResponse(
    RootModel[GetServiceInformationResponseData | OperationErrorMessage]
):
    """Envelope for service-specific metadata and capabilities."""

    root: GetServiceInformationResponseData | OperationErrorMessage


class GetServiceStatusResponse(RootModel[GetServiceStatusResponseData | OperationErrorMessage]):
    """Envelope for monitoring the runtime status of internal sensor services."""

    root: GetServiceStatusResponseData | OperationErrorMessage
