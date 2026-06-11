"""
Xovis SDK - Door State Service Models

Operates within the Control Plane.
Provides auto-generated Pydantic V2 models for monitoring door
opening and closing states on edge sensors.
"""

from __future__ import annotations

from pydantic import RootModel

from . import GetDoorOpenStatesResponseData, OperationErrorMessage


class GetDoorOpenStatesResponse(RootModel[GetDoorOpenStatesResponseData | OperationErrorMessage]):
    """Envelope for door state telemetry, supporting error polymorphic responses."""

    root: GetDoorOpenStatesResponseData | OperationErrorMessage
