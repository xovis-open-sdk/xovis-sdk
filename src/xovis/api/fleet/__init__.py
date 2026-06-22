"""
Xovis SDK - Fleet Orchestration Plane.

This module provides abstractions for orchestrating multiple DeviceClient
instances, such as the DeviceGroup, which enables bulk operations
and aggregated caching.
"""

from .directory import HubFleetDirectory
from .group import DeviceGroup
from .models import BulkOperationResult

__all__ = ["DeviceGroup", "BulkOperationResult", "HubFleetDirectory"]
