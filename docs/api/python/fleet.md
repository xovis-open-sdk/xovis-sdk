# Fleet Management

The `xovis-sdk` provides an advanced, SDK-native Fleet Management abstraction for operating on independent devices as logical groups. Unlike physical topology (which maps strict parent-child stitched environments), the **Fleet Management** module allows you to group, query, and perform bulk operations on arbitrary sets of devices via the Xovis HUB or local JSON caches.

## HubFleetDirectory (Discovery)

The `HubFleetDirectory` is an offline-first indexer that parses raw fleet state data from the Xovis Hub. It leverages dynamic `REPLAccessor` layers to provide perfect IDE auto-suggestions for discovering your devices.

### Loading the Directory

You can build your directory from a live Hub connection or a downloaded `hub_fleet_state.json` file.

```python
from xovis.api.fleet import HubFleetDirectory

# Option A: Load from default offline file (_local_resources/states/hub_fleet_state.json)
directory = HubFleetDirectory.from_file()

# Option B: Load from an active Hub connection
# async with HubClient() as hub:
#     directory = HubFleetDirectory.from_hub(hub)
```

### Auto-Suggested Accessors

The directory automatically builds indexes based on your fleet's metadata. Your IDE (e.g., PyCharm) will surface these properties automatically:

- `directory.by_mac`
- `directory.by_name`
- `directory.by_category` (e.g., `directory.by_category.Xovis_Office`)
- `directory.by_customer`
- `directory.by_device_group` (e.g., `directory.by_device_group.Lades`)

## DeviceGroup (Bulk Execution)

A `DeviceGroup` is the SDK's abstraction for a "Fleet Bucket." It logically groups independent `DeviceClient` instances, allowing you to orchestrate commands across all sensors simultaneously using robust `BulkDeviceFacade` patterns.

### Secure Initialization

Always initialize your groups using the explicit factory method `from_directory_nodes()`. This ensures devices are correctly instantiated as either local LAN clients or `UnifiedDeviceClient` proxies routed through the Xovis Hub, maintaining strict security and routing rules.

```python
import asyncio
from xovis.api.fleet import HubFleetDirectory, DeviceGroup

async def main():
    directory = HubFleetDirectory.from_file()
    
    # Grab the raw dictionaries using IDE autosuggestions
    nodes = directory.by_device_group.Lades

    # Instantiate securely
    grp = DeviceGroup.from_directory_nodes(
        name="Lades",
        nodes=nodes,
        password="YourSecurePassword123" # Used for direct LAN access
        # hub_client=hub                 # Uncomment to use Hub proxy tunneling
    )
```

### Bulk Control Plane Operations

`DeviceGroup` mirrors the `DeviceClient` control plane completely. Endpoints such as `.datapush`, `.system`, `.network`, `.analytics`, and `.time` are available with full IDE autosuggestion capabilities.

Operations invoked on the group are broadcast concurrently across all devices, protected by an internal `asyncio.Semaphore` to prevent rate-limit exhaustion.

```python
    # Broadcast an asynchronous command
    result = await grp.network.get_hostname()
    
    # Bulk operations return a BulkOperationResult avoiding split-brain crashes
    print("Successful Hostnames:", result.successes)
    if result.exceptions:
        print("Failed Devices:", result.exceptions)
```

## Adding and Removing Devices Dynamically

You can easily adjust the composition of a `DeviceGroup` on the fly. 

```python
# Remove a device by Name, IP, or MAC
grp.remove_device("Sensor_52")
grp.remove_device("192.168.1.100")

# Add individual clients manually
from xovis.api.device.client import DeviceClient
grp.add_device(DeviceClient(host="10.0.0.5", username="admin", password="password"))
```