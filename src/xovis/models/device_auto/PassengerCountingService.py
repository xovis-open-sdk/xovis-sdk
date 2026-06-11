"""
Xovis SDK - Passenger Counting Service Models

Operates within the Control Plane.
Provides auto-generated Pydantic V2 models for retrieving passenger
counting analytics and aggregated flow data from edge sensors.
"""

from __future__ import annotations

from pydantic import RootModel

from . import AllData, OperationErrorMessage


class GetAllDataResponse(RootModel[AllData | OperationErrorMessage]):
    """Envelope for comprehensive passenger counting data retrieval."""

    root: AllData | OperationErrorMessage
