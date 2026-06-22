from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from xovis.api.device.cache import BulkDeviceFacade
    from xovis.api.device.resources.analytics import AnalyticsManager
    from xovis.api.device.resources.datapush import DataPushManager
    from xovis.api.device.resources.history import HistoryManager
    from xovis.api.device.resources.itxpt import ITxPTManager
    from xovis.api.device.resources.network import NetworkManager
    from xovis.api.device.resources.privacy import PrivacyManager
    from xovis.api.device.resources.scene import SceneManager
    from xovis.api.device.resources.system import SystemManager
    from xovis.api.device.resources.time_config import TimeManager
    from xovis.api.device.resources.update import UpdateManager
    from xovis.api.device.resources.users import UsersManager
    from xovis.api.device.topology import MultisensorsManager, TopologyManager

class BaseControlPlane:
    """
    A DRY mixin that provides explicitly typed Control Plane endpoint properties
    for IDE autosuggestions. At runtime, subclasses (like DeviceGroup and
    ChildDevicesAccessor) implement these dynamically via __getattr__, 
    while DeviceClient provides concrete property implementations.
    """
    if TYPE_CHECKING:
        @property
        def datapush(self) -> Union["DataPushManager", "BulkDeviceFacade"]: ...
        @property
        def analytics(self) -> Union["AnalyticsManager", "BulkDeviceFacade"]: ...
        @property
        def system(self) -> Union["SystemManager", "BulkDeviceFacade"]: ...
        @property
        def network(self) -> Union["NetworkManager", "BulkDeviceFacade"]: ...
        @property
        def time(self) -> Union["TimeManager", "BulkDeviceFacade"]: ...
        @property
        def update(self) -> Union["UpdateManager", "BulkDeviceFacade"]: ...
        @property
        def scene(self) -> Union["SceneManager", "BulkDeviceFacade"]: ...
        @property
        def history(self) -> Union["HistoryManager", "BulkDeviceFacade"]: ...
        @property
        def privacy(self) -> Union["PrivacyManager", "BulkDeviceFacade"]: ...
        @property
        def topology(self) -> Union["TopologyManager", "BulkDeviceFacade"]: ...
        @property
        def users(self) -> Union["UsersManager", "BulkDeviceFacade"]: ...
        @property
        def itxpt(self) -> Union["ITxPTManager", "BulkDeviceFacade"]: ...
        @property
        def multisensors(self) -> Union["MultisensorsManager", "BulkDeviceFacade"]: ...
