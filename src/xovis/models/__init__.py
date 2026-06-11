"""
Xovis SDK - REPL Accessors & Pydantic Injection

Operates within the Developer Experience (DX) boundary of the State & Topology Plane.
Provides read-only dynamic accessors for object discovery in interactive environments
(Jupyter/REPL) and injects discovery properties into auto-generated Pydantic V2 models.
"""

import re
from collections.abc import Iterable
from typing import Any, List

from .device import (
    AgentConfig,
    BlockedSpace,
    CountAction,
    Counter,
    CounterName,
    CounterType,
    CountEvent,
    DataConfig,
    DataFormat,
    DataFormatType,
    DataPushAgent,
    DataPushAgentCollection,
    DataPushConnection,
    DataPushConnectionCollection,
    DataPushFilters,
    DataPushProtocol,
    DataPushStatus,
    DataPushStatusCollection,
    DataPushTestResponse,
    DataPushTriggerConfig,
    DataPushTriggerInfo,
    DataPushTriggerStatus,
    DataPushTriggerType,
    DataPushType,
    Filter,
    FTPConfig,
    FTPDirectoryMode,
    FTPFileMode,
    HeatHeightMap,
    HistoryLogics,
    HistoryMeasurement,
    HistoryQuery,
    HistoryStatus,
    HTTPAuthMethod,
    HTTPConfig,
    HTTPHeaderField,
    IntervalType,
    Layer,
    Line,
    Logic,
    LogicType,
    Modifier,
    MQTTConfig,
    ObjectType,
    PathStitchingZone,
    RetryConfig,
    RetryMode,
    SceneMask,
    SceneMaskType,
    Scheduler,
    SchedulerType,
    SFTPConfig,
    StartStopPoints,
    StartStopQuery,
    StorageCapacity,
    StoredData,
    StoredDataRecord,
    SystemInfo,
    TCPConfig,
    TCPUDPMode,
    TimeFormat,
    TransmitStatus,
    TriggerType,
    UDPConfig,
    ViewMask,
    ViewMaskType,
    XovisGeometry,
    Zone,
)
from .device_auto import (
    AgentConfigCollection,
    ConnectionConfigCollection,
    CounterCollection,
    LogicCollection,
    ModifierCollection,
    SceneGeometries,
)
from .hub_device import HubDevice


class REPLAccessor:
    """
    Read-only dynamic accessor allowing object discovery via dot-notation.

    Wraps Pydantic collections to provide fast, interactive exploration of cached
    hardware topologies without mutating the underlying Desired State Configuration.

    Attributes:
        _items (dict): Internal mapping of sanitized names to resource objects.
    """

    def __init__(self, elements: Iterable[Any]) -> None:
        """
        Initializes the accessor by sanitizing and mapping element names.

        Args:
            elements (Iterable[Any]): A collection of instantiated Pydantic models.
        """
        self._items = {}
        for item in elements:
            name = getattr(item, "name", None)
            if name:
                safe_name = re.sub(r"\W+", "_", name).strip("_")
                if safe_name and safe_name[0].isdigit():
                    safe_name = f"_{safe_name}"
                self._items[safe_name] = item

    def __getattr__(self, key: str) -> Any:
        """
        Retrieves a hardware resource by its sanitized name.

        Args:
            key (str): The sanitized name of the resource.

        Returns:
            Any: The target Pydantic resource model.

        Raises:
            AttributeError: If the resource name does not exist in the collection.
        """
        if key in self._items:
            return self._items[key]
        raise AttributeError(f"Resource '{key}' not found. Available names: {list(self._items.keys())}")

    def __dir__(self) -> list[str]:
        """
        Extends directory listing to trigger IDE/REPL autocomplete dropdowns.

        Returns:
            List[str]: Combined list of standard attributes and dynamic resource keys.
        """
        return super().__dir__() + list(self._items.keys())

    def __repr__(self) -> str:
        """
        Returns a structured string representation of the accessor.

        Returns:
            str: The accessor representation highlighting available resources.
        """
        return f"<REPLAccessor resources={list(self._items.keys())}>"


def _by_name_property(self: Any) -> REPLAccessor:
    """
    Instantiates a REPLAccessor to bypass Pydantic V2 strict mutation locks.

    Safely unwraps RootModels to ensure compatibility with polymorphic hardware endpoints.

    Args:
        self (Any): The Pydantic collection instance.

    Returns:
        REPLAccessor: A dynamic accessor for the collection's validated items.
    """
    items = getattr(self, "root", self)
    return REPLAccessor(items)


AgentConfigCollection.by_name = property(_by_name_property)
ConnectionConfigCollection.by_name = property(_by_name_property)
SceneGeometries.by_name = property(_by_name_property)
LogicCollection.by_name = property(_by_name_property)
ModifierCollection.by_name = property(_by_name_property)
CounterCollection.by_name = property(_by_name_property)
