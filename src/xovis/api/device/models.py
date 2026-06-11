"""
Xovis SDK - Device Plane Pydantic Models

This module resides within the State & Topology Plane, defining the core data
structures for configuration synchronization, topology node representation,
and resilient bulk execution results.
"""

from enum import Enum
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class CacheStrategy(str, Enum):
    """
    Execution strategies for the Smart Configuration Synchronizer.

    Defines how the `ConfigCacheManager` interacts with the edge hardware
    to maintain state consistency.
    """

    MANUAL = "MANUAL"
    LAZY_TTL = "LAZY_TTL"
    BACKGROUND_WATCHER = "BACKGROUND_WATCHER"


class TopologyNodeInfo(BaseModel):
    """
    Representation of a node strictly tied to a Multisensor Graph topology.
    """

    model_config = ConfigDict(extra="ignore")

    mac_address: str
    ip_address: Optional[str] = None
    name: Optional[str] = None
    group: Optional[str] = None
    status: Optional[str] = None
    reference: bool = False


class MSGraph(BaseModel):
    """
    A Layer 2.5 directed graph mapping the master-slave relationships.
    """

    master_mac: str
    children: list[TopologyNodeInfo] = Field(default_factory=list)
    ip_map: dict[str, str] = Field(default_factory=dict)
    # Support for multiple potential parent clusters if a child is incorrectly assigned
    # or in future multi-master edge cases.
    alternative_masters: list[str] = Field(default_factory=list)


class BulkResult(BaseModel, Generic[T]):
    """
    A generic-aware, highly resilient outcome report from a concurrent batch execution.

    Type inference guarantees flawless IDE auto-completion for the success payload (T).
    This model is used to report results from fleet orchestration tasks.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool = True
    result: Optional[T] = None
    error: Optional[str] = None
