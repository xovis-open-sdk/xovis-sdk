from __future__ import annotations

from enum import Enum, IntEnum
from ipaddress import IPv4Address
from typing import Literal

from pydantic import (
    AnyUrl,
    AwareDatetime,
    Base64Str,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    confloat,
    conint,
    constr,
)

from xovis.utils.time import XovisTime


class CountQuality(Enum):
    """Pydantic model representing the CountQuality schema."""

    Defect = "Defect"
    Other = "Other"
    Regular = "Regular"
    Sabotage = "Sabotage"


class ObjectClass(Enum):
    """Pydantic model representing the ObjectClass schema."""

    ADULT = "ADULT"
    CHILD = "CHILD"
    BICYCLE = "BICYCLE"
    PRAM = "PRAM"
    WHEELCHAIR = "WHEELCHAIR"
    OTHER = "OTHER"
    UNIDENTIFIED = "UNIDENTIFIED"


class Value(Enum):
    """Pydantic model representing the Value schema."""

    DoorsOpen = "DoorsOpen"
    AllDoorsClosed = "AllDoorsClosed"
    SingleDoorOpen = "SingleDoorOpen"
    SingleDoorClosed = "SingleDoorClosed"


class DeviceClass(Enum):
    """Pydantic model representing the DeviceClass schema."""

    APC = "APC"
    Other = "Other"


class DeviceState(Enum):
    """Pydantic model representing the DeviceState schema."""

    defective = "defective"
    notavailable = "notavailable"
    running = "running"
    readyForShutdown = "readyForShutdown"


class Value1(Enum):
    """Pydantic model representing the Value1 schema."""

    DoorsOpen_AllDoorsClosed_SingleDoorOpen_SingleDoorClosed = (
        "DoorsOpen AllDoorsClosed SingleDoorOpen SingleDoorClosed"
    )


class ServiceState(Enum):
    """Pydantic model representing the ServiceState schema."""

    defective_notrunning = "defective notrunning"
    running = "running"
    starting = "starting"
    standby = "standby"


class IBISIPErrorCode(Enum):
    """Pydantic model representing the IBISIPErrorCode schema."""

    DataEstimated = "DataEstimated"
    FaultData = "FaultData"
    NoScheduleDataAvailable = "NoScheduleDataAvailable"
    DeviceMissing = "DeviceMissing"
    NoServiceResponse = "NoServiceResponse"
    ImportantDataNotAvailable = "ImportantDataNotAvailable"
    DataNotValid = "DataNotValid"
    OperationNotSupported = "OperationNotSupported"


class IBISIPInt(BaseModel):
    """Pydantic model representing the IBISIPInt schema."""

    ErrorCode: IBISIPErrorCode | None = None
    Value: int = Field(..., description="xs:int", examples=[123])


class IBISIPString(BaseModel):
    """Pydantic model representing the IBISIPString schema."""

    ErrorCode: IBISIPErrorCode | None = None
    Value: str = Field(..., description="xs:string", examples=["some_chars"])


class ServiceType(Enum):
    """Pydantic model representing the ServiceType schema."""

    itxpt_socket = "itxpt_socket"
    itxpt_http = "itxpt_http"
    sntp = "sntp"
    itxpt_multicast = "itxpt_multicast"
    mqtt = "mqtt"


class Service(BaseModel):
    """Pydantic model representing the Service schema."""

    ServiceName: str | None = Field(
        None, description="Name of the implemented services", examples=["inventory"]
    )
    ServiceType_1: ServiceType | None = Field(
        None, alias="ServiceType", description="Type of the implemented service"
    )


class Module(BaseModel):
    """Pydantic model representing the Module schema."""

    HardwareVersion: str | None = Field(None, description="The hardware version of the module")
    MACAddress: str | None = Field(
        None, description="The MAC address of the module as HEX, with “:” separating the bytes"
    )
    Manufacturer: str | None = Field(
        None, description="The manufacturer of the module", examples=["Xovis AG"]
    )
    Model: str | None = Field(None, description="The model of the module", examples=["PC2RL"])
    SerialNumber: str | None = Field(None, description="Serial number of the module")
    Services: list[Service] | None = Field(None, description="Available list of services")
    SoftwareVersion: str | None = Field(
        None, description="The software version installed on the module"
    )
    Status: str | None = Field(None, description="The last error detected during selftest")
    Type: str | None = Field(
        None, description="Type of the module", examples=["Passenger counting"]
    )


class ModulesDelivery(BaseModel):
    """Pydantic model representing the ModulesDelivery schema."""

    Module_1: Module | None = Field(None, alias="Module")


class OperationErrorMessage(BaseModel):
    """Pydantic model representing the OperationErrorMessage schema."""

    OperationErrorMessage: IBISIPString | None = None


class DoorCountQuality(Enum):
    """Pydantic model representing the DoorCountQuality schema."""

    Regular = "Regular"
    Defect = "Defect"
    Other = "Other"


class ObjectClass1(Enum):
    """Pydantic model representing the ObjectClass1 schema."""

    Adult = "Adult"
    Child = "Child"
    Pram = "Pram"
    Bike = "Bike"
    Wheelchair = "Wheelchair"
    Other = "Other"


class PassengerCountingItem(BaseModel):
    """Pydantic model representing the PassengerCountingItem schema."""

    DoorPassengerIn: int = Field(
        ..., description="Number of passengers having boarded since power up"
    )
    DoorPassengerOut: int = Field(
        ..., description="Number of passengers having alighted since power up"
    )
    ObjectClass: ObjectClass1 | None = Field(None, description="Information on the passenger type")


class PassengerDoorCount(BaseModel):
    """Pydantic model representing the PassengerDoorCount schema."""

    DoorCountQuality_1: DoorCountQuality | None = Field(
        None, alias="DoorCountQuality", description="Information on the quality of counting"
    )
    DoorId: int = Field(..., description="Identification of the door")
    PassengerCounting: list[PassengerCountingItem] | None = None
    RecordedAtTime: str = Field(
        ...,
        description="Date and time of the counting information",
        examples=["2022-03-07T15:00:54"],
    )


class PassengerDoorCountDelivery(BaseModel):
    """Pydantic model representing the PassengerDoorCountDelivery schema."""

    PassengerDoorCount_1: PassengerDoorCount = Field(..., alias="PassengerDoorCount")


class ServiceName(Enum):
    """Pydantic model representing the ServiceName schema."""

    PassengerCountingService = "PassengerCountingService"
    DeviceManagementService = "DeviceManagementService"


class SubscribeRequest(BaseModel):
    """Pydantic model representing the SubscribeRequest schema."""

    model_config = ConfigDict(json_schema_extra={"xml": {"name": "SubscribeRequest"}})
    Client_IP_Address: IBISIPString = Field(..., alias="Client-IP-Address")
    Reply_Path: IBISIPString = Field(..., alias="Reply-Path")
    ReplyPort: IBISIPInt


class UnsubscribeRequest(BaseModel):
    """Pydantic model representing the UnsubscribeRequest schema."""

    model_config = ConfigDict(json_schema_extra={"xml": {"name": "SubscribeRequest"}})
    Client_IP_Address: IBISIPString = Field(..., alias="Client-IP-Address")
    Reply_Path: IBISIPString = Field(..., alias="Reply-Path")
    ReplyPort: IBISIPInt


class AdditionalInformation(BaseModel):
    """Pydantic model representing the AdditionalInformation schema."""

    mac_address: str | None = Field(
        None, description="MAC address of the sensor", examples=["00:00:00:00:00:00"]
    )
    rotation: float | None = Field(
        None, description="The rotation of the sensor in degrees", examples=[90.0]
    )


class MultisensorVersion(Enum):
    """Pydantic model representing the MultisensorVersion schema."""

    default = "default"
    legacy = "legacy"


class AdvancedMultisensorSettings(BaseModel):
    """Pydantic model representing the AdvancedMultisensorSettings schema."""

    low_latency_mode: bool | None = Field(None, examples=[False])
    multisensor_version: MultisensorVersion | None = Field(
        None,
        description="only supported on spider, possible values are given by settings/advanced/options",
    )


class TrackingVersion(Enum):
    """Pydantic model representing the TrackingVersion schema."""

    default = "default"
    field_3X_COMPATIBILITY = "3X_COMPATIBILITY"
    V1 = "V1"
    V2 = "V2"
    V3 = "V3"
    ULTRA_LOW = "ULTRA_LOW"


class AdvancedSettings(BaseModel):
    """Pydantic model representing the AdvancedSettings schema."""

    height_correction: float | None = Field(None, examples=[0.0])
    low_latency_mode: bool | None = Field(None, examples=[False])
    sitting_persons: bool | None = Field(None, examples=[False])
    tracking_version: TrackingVersion | None = Field(
        None, description="possible values are given by /settings/advanced/options"
    )


class TrackingVersionEnum(Enum):
    """Pydantic model representing the TrackingVersionEnum schema."""

    default = "default"
    field_3X_COMPATIBILITY = "3X_COMPATIBILITY"
    V1 = "V1"
    V2 = "V2"
    V3 = "V3"
    ULTRA_LOW = "ULTRA_LOW"


class AdvancedSettingsOptions(BaseModel):
    """Pydantic model representing the AdvancedSettingsOptions schema."""

    tracking_version: list[TrackingVersionEnum] | None = None


class Method(Enum):
    """Pydantic model representing the Method schema."""

    GET = "GET"
    POST = "POST"


class Resource(BaseModel):
    """Pydantic model representing the Resource schema."""

    method: Method | None = None
    uri: constr(pattern="^[ -~]*$") | None = None


class LastProcessed(BaseModel):
    """Pydantic model representing the LastProcessed schema."""

    ack: bool | None = None
    index: conint(ge=-1) | None = None
    package_id: conint(ge=0) | None = None


class PackageInfo(BaseModel):
    """Pydantic model representing the PackageInfo schema."""

    last_processed: LastProcessed | None = None
    no_of_dropped: conint(ge=0) | None = None
    no_of_sent: conint(ge=0) | None = None


class Status(Enum):
    """Pydantic model representing the Status schema."""

    IDLE = "IDLE"
    BUSY = "BUSY"


class AgentTriggerTypes(Enum):
    """Pydantic model representing the AgentTriggerTypes schema."""

    TIME_RANGE = "TIME_RANGE"
    ALL = "ALL"
    LAST_PACKAGE = "LAST_PACKAGE"
    DUMMY_DATA = "DUMMY_DATA"


class Reason(BaseModel):
    """Pydantic model representing the Reason schema."""

    code: int | None = None
    info: str | None = None


class AgentTxStatusDataStats(BaseModel):
    """Pydantic model representing the AgentTxStatusDataStats schema."""

    size: str | None = Field(
        None, description="string representation of size_b (in B, KB, MB, GB, …)"
    )
    size_b: int | None = Field(
        None,
        description="size of transferred data in bytes (payload and most upoper layer header only, no TCP and IP package header bytes)",
    )
    speed: str | None = Field(
        None, description="string representation of speed_bps (in B/s, KB/s, MB/s, …)"
    )
    speed_bps: int | None = Field(None, description="transfer speed in Bytes/Second")


class AgentTypes(Enum):
    """Pydantic model representing the AgentTypes schema."""

    LOGICS = "LOGICS"
    LIVE_DATA = "LIVE_DATA"
    STATUS = "STATUS"
    WIFI_BT = "WIFI_BT"
    RECORDING = "RECORDING"
    LEGACY_LINE_COUNT = "LEGACY_LINE_COUNT"
    LEGACY_ZONE_OCCUPANCY_COUNT = "LEGACY_ZONE_OCCUPANCY_COUNT"
    LEGACY_ZONE_IN_OUT_COUNT = "LEGACY_ZONE_IN_OUT_COUNT"
    LEGACY_EVENT = "LEGACY_EVENT"
    LEGACY_EVENT_STREAM = "LEGACY_EVENT_STREAM"
    LEGACY_COORDINATE = "LEGACY_COORDINATE"
    LEGACY_OBJECT_STREAM = "LEGACY_OBJECT_STREAM"
    LEGACY_WIFI_BT = "LEGACY_WIFI_BT"


class BaseLineCountTemplateOptions(BaseModel):
    """Pydantic model representing the BaseLineCountTemplateOptions schema."""

    activation_zone_id: int | None = None
    count_line_id: int
    deactivation_zone_id: int | None = None
    door_id: int | None = None
    min_dwell_time: float | None = None
    min_dwell_zone_id: int | None = None
    zone_of_interest_id: int | None = None


class BasePersonLineCountTemplateOptions(BaseModel):
    """Pydantic model representing the BasePersonLineCountTemplateOptions schema."""

    age_histogram: list[float] | None = Field(
        None, description="List of strictly-increasing bin boundaries.", max_length=19, min_length=1
    )
    exclude_staff: bool | None = None
    max_person_height: float | None = None
    min_person_height: float | None = None
    recognize_gender: bool | None = None


class BaseZoneCountTemplateOptions(BaseModel):
    """Pydantic model representing the BaseZoneCountTemplateOptions schema."""

    zone_id: int
    zone_of_interest_id: int | None = None


class CoordinateSystem(Enum):
    """Pydantic model representing the CoordinateSystem schema."""

    VIEW = "VIEW"
    STEREOGRAPHIC = "STEREOGRAPHIC"


class InvalidPixelMode(Enum):
    """Pydantic model representing the InvalidPixelMode schema."""

    BACKGROUND = "BACKGROUND"
    FOREGROUND = "FOREGROUND"
    IGNORE = "IGNORE"


class BlockedSpaceLimits(BaseModel):
    """Pydantic model representing the BlockedSpaceLimits schema."""

    max_elements: int | None = None
    max_vertices_per_element: int | None = None


class BluetoothSettings(BaseModel):
    """Pydantic model representing the BluetoothSettings schema."""

    allowlist_enabled: bool | None = Field(
        None, description="Allowlist enabled for Bluetooth monitoring.", examples=[False]
    )
    denylist_enabled: bool | None = Field(
        None, description="Denylist enabled for Bluetooth monitoring.", examples=[True]
    )
    enabled: bool | None = Field(None, description="Bluetooth monitoring enabled.", examples=[True])


class ConfigEndpoint(BaseModel):
    """Pydantic model representing the ConfigEndpoint schema."""

    checksum: str = Field(..., description="Checksum", examples=["0422d752"])
    content: dict[str, str] | None = None
    last_change: str = Field(
        ..., description="Time of last change", examples=["2021-12-08T09:19:39Z"]
    )
    url: str = Field(..., description="URL", examples=["/api/v5/www/config"])


class DirectoryMode(Enum):
    """Pydantic model representing the DirectoryMode schema."""

    MULTICWD = "MULTICWD"
    NOCWD = "NOCWD"
    SINGLECWD = "SINGLECWD"


class FileMode(Enum):
    """Pydantic model representing the FileMode schema."""

    PACKAGE = "PACKAGE"
    APPEND_INTERVAL = "APPEND_INTERVAL"
    APPEND_MAX_SIZE = "APPEND_MAX_SIZE"


class Config1(BaseModel):
    """Pydantic model representing the Config1 schema."""

    account_info: constr(max_length=512) | None = None
    alternative_to_user: constr(max_length=1024) | None = None
    connection_timeout_s: conint(ge=1, le=600) | None = None
    create_directories: bool | None = None
    directory_mode: DirectoryMode | None = None
    file_mode: FileMode | None = None
    ignore_proxy: bool | None = None
    max_file_size: int | None = None
    password: constr(max_length=512) | None = None
    path: constr(max_length=1024) | None = None
    port: conint(ge=1, le=65535) | None = None
    response_timeout_s: conint(ge=1, le=600) | None = None
    ssl_enable: bool | None = None
    uri: AnyUrl
    use_pret: bool | None = None
    user: constr(max_length=512)


class Protocol(Enum):
    """Pydantic model representing the Protocol schema."""

    FTP = "FTP"


class ConnectionConfigFtp(BaseModel):
    """Pydantic model representing the ConnectionConfigFtp schema."""

    config: Config1
    id: int | None = None
    name: constr(max_length=128)
    protocol: Protocol


class AuthMethod(Enum):
    """Pydantic model representing the AuthMethod schema."""

    NONE = "NONE"
    BASIC = "BASIC"
    DIGEST = "DIGEST"
    DIGEST_IE = "DIGEST_IE"
    BEARER_TOKEN = "BEARER_TOKEN"


class CustomHeaderField(BaseModel):
    """Pydantic model representing the CustomHeaderField schema."""

    name: constr(pattern="^[ -~]*$") | None = None
    value: constr(pattern="^[ -~]*$") | None = None


class Config2(BaseModel):
    """Pydantic model representing the Config2 schema."""

    auth_data: constr(max_length=1024) | None = None
    auth_method: AuthMethod | None = None
    chunked_transfer_enabled: bool | None = None
    connection_timeout_s: conint(ge=1, le=600) | None = None
    custom_header_fields: list[CustomHeaderField] | None = None
    ignore_proxy: bool | None = None
    password: constr(max_length=512) | None = None
    port: conint(ge=1, le=65535) | None = None
    ssl_enable: bool | None = None
    uri: AnyUrl
    user: constr(max_length=512) | None = None


class Protocol1(Enum):
    """Pydantic model representing the Protocol1 schema."""

    HTTP = "HTTP"


class ConnectionConfigHttp(BaseModel):
    """Pydantic model representing the ConnectionConfigHttp schema."""

    config: Config2
    id: int | None = None
    name: constr(max_length=128)
    protocol: Protocol1


class Config3(BaseModel):
    """Pydantic model representing the Config3 schema."""

    model_config = ConfigDict(extra="forbid")
    auth_enable: bool | None = None
    client_id: constr(max_length=8192) | None = None
    connection_timeout_s: conint(ge=1, le=600) | None = None
    delivery_timeout_s: conint(ge=1, le=600) | None = None
    password: constr(max_length=512) | None = None
    port: conint(ge=1, le=65535) | None = None
    qos_level: conint(ge=0, le=2) | None = None
    ssl_enable: bool | None = None
    topic: constr(max_length=1024)
    uri: AnyUrl
    user: constr(max_length=512) | None = None
    websocket_enable: bool | None = None


class Protocol2(Enum):
    """Pydantic model representing the Protocol2 schema."""

    MQTT = "MQTT"


class ConnectionConfigMqtt(BaseModel):
    """Pydantic model representing the ConnectionConfigMqtt schema."""

    config: Config3
    id: int | None = None
    name: constr(max_length=128)
    protocol: Protocol2


class Config4(BaseModel):
    """Pydantic model representing the Config4 schema."""

    model_config = ConfigDict(extra="forbid")
    connection_timeout_s: conint(ge=1, le=600) | None = None
    create_directories: bool | None = None
    file_mode: FileMode | None = None
    host_key: constr(max_length=512) | None = None
    ignore_proxy: bool | None = None
    max_file_size: int | None = None
    new_directory_permission: (
        constr(pattern="((^[0-7]{3}$)|(([r-]{1}[w-]{1}[x-]{1}){3}))", max_length=9) | None
    ) = None
    new_file_permission: (
        constr(pattern="((^[0-7]{3}$)|(([r-]{1}[w-]{1}[x-]{1}){3}))", max_length=9) | None
    ) = None
    password: constr(max_length=512) | None = None
    path: constr(max_length=512) | None = None
    port: conint(ge=1, le=65535) | None = None
    ssh_compression_enable: bool | None = None
    uri: AnyUrl
    user: constr(max_length=512)


class Protocol3(Enum):
    """Pydantic model representing the Protocol3 schema."""

    SFTP = "SFTP"


class ConnectionConfigSftp(BaseModel):
    """Pydantic model representing the ConnectionConfigSftp schema."""

    config: Config4 = Field(
        ..., description="Configuration of a SFTP connection used for data datapush's"
    )
    id: int | None = None
    name: constr(max_length=128)
    protocol: Protocol3


class Mode(Enum):
    """Pydantic model representing the Mode schema."""

    CLIENT = "CLIENT"
    SERVER = "SERVER"
    LEGACY_EVENT_STREAM_SERVER = "LEGACY_EVENT_STREAM_SERVER"


class Config5(BaseModel):
    """Pydantic model representing the Config5 schema."""

    model_config = ConfigDict(extra="forbid")
    connection_timeout_s: conint(ge=1, le=600) | None = None
    mode: Mode
    port: conint(ge=1, le=65535) | None = None
    uri: AnyUrl | None = None


class Protocol4(Enum):
    """Pydantic model representing the Protocol4 schema."""

    TCP = "TCP"


class ConnectionConfigTcp(BaseModel):
    """Pydantic model representing the ConnectionConfigTcp schema."""

    config: Config5
    id: int | None = None
    name: constr(max_length=128)
    protocol: Protocol4


class Mode1(Enum):
    """Pydantic model representing the Mode1 schema."""

    CLIENT = "CLIENT"
    LEGACY_OBJECT_STREAM_SERVER = "LEGACY_OBJECT_STREAM_SERVER"


class Config6(BaseModel):
    """Pydantic model representing the Config6 schema."""

    model_config = ConfigDict(extra="forbid")
    connection_timeout_s: conint(ge=1, le=600) | None = None
    mode: Mode1
    port: conint(ge=1, le=65535) | None = None
    uri: AnyUrl | None = None


class Protocol5(Enum):
    """Pydantic model representing the Protocol5 schema."""

    UDP = "UDP"


class ConnectionConfigUdp(BaseModel):
    """Pydantic model representing the ConnectionConfigUdp schema."""

    config: Config6
    id: int | None = None
    name: constr(max_length=128)
    protocol: Protocol5


class ConnectionProtocols(Enum):
    """Pydantic model representing the ConnectionProtocols schema."""

    HTTP = "HTTP"
    FTP = "FTP"
    SFTP = "SFTP"
    MQTT = "MQTT"
    TCP = "TCP"
    UDP = "UDP"


class ServerResponse(BaseModel):
    """Pydantic model representing the ServerResponse schema."""

    code: int | None = None
    info: str | None = None


class Status1(Enum):
    """Pydantic model representing the Status1 schema."""

    OK = "OK"
    NOT_CONNECTED = "NOT_CONNECTED"
    CLIENT_ERROR = "CLIENT_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    UNKNOWN = "UNKNOWN"


class ConnectionTest(BaseModel):
    """Pydantic model representing the ConnectionTest schema."""

    server_response: ServerResponse | None = None
    status: Status1 | None = None


class ConnectionTestResponse(BaseModel):
    """Pydantic model representing the ConnectionTestResponse schema."""

    connection_test: ConnectionTest | None = None


class Coord2d(RootModel[list[float]]):
    """Pydantic model representing the Coord2d schema."""

    root: list[float] = Field(
        ...,
        description="JSON representation of points",
        examples=[[23.3, 12.0]],
        max_length=2,
        min_length=2,
        title="Coord2D",
    )


class Coord3d(RootModel[list[float]]):
    """Pydantic model representing the Coord3d schema."""

    root: list[float] = Field(
        ...,
        description="JSON representation of vectors",
        examples=[[0.4, 0.1, 1.0]],
        max_length=3,
        min_length=3,
        title="Coord3D",
    )


class Histogram(Enum):
    """Pydantic model representing the Histogram schema."""

    PERSON_AGE = "PERSON_AGE"


class Type(Enum):
    """Pydantic model representing the Type schema."""

    COUNT_INCREMENT = "COUNT_INCREMENT"
    COUNT_DECREMENT = "COUNT_DECREMENT"
    WRONG_WAY_DETECTED = "WRONG_WAY_DETECTED"
    COUNT_INCREMENT_BY_DWELL_TIME = "COUNT_INCREMENT_BY_DWELL_TIME"
    COUNT_DECREMENT_BY_DWELL_TIME = "COUNT_DECREMENT_BY_DWELL_TIME"
    COUNT_INCREMENT_BY_TOTAL_DWELL_TIME = "COUNT_INCREMENT_BY_TOTAL_DWELL_TIME"
    COUNT_DECREMENT_BY_TOTAL_DWELL_TIME = "COUNT_DECREMENT_BY_TOTAL_DWELL_TIME"


class CountEvent(BaseModel):
    """Pydantic model representing the CountEvent schema."""

    counter_id: int | None = Field(
        None, description="The id of the counter which gets modified by this count event."
    )
    dwell_zone_id: int | None = Field(
        None, description="The id of the zone used for the dwell-time."
    )
    histogram: Histogram | None = None
    type: Type | None = None


class CountEventType(Enum):
    """Pydantic model representing the CountEventType schema."""

    COUNT_INCREMENT = "COUNT_INCREMENT"
    COUNT_DECREMENT = "COUNT_DECREMENT"
    COUNT_RESET = "COUNT_RESET"
    WRONG_WAY_DETECTED = "WRONG_WAY_DETECTED"


class CountEventTypes1(Enum):
    """Pydantic model representing the CountEventTypes1 schema."""

    ALL = "ALL"
    NONE = "NONE"


class CountEventTypes(RootModel[list[CountEventType] | CountEventTypes1]):
    """Pydantic model representing the CountEventTypes schema."""

    root: list[CountEventType] | CountEventTypes1


class Quantity(Enum):
    """Pydantic model representing the Quantity schema."""

    count = "count"
    time = "time"


class Type1(Enum):
    """Pydantic model representing the Type1 schema."""

    accumulation = "accumulation"
    state = "state"


class Counter(BaseModel):
    """Pydantic model representing the Counter schema."""

    histogram: list[float] | None = Field(
        None, description="List of strictly-increasing bin boundaries.", max_length=19, min_length=1
    )
    id: int | None = Field(None, description="Identification of counter.")
    logic_id: int | None = Field(None, description="Identification of logic.")
    name: str | None = Field(None, description="Name of the counter.")
    quantity: Quantity | None = None
    type: Type1 | None = None


class CounterCollection(BaseModel):
    """Pydantic model representing the CounterCollection schema."""

    counters: list[Counter] | None = None


class Type2(Enum):
    """Pydantic model representing the Type2 schema."""

    XLT_CUSTOM = "XLT_CUSTOM"


class CustomLogicTemplate(BaseModel):
    """Pydantic model representing the CustomLogicTemplate schema."""

    type: Literal["XLT_CUSTOM"]


class Type3(Enum):
    """Pydantic model representing the Type3 schema."""

    WIFI = "WIFI"
    BLE = "BLE"


class DeviceId(BaseModel):
    """Pydantic model representing the DeviceId schema."""

    group: str = Field(..., description="Sensor group", examples=["group 1"])
    id: str | None = Field(
        None, description="Id of device", examples=["ABCDEF123456789ABCDEF123456789ABCDEF1234"]
    )
    name: str = Field(..., description="Sensor name", examples=["my sensor"])
    rssi: int | None = Field(None, description="Signal strength in dB", examples=[-80])
    type: Type3 | None = Field(None, description="Type of device", examples=["WIFI"])


class DeviceIdList(BaseModel):
    """Pydantic model representing the DeviceIdList schema."""

    devices: list[DeviceId] | None = Field(None, description="List of devices")


class ProductSeries(Enum):
    """Pydantic model representing the ProductSeries schema."""

    Standard = "Standard"
    Pixel_Lock = "Pixel Lock"


class DeviceInfo(BaseModel):
    """Pydantic model representing the DeviceInfo schema."""

    fw_version: str = Field(
        ..., description="Firmware version running on sensor.", examples=["5.1.0"]
    )
    hw_bom_rev: str = Field(..., description="BOM revision of device.", examples=["B"])
    hw_id: str
    hw_pcb_rev: str = Field(..., description="PCB revision of device.", examples=["C"])
    hw_prod_rev: str = Field(..., description="Production revision", examples=["AD"])
    prod_code: str = Field(..., description="Device model.", examples=["PC2RUL"])
    product_series: ProductSeries | None = Field(None, examples=["Standard"])
    serial: str = Field(..., description="Serial number of sensor.", examples=["00:00:34:56:2b:7c"])
    type: str = Field(..., description="Device type based on electronics only.", examples=["PC2R"])
    variant: str = Field(..., description="Device variant name", examples=["PRT-400"])


class DeviceLedMode(BaseModel):
    """Pydantic model representing the DeviceLedMode schema."""

    enabled: bool = Field(
        ..., description="Indicates whether LED is enabled or not.", examples=[True]
    )


class Temperatures(BaseModel):
    """Pydantic model representing the Temperatures schema."""

    die: int | None = Field(None, description="Die temperature in degree Celsius", examples=[62])
    housing: int | None = Field(
        None, description="Housing temperature in degree Celsius", examples=[45]
    )


class Details(BaseModel):
    """Pydantic model representing the Details schema."""

    temperatures: Temperatures
    uptime_sec: int = Field(..., description="Seconds since last boot", examples=[12390])


class State1(Enum):
    """Pydantic model representing the State1 schema."""

    UNDEFINED = "UNDEFINED"
    OK = "OK"
    RESCUE = "RESCUE"
    UPDATING = "UPDATING"
    REBOOTING = "REBOOTING"


class DeviceState1(BaseModel):
    """Pydantic model representing the DeviceState1 schema."""

    details: Details
    state: State1 = Field(..., description="State of sensor device", examples=["OK"])


class State2(Enum):
    """Pydantic model representing the State2 schema."""

    UNINITIALIZED = "UNINITIALIZED"
    IN_PROGRESS = "IN_PROGRESS"
    AVAILABLE = "AVAILABLE"
    RESTORING = "RESTORING"
    ERROR = "ERROR"


class DiagBundleState(BaseModel):
    """Pydantic model representing the DiagBundleState schema."""

    creation_date: str | None = Field(
        None,
        description="Time of diag bundle creation (format RFC3339)",
        examples=["2021-03-31T09:15:53+0100"],
    )
    state: State2 = Field(
        ..., description="State of diag bundle package", examples=["UNINITIALIZED"]
    )


class Port(BaseModel):
    """Pydantic model representing the Port schema."""

    number: int = Field(..., examples=[443])
    service: str = Field(..., examples=["https"])


class DiscoverIp(BaseModel):
    """Pydantic model representing the DiscoverIp schema."""

    ip: str = Field(..., examples=["192.168.1.10"])
    ipv6: list[str]
    mac: str = Field(..., examples=["01:02:03:04:05:06"])
    ports: list[Port]


class DiscoverMac(BaseModel):
    """Pydantic model representing the DiscoverMac schema."""

    mac: str = Field(..., examples=["01:02:03:04:05:06"])


class DiscoverScanJob(BaseModel):
    """Pydantic model representing the DiscoverScanJob schema."""

    count: int = Field(..., examples=[100])
    first_ip: str = Field(..., examples=["192.168.1.5"])


class DiscoverSensor(BaseModel):
    """Pydantic model representing the DiscoverSensor schema."""

    fw_version: str = Field(..., examples=["5.0.1"])
    group: str = Field(..., examples=["MyGroup"])
    ip: str = Field(..., examples=["192.168.1.10"])
    ipv6: list[str]
    mac: str = Field(..., examples=["01:02:03:04:05:06"])
    model: str = Field(..., examples=["PC2RUL"])
    name: str = Field(..., examples=["MySensor"])
    ports: list[Port]


class OpenSignal(Enum):
    """Pydantic model representing the OpenSignal schema."""

    HIGH = "HIGH"
    LOW = "LOW"


class Source(Enum):
    """Pydantic model representing the Source schema."""

    EXTERNAL = "EXTERNAL"
    DIGITAL_IO = "DIGITAL_IO"


class Door(BaseModel):
    """Pydantic model representing the Door schema."""

    id: int | None = Field(None, description="Identification of door.")
    ignore_timestamp: bool | None = None
    name: str | None = Field(None, description="Name of the door.")
    open_signal: OpenSignal | None = None
    source: Source | None = None


class Status2(Enum):
    """Pydantic model representing the Status2 schema."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    ERROR = "ERROR"
    OUT_OF_SYNC = "OUT_OF_SYNC"


class DoorStatus(BaseModel):
    """Pydantic model representing the DoorStatus schema."""

    id: float | None = None
    name: str | None = Field(None, examples=["Front door"])
    status: Status2 | None = None
    timestamp: float | None = None


class Doors(BaseModel):
    """Pydantic model representing the Doors schema."""

    doors: list[Door] | None = None


class DoorsStatus(BaseModel):
    """Pydantic model representing the DoorsStatus schema."""

    doors: list[DoorStatus] | None = None


class DownloadConfig(BaseModel):
    """Pydantic model representing the DownloadConfig schema."""

    auto_download: bool | None = Field(
        None,
        description="Allows sensor to download latest minor update available on the sensor automatically",
        examples=[False],
    )
    auto_refresh: bool | None = Field(
        None,
        description="Allows sensor to try to refresh updates available at least once per day",
        examples=[True],
    )


class Error(BaseModel):
    """Pydantic model representing the Error schema."""

    code: int = Field(..., examples=[1])
    info: str = Field(..., examples=["Failed to connect to server"])


class State3(Enum):
    """Pydantic model representing the State3 schema."""

    UNDEFINED = "UNDEFINED"
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class DownloadState(BaseModel):
    """Pydantic model representing the DownloadState schema."""

    error: Error | None = Field(None, description="Error details of the last download if failed")
    progress: float | None = Field(
        None, description="Current progress of the active download", examples=[99.99]
    )
    state: State3 = Field(..., description="State of last/active download", examples=["UNDEFINED"])
    version: str | None = Field(
        None, description="Version of last/active download", examples=["5.0.0-adsfasdf"]
    )


class Protocol6(Enum):
    """Pydantic model representing the Protocol6 schema."""

    PEAP = "PEAP"
    TLS = "TLS"
    TTLS = "TTLS"


class EapolConfig(BaseModel):
    """Pydantic model representing the EapolConfig schema."""

    anonymous_identity: str | None = Field(None, examples=["anonymous"])
    enabled: bool = Field(
        ..., description="Indicates whether 802.1X EAPoL is enabled", examples=[True]
    )
    identity: str = Field(..., examples=["xovis_pc2_08:80:39:5e:6c:2b"])
    password: str | None = Field(None, examples=["password"])
    protocol: Protocol6 = Field(
        ..., description="Extensible authentication protocol", examples=["TLS"]
    )


class Details1(BaseModel):
    """Pydantic model representing the Details1 schema."""

    enabled: bool = Field(
        ..., description="Indicates whether 802.1X EAPoL is enabled.", examples=[True]
    )
    port_authorized: bool | None = Field(None, description="State of port", examples=["true;"])


class State4(Enum):
    """Pydantic model representing the State4 schema."""

    OK = "OK"
    WARN = "WARN"
    ERROR = "ERROR"


class EapolState(BaseModel):
    """Pydantic model representing the EapolState schema."""

    details: Details1
    state: State4 = Field(..., description="State of module")


class ElementsLimits(BaseModel):
    """Pydantic model representing the ElementsLimits schema."""

    max_elements: int | None = None


class EmbeddedUiConfig(BaseModel):
    """Pydantic model representing the EmbeddedUiConfig schema."""

    path: str | None = Field(
        None,
        description="Path to the top html file of the sandbox UI",
        examples=["/sandbox/index.html"],
    )
    title: str | None = Field(
        "", description="Title of link / button in main ui", examples=["Sandbox UI"]
    )


class ErrorMessage(BaseModel):
    """Pydantic model representing the ErrorMessage schema."""

    code: float | None = Field(None, description="Error code", examples=[11100])
    detail: list[str] | None = Field(None, description="Optional detail about the error")
    info: str | None = Field(
        None, description="Short error description", examples=["The json could not be parsed."]
    )


class ZoneEventType(Enum):
    """Pydantic model representing the ZoneEventType schema."""

    TRACK_CREATED = "TRACK_CREATED"
    TRACK_DELETED = "TRACK_DELETED"
    BOUNDARY_CROSS = "BOUNDARY_CROSS"
    ZONE_MODIFICATION = "ZONE_MODIFICATION"


class Attributes(BaseModel):
    """Pydantic model representing the Attributes schema."""

    counter_id: int | None = Field(None, description="Identification of counter", examples=[13])
    door_id: int | None = Field(None, description="Identification of door", examples=[2])
    geometry_id: int | None = Field(None, description="Identification of geometry", examples=[2])
    sequence_number: int | None = Field(
        None, description="Order within all events in the frame", examples=[1]
    )
    space_id: int | None = Field(None, description="Identification of space", examples=[8])
    time_in_zone: int | None = Field(None, description="Time in zone in seconds", examples=[4.3])
    track_id: int | None = Field(None, description="Identification of object", examples=[167])
    zone_event_type: ZoneEventType | None = None


class Category(Enum):
    """Pydantic model representing the Category schema."""

    SCENE = "SCENE"
    COUNT = "COUNT"
    INFO = "INFO"


class Type4(Enum):
    """Pydantic model representing the Type4 schema."""

    TRACK_CREATE = "TRACK_CREATE"
    TRACK_DELETE = "TRACK_DELETE"
    LINE_CROSS_FORWARD = "LINE_CROSS_FORWARD"
    LINE_CROSS_BACKWARD = "LINE_CROSS_BACKWARD"
    ZONE_ENTRY = "ZONE_ENTRY"
    ZONE_EXIT = "ZONE_EXIT"
    DOOR_OPEN = "DOOR_OPEN"
    DOOR_CLOSED = "DOOR_CLOSED"
    COUNT_INCREMENT = "COUNT_INCREMENT"
    COUNT_DECREMENT = "COUNT_DECREMENT"
    COUNT_RESET = "COUNT_RESET"
    WRONG_WAY_DETECTED = "WRONG_WAY_DETECTED"
    SENSOR_FAILURE = "SENSOR_FAILURE"
    DIGITAL_INPUT_HIGH = "DIGITAL_INPUT_HIGH"
    DIGITAL_INPUT_LOW = "DIGITAL_INPUT_LOW"
    BLOCKED_SPACE_ABOVE = "BLOCKED_SPACE_ABOVE"
    BLOCKED_SPACE_BELOW = "BLOCKED_SPACE_BELOW"
    ILLUMINATION_SUFFICIENT = "ILLUMINATION_SUFFICIENT"
    ILLUMINATION_INSUFFICIENT = "ILLUMINATION_INSUFFICIENT"


class Event(BaseModel):
    """Pydantic model representing the Event schema."""

    attributes: Attributes | None = None
    category: Category | None = None
    type: Type4 | None = None


class Events(RootModel[list[Event]]):
    """Pydantic model representing the Events schema."""

    root: list[Event] = Field(..., description="JSON representation of events", title="Events")


class Type5(Enum):
    """Pydantic model representing the Type5 schema."""

    BLOCKED_SPACE = "BLOCKED_SPACE"


class Mode2(Enum):
    """Pydantic model representing the Mode2 schema."""

    AUTOMATED = "AUTOMATED"
    MANUAL = "MANUAL"


class ExposureControlSettings(BaseModel):
    """Pydantic model representing the ExposureControlSettings schema."""

    exposure_time: float | None = Field(None, examples=[0.01])
    gain: float | None = Field(None, examples=[5.0])
    mode: Mode2


class Entry(BaseModel):
    """Pydantic model representing the Entry schema."""

    enabled: bool | None = Field(None, examples=[True])
    id: str | None = Field(
        None, description="extension identifier: PIFMD, PIGES, PISTE, PIVID", examples=["PIFMD"]
    )


class ExtensionHeaders(BaseModel):
    """Pydantic model representing the ExtensionHeaders schema."""

    entries: list[Entry]


class ExtensionPiges(BaseModel):
    """Pydantic model representing the ExtensionPiges schema."""

    alternativeColors: bool | None = Field(
        None, description="Visualize gender in alternative colors"
    )
    ambiguousDetectionStrategy: bool | None = None
    genderSymbol: bool | None = Field(None, description="Visualize gender symbol")
    viewEnabled: bool | None = Field(None, description="Visualize gender in ui")


class ExtensionPiste(BaseModel):
    """Pydantic model representing the ExtensionPiste schema."""

    type: str | None = None
    typeSelected: str | None = None
    viewEnabled: bool | None = Field(None, description="Visualize staff in ui")


class Type6(Enum):
    """Pydantic model representing the Type6 schema."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class FilterOperator(BaseModel):
    """Pydantic model representing the FilterOperator schema."""

    type: Literal["AND", "OR", "NOT"]


class FloorPlanMetadata(BaseModel):
    """Pydantic model representing the FloorPlanMetadata schema."""

    distance: float | None = None
    end: Coord2d | None = None
    group: str | None = Field(None, examples=["office 3"])
    name: str | None = Field(None, examples=["floor plan"])
    origin: Coord2d | None = None
    start: Coord2d | None = None


class Formats(Enum):
    """Pydantic model representing the Formats schema."""

    JSON = "JSON"
    PROTOBUF = "PROTOBUF"
    BINARY = "BINARY"
    XML = "XML"
    RECORDING = "RECORDING"


class GigabitEnabled(BaseModel):
    """Pydantic model representing the GigabitEnabled schema."""

    gigabit_enabled: bool = Field(
        ..., description="Indicates whether gigabit is enabled or disabled.", examples=[False]
    )


class Type7(Enum):
    """Pydantic model representing the Type7 schema."""

    XLT_GROUP_LINE_IN_OUT_COUNT = "XLT_GROUP_LINE_IN_OUT_COUNT"
    XLT_GROUP_LINE_LATE_COUNT = "XLT_GROUP_LINE_LATE_COUNT"


class GroupLineCountLogicTemplate(BaseModel):
    """Pydantic model representing the GroupLineCountLogicTemplate schema."""

    options: BaseLineCountTemplateOptions | None = None
    type: Literal["XLT_GROUP_LINE_IN_OUT_COUNT", "XLT_GROUP_LINE_LATE_COUNT"]


class GroupsSettings(BaseModel):
    """Pydantic model representing the GroupsSettings schema."""

    delay: confloat(ge=1.0, le=10.0) | None = Field(
        None, description="Delay of group track in [s].", examples=[2.0]
    )
    max_distance: confloat(ge=0.0, le=1000.0) | None = Field(
        None, description="The maximum distance between two group members in [m].", examples=[1.0]
    )


class Count1(BaseModel):
    """Pydantic model representing the Count1 schema."""

    bins: list[int | float] | None = Field(None, description="List of differential bin values.")
    id: int | None = Field(None, description="the id of the corresponding counter config")
    value: int | float | None = None


class Type8(Enum):
    """Pydantic model representing the Type8 schema."""

    accumulation = "accumulation"
    state = "state"


class Count2(BaseModel):
    """Pydantic model representing the Count2 schema."""

    id: int | None = None
    logic_id: int | None = Field(None, description="id of logic the counter belongs to")
    name: str | None = Field(None, description="name of the counter")
    type: Type8 | None = None


class Type9(Enum):
    """Pydantic model representing the Type9 schema."""

    LINE = "LINE"
    ZONE = "ZONE"


class Geometry(BaseModel):
    """Pydantic model representing the Geometry schema."""

    id: int | None = None
    name: str | None = Field(None, description="name of the geometry")
    type: Type9 | None = None


class Hostname(BaseModel):
    """Pydantic model representing the Hostname schema."""

    hostname: str = Field(..., examples=["XS-SENSOR-71fbf5"])


class IbisipApcObjectDetails(BaseModel):
    """Pydantic model representing the IbisipApcObjectDetails schema."""

    in_counter_id: int | None = Field(None, description="Identification of in counter")
    logic_id: int | None = Field(
        None, description="Identification of logic that counts specific object"
    )
    out_counter_id: int | None = Field(None, description="Identification of out counter")


class ApcPushType(Enum):
    """Pydantic model representing the ApcPushType schema."""

    on_event = "on_event"
    periodic = "periodic"


class ProtocolVersion(Enum):
    """Pydantic model representing the ProtocolVersion schema."""

    v2_1_0 = "v2.1.0"
    unknown = "unknown"


class IbisipConfig(BaseModel):
    """Pydantic model representing the IbisipConfig schema."""

    apc_push_max_resolution_ms: conint(ge=80, le=5000) | None = Field(
        1000,
        description="Only required when apc_push_type = on_event. Maximal output rate of data published",
    )
    apc_push_period_ms: conint(ge=80, le=60000) | None = Field(
        1000, description="Only required when apc_push_type = periodic. Period of data published"
    )
    apc_push_type: ApcPushType = Field(..., description="APC datapush type configured")
    enabled: bool = Field(..., description="Indicates whether ibisip features are enabled or not.")
    heartbeat_period_ms: conint(ge=1000, le=60000) | None = Field(
        30000,
        description="Only required when apc_push_type = on_event. Heartbeat when no event was generated",
    )
    nb_retries_before_expiration: conint(ge=0, le=100) | None = Field(
        5, description="Number of retries before unsubscribing a client"
    )
    protocol_version: ProtocolVersion = Field(
        ..., description="Set protocol version for published services"
    )


class IbisipConfigTxt(BaseModel):
    """Pydantic model representing the IbisipConfigTxt schema."""

    additionalProperties: str | None = None


class ExternalSource(Enum):
    """Pydantic model representing the ExternalSource schema."""

    doorstateservice = "doorstateservice"


class IbisipSensorDoorConfig(BaseModel):
    """Pydantic model representing the IbisipSensorDoorConfig schema."""

    external_source: ExternalSource | None = Field(None, description="Source of the door status")
    external_source_door_id: str | None = Field(
        None, description="Identification of the door from the selected source"
    )
    sensor_door_id: int = Field(
        ...,
        description="Identification of the sensor door that should be linked with this apc door",
    )


class Consumer(BaseModel):
    """Pydantic model representing the Consumer schema."""

    ip: str | None = Field(None, description="IP of the device subscribed to the service")
    path: str | None = Field(None, description="path used to access the service")
    port: int | None = Field(None, description="port used to access the service")


class IbisipTime(BaseModel):
    """Pydantic model representing the IbisipTime schema."""

    searching: bool = Field(..., description="If a time service publisher is currently looked for")
    sntp_server: str = Field(
        ..., description="Contains ip address of the sntp server found or message status"
    )


class IbisipTimeConfig(BaseModel):
    """Pydantic model representing the IbisipTimeConfig schema."""

    time_discovery: bool = Field(..., description="Set discovery of a VDV-301 time service")


class RefCoordinateSystem(Enum):
    """Pydantic model representing the RefCoordinateSystem schema."""

    VIEW = "VIEW"
    SCENE = "SCENE"
    STEREOGRAPHIC = "STEREOGRAPHIC"
    IMAGE = "IMAGE"


class IncludedLogics1(Enum):
    """Pydantic model representing the IncludedLogics1 schema."""

    ALL = "ALL"
    NONE = "NONE"


class IncludedLogics(RootModel[list[int] | IncludedLogics1]):
    """Pydantic model representing the IncludedLogics schema."""

    root: list[int] | IncludedLogics1


class InfoEventType(Enum):
    """Pydantic model representing the InfoEventType schema."""

    SENSOR_FAILURE = "SENSOR_FAILURE"
    DIGITAL_INPUT_HIGH = "DIGITAL_INPUT_HIGH"
    DIGITAL_INPUT_LOW = "DIGITAL_INPUT_LOW"
    BLOCKED_SPACE_ABOVE = "BLOCKED_SPACE_ABOVE"
    BLOCKED_SPACE_BELOW = "BLOCKED_SPACE_BELOW"
    ILLUMINATION_SUFFICIENT = "ILLUMINATION_SUFFICIENT"
    ILLUMINATION_INSUFFICIENT = "ILLUMINATION_INSUFFICIENT"


class InfoEventTypes1(Enum):
    """Pydantic model representing the InfoEventTypes1 schema."""

    ALL = "ALL"
    NONE = "NONE"


class InfoEventTypes(RootModel[list[InfoEventType] | InfoEventTypes1]):
    """Pydantic model representing the InfoEventTypes schema."""

    root: list[InfoEventType] | InfoEventTypes1


class ItxptApcObjectDetails(BaseModel):
    """Pydantic model representing the ItxptApcObjectDetails schema."""

    in_counter_id: int | None = Field(None, description="Identification of in counter")
    logic_id: int | None = Field(
        None, description="Identification of logic that counts specific object"
    )
    out_counter_id: int | None = Field(None, description="Identification of out counter")


class FmstoipUpdatePolicy(Enum):
    """Pydantic model representing the FmstoipUpdatePolicy schema."""

    on_change = "on_change"
    every_second = "every_second"


class ProtocolVersion1(Enum):
    """Pydantic model representing the ProtocolVersion1 schema."""

    v2_0_1 = "v2.0.1"
    v2_1_0 = "v2.1.0"
    v2_1_1 = "v2.1.1"
    unknown = "unknown"


class VehicleIdSource(Enum):
    """Pydantic model representing the VehicleIdSource schema."""

    fmstoip = "fmstoip"
    vehicletoip = "vehicletoip"
    custom = "custom"


class ItxptConfig(BaseModel):
    """Pydantic model representing the ItxptConfig schema."""

    apc_push_max_resolution_ms: conint(ge=80, le=5000) | None = Field(
        1000,
        description="Only required when apc_push_type = on_event. Maximal output rate of data published",
    )
    apc_push_period_ms: conint(ge=80, le=60000) | None = Field(
        1000, description="Only required when apc_push_type = periodic. Period of data published"
    )
    apc_push_type: ApcPushType = Field(..., description="APC datapush type configured")
    consumed_services_timeout_s: conint(ge=0, le=86400) | None = Field(
        3600,
        description="Listening timeout for all consumed services. The service listeners are automatically restarted after the timeout. If set to 0 no timeout is considered",
    )
    custom_vehicle_id: str | None = Field(
        "",
        description="custom id when selected vehicle id source is set to custom",
        examples=["Batmobile"],
    )
    fmstoip_update_policy: FmstoipUpdatePolicy | None = Field(
        "on_change",
        description="Set update policy for FMStoIP. Only applicable for versions 2.2.0 and higher",
    )
    heartbeat_period_ms: conint(ge=1000, le=60000) | None = Field(
        30000,
        description="Only required when apc_push_type = on_event. Heartbeat when no event was generated",
    )
    inventory_path: str | None = Field(
        "/api/v5/itxpt/services/inventory/moduleinfo.xml",
        description="Path for inventory operations (reflected in mdns record)",
    )
    itxpt_enabled: bool = Field(
        ..., description="Indicates whether itxpt features are enabled or not."
    )
    nb_retries_before_expiration: conint(ge=0, le=100) | None = Field(
        5, description="Number of retries before unsubscribing a client"
    )
    protocol_version: ProtocolVersion1 = Field(
        ..., description="Set protocol version for published services (APC and Inventory)"
    )
    vehicle_id_source: VehicleIdSource = Field(
        ..., description="Supported vehicle id source information"
    )


class ItxptConfigTxt(BaseModel):
    """Pydantic model representing the ItxptConfigTxt schema."""

    additionalProperties: str | None = None


class ItxptCustomConfigurations(BaseModel):
    """Pydantic model representing the ItxptCustomConfigurations schema."""

    customField1: str | None = Field(None, description="Custom free text 1")
    customField2: str | None = Field(None, description="Custom free text 2")


class ExternalSource1(Enum):
    """Pydantic model representing the ExternalSource1 schema."""

    fmstoip = "fmstoip"
    vehicletoip = "vehicletoip"


class ItxptSensorDoorConfig(BaseModel):
    """Pydantic model representing the ItxptSensorDoorConfig schema."""

    external_source: ExternalSource1 | None = Field(None, description="Source of the door status")
    external_source_door_id: int | None = Field(
        None, description="Identification of the door from the selected source"
    )
    sensor_door_id: int = Field(
        ...,
        description="Identification of the sensor door that should be linked with this apc door",
    )


class ItxptState(BaseModel):
    """Pydantic model representing the ItxptState schema."""

    vehicle_id: str = Field(..., description="Vehicle ID")


class DoorSource(Enum):
    """Pydantic model representing the DoorSource schema."""

    digital_io = "digital_io"
    fmstoip = "fmstoip"
    vehicletoip = "vehicletoip"


class DoorSourceProtocolVersion(Enum):
    """Pydantic model representing the DoorSourceProtocolVersion schema."""

    v2_0_1 = "v2.0.1"
    v2_1_0 = "v2.1.0"
    v2_1_1 = "v2.1.1"
    not_supported = "not_supported"
    unknown = "unknown"


class DoorState(Enum):
    """Pydantic model representing the DoorState schema."""

    Open = "Open"
    Close = "Close"
    Error = "Error"
    NotAvailable = "NotAvailable"
    unknown = "unknown"


class Door1(BaseModel):
    """Pydantic model representing the Door1 schema."""

    door_id: int = Field(..., description="Door id for ITxPT APC")
    door_source: DoorSource = Field(..., description="Supported door source information")
    door_source_protocol_version: DoorSourceProtocolVersion = Field(
        ..., description="Actual used protocol version of the protocol source."
    )
    door_state: DoorState
    logic_id_adult: int = Field(..., description="logic_id to read counter values of Adults")
    logic_id_bicycle: int = Field(..., description="logic_id to read counter values of Bikes")
    logic_id_child: int = Field(..., description="logic_id to read counter values of Childs")
    logic_id_pram: int = Field(..., description="logic_id to read counter values of Prams")
    logic_id_wheelchair: int = Field(
        ..., description="logic_id to read counter values of Wheelchairs"
    )


class VehicleIdSourceProtocolVersion(Enum):
    """Pydantic model representing the VehicleIdSourceProtocolVersion schema."""

    v2_0_1 = "v2.0.1"
    v2_1_0 = "v2.1.0"
    v2_1_1 = "v2.1.1"
    not_supported = "not_supported"
    unknown = "unknown"


class ItxptStateDeprecated(BaseModel):
    """Pydantic model representing the ItxptStateDeprecated schema."""

    doors: list[Door1] | None = None
    ready: bool = Field(
        ...,
        description="Means APC is configured and running. Everything else could be reasonably defaulted.",
    )
    vehicle_id: str = Field(..., description="Vehicle ID")
    vehicle_id_source: VehicleIdSource = Field(..., description="Vehicle ID source")
    vehicle_id_source_protocol_version: VehicleIdSourceProtocolVersion = Field(
        ..., description="Actual used protocol version of the vehicle id source."
    )


class ItxptTime(BaseModel):
    """Pydantic model representing the ItxptTime schema."""

    searching: bool = Field(..., description="If a time service publisher is currently looked for")
    sntp_server: str = Field(
        ..., description="Contains ip address of the sntp server found or message status"
    )


class ItxptTimeConfig(BaseModel):
    """Pydantic model representing the ItxptTimeConfig schema."""

    time_discovery: bool = Field(..., description="Set discovery of a ITxPT time service")


class Latency(Enum):
    """Pydantic model representing the Latency schema."""

    DEFAULT = "DEFAULT"
    LOW = "LOW"


class LatencySettings(BaseModel):
    """Pydantic model representing the LatencySettings schema."""

    latency: Latency | None = None


class LayersLimits(BaseModel):
    """Pydantic model representing the LayersLimits schema."""

    max_elements: int | None = None
    max_total_perimeter: int | None = None
    max_total_vertices: int | None = None
    max_vertices_per_element: int | None = None


class LegacyConfigPut(BaseModel):
    """Pydantic model representing the LegacyConfigPut schema."""

    enabled: bool | None = None


class LegacyMode(BaseModel):
    """Pydantic model representing the LegacyMode schema."""

    enabled: bool | None = Field(None, description="Enable legacy support")


class ObjectType(Enum):
    """Pydantic model representing the ObjectType schema."""

    PERSON = "PERSON"
    GROUP = "GROUP"
    BICYCLE = "BICYCLE"


class Options(BaseLineCountTemplateOptions, BasePersonLineCountTemplateOptions):
    """Pydantic model representing the Options schema."""

    count_face_mask: bool | None = None
    object_type: ObjectType | None = None


class Type10(Enum):
    """Pydantic model representing the Type10 schema."""

    XLT_4X_LINE_IN_OUT_COUNT = "XLT_4X_LINE_IN_OUT_COUNT"
    XLT_4X_LINE_LATE_COUNT = "XLT_4X_LINE_LATE_COUNT"


class LegacyPersonLineCountLogicTemplate(BaseModel):
    """Pydantic model representing the LegacyPersonLineCountLogicTemplate schema."""

    options: Options | None = None
    type: Literal["XLT_4X_LINE_IN_OUT_COUNT", "XLT_4X_LINE_LATE_COUNT"]


class Options1(BaseZoneCountTemplateOptions):
    """Pydantic model representing the Options1 schema."""

    dwell_time: bool | None = None
    max_dwell_time: float | None = None
    min_dwell_time: float | None = None


class Type11(Enum):
    """Pydantic model representing the Type11 schema."""

    XLT_4X_ZONE_COUNT = "XLT_4X_ZONE_COUNT"


class LegacyZoneInOutCountLogicTemplate(BaseModel):
    """Pydantic model representing the LegacyZoneInOutCountLogicTemplate schema."""

    options: Options1 | None = None
    type: Literal["XLT_4X_ZONE_COUNT"]


class Detail(BaseModel):
    """Pydantic model representing the Detail schema."""

    code: int | None = Field(None, description="Code related to the error occurred")
    details: str | None = Field(
        None, description="Details about this specific feature", examples=["Accepted"]
    )
    id: int | None = Field(
        None, description="What id did the feature have that wanted to be included", examples=[1000]
    )


class LicenseAddResponse(BaseModel):
    """Pydantic model representing the LicenseAddResponse schema."""

    details: list[Detail] | None = None
    info: str | None = Field(
        None, description="Could the license be fully/partial/not at all added"
    )


class LicenseConfig(BaseModel):
    """Pydantic model representing the LicenseConfig schema."""

    connect: bool = Field(..., description="enables communication with the license server")
    plugins: list[int] | None = None
    proxy_enable: bool | None = Field(None, description="Deprecated")


class LicensedLifetimeItem(BaseModel):
    """Pydantic model representing the LicensedLifetimeItem schema."""

    feature: str = Field(..., examples=["PIFLT"])
    id: int = Field(..., examples=[104])


class LicensedRecurringItem(BaseModel):
    """Pydantic model representing the LicensedRecurringItem schema."""

    days: int = Field(..., examples=[30])
    feature: str = Field(..., examples=["PIGES"])
    id: int = Field(..., examples=[112])


class LicensedTestItem(BaseModel):
    """Pydantic model representing the LicensedTestItem schema."""

    days: int = Field(..., examples=[30])
    feature: str = Field(..., examples=["PIGES"])
    id: int = Field(..., examples=[112])


class LicenseStatus(BaseModel):
    """Pydantic model representing the LicenseStatus schema."""

    licensed_lifetime: list[LicensedLifetimeItem]
    licensed_recurring: list[LicensedRecurringItem]
    licensed_test: list[LicensedTestItem]
    test_license_available: bool = Field(
        ..., description="The test license is still available for activation"
    )


class State5(Enum):
    """Pydantic model representing the State5 schema."""

    ENABLED = "ENABLED"
    TEST_ENABLED = "TEST_ENABLED"
    EXPIRED = "EXPIRED"
    NOT_LICENSED = "NOT_LICENSED"


class License(BaseModel):
    """Pydantic model representing the License schema."""

    feature: str = Field(..., examples=["PIPAB"])
    id: int = Field(..., examples=[1000])
    remaining_days: int = Field(
        ...,
        description="The number of days remaining before expiration (-1 => lifetime)",
        examples=[10],
    )
    state: State5 = Field(..., description="State of the license", examples=["ENABLED"])
    test_license_available: bool = Field(
        ..., description="The test license is still available for activation"
    )


class LicenseStatusDetailed(BaseModel):
    """Pydantic model representing the LicenseStatusDetailed schema."""

    licenses: list[License] | None = None


class LightSettings(BaseModel):
    """Pydantic model representing the LightSettings schema."""

    light_frequency: float | None = Field(
        None,
        description="Optional value. The frequency of dominant LED lights in Hz.",
        examples=[100.5],
    )
    power_frequency: float = Field(..., description="The power frequency in Hz.", examples=[50.0])


class Line(RootModel[list[Coord2d]]):
    """Pydantic model representing the Line schema."""

    root: list[Coord2d] = Field(
        ...,
        description="JSON representation of lines",
        examples=[[[23.3, 12.0], [47.2, 3.141]]],
        max_length=2,
        min_length=2,
        title="Line",
    )


class LiveCountItem(BaseModel):
    """Pydantic model representing the LiveCountItem schema."""

    bins: list[int | float] | None = Field(None, description="List of bin values.")
    histogram: list[float] | None = Field(
        None, description="List of strictly-increasing bin boundaries.", max_length=19, min_length=1
    )
    id: int | None = Field(None, description="Identification of count")
    logic_id: int | None = Field(None, description="Identification of corresponding logic")
    name: str | None = Field(None, description="Name of count")
    value: int | float | None = None


class LiveCountSpecific(BaseModel):
    """Pydantic model representing the LiveCountSpecific schema."""

    count: LiveCountItem | None = None
    time: AwareDatetime | None = Field(
        None, description="RFC3339 timestamp including timezone offset of contained measurements"
    )


class Type12(Enum):
    """Pydantic model representing the Type12 schema."""

    LINE = "LINE"
    ZONE = "ZONE"


class Geometry1(BaseModel):
    """Pydantic model representing the Geometry1 schema."""

    id: int | None = None
    name: str | None = None
    type: Type12 | None = None


class LiveLogicsItem(BaseModel):
    """Pydantic model representing the LiveLogicsItem schema."""

    counts: list[LiveCountItem] | None = None
    geometries: list[Geometry1] | None = None
    id: int | None = None
    info: str | None = None
    name: str | None = None
    zone_of_interest_id: int | None = None


class LiveLogicsSpecific(BaseModel):
    """Pydantic model representing the LiveLogicsSpecific schema."""

    logic: LiveLogicsItem | None = None
    time: AwareDatetime | None = Field(
        None, description="RFC3339 timestamp including timezone offset of contained measurements"
    )


class Type13(Enum):
    """Pydantic model representing the Type13 schema."""

    XLT_CUSTOM = "XLT_CUSTOM"
    XLT_ZONE_OCCUPANCY_COUNT = "XLT_ZONE_OCCUPANCY_COUNT"
    XLT_LINE_IN_OUT_COUNT = "XLT_LINE_IN_OUT_COUNT"
    XLT_LINE_LATE_COUNT = "XLT_LINE_LATE_COUNT"
    XLT_ZONE_IN_OUT_COUNT = "XLT_ZONE_IN_OUT_COUNT"
    XLT_GROUP_LINE_IN_OUT_COUNT = "XLT_GROUP_LINE_IN_OUT_COUNT"
    XLT_GROUP_LINE_LATE_COUNT = "XLT_GROUP_LINE_LATE_COUNT"
    XLT_BICYCLE_LINE_IN_OUT_COUNT = "XLT_BICYCLE_LINE_IN_OUT_COUNT"
    XLT_BICYCLE_LINE_LATE_COUNT = "XLT_BICYCLE_LINE_LATE_COUNT"
    XLT_PRAM_LINE_IN_OUT_COUNT = "XLT_PRAM_LINE_IN_OUT_COUNT"
    XLT_PRAM_LINE_LATE_COUNT = "XLT_PRAM_LINE_LATE_COUNT"
    XLT_WHEELCHAIR_LINE_IN_OUT_COUNT = "XLT_WHEELCHAIR_LINE_IN_OUT_COUNT"
    XLT_WHEELCHAIR_LINE_LATE_COUNT = "XLT_WHEELCHAIR_LINE_LATE_COUNT"
    XLT_SHOPPING_CART_LINE_IN_OUT_COUNT = "XLT_SHOPPING_CART_LINE_IN_OUT_COUNT"
    XLT_SHOPPING_CART_LINE_LATE_COUNT = "XLT_SHOPPING_CART_LINE_LATE_COUNT"
    XLT_ZONE_DOOR_COUNT = "XLT_ZONE_DOOR_COUNT"
    XLT_QUEUE_STATISTICS = "XLT_QUEUE_STATISTICS"
    XLT_WRONG_WAY_DETECTION = "XLT_WRONG_WAY_DETECTION"
    XLT_4X_LINE_IN_OUT_COUNT = "XLT_4X_LINE_IN_OUT_COUNT"
    XLT_4X_LINE_LATE_COUNT = "XLT_4X_LINE_LATE_COUNT"
    XLT_4X_ZONE_COUNT = "XLT_4X_ZONE_COUNT"


class Logic1(BaseModel):
    """Pydantic model representing the Logic1 schema."""

    id: int | None = Field(None, description="Identification of logic.")
    layer_id: int | None = None
    name: str = Field(..., description="Name of the logic.")
    optional_data: str | None = Field(
        None, description="Optional string associated with the logic."
    )
    type: Type13 | None = Field(None, description="Template type.")


class LogicCollection(BaseModel):
    """Pydantic model representing the LogicCollection schema."""

    logics: list[Logic1] | None = None


class Matrix2d(RootModel[list[Coord2d]]):
    """Pydantic model representing the Matrix2d schema."""

    root: list[Coord2d] = Field(
        ...,
        description="JSON representation of matrices",
        examples=[[[1, 0], [0, 1]]],
        max_length=2,
        min_length=2,
        title="Matrix2D",
    )


class Matrix3d(RootModel[list[Coord3d]]):
    """Pydantic model representing the Matrix3d schema."""

    root: list[Coord3d] = Field(
        ...,
        description="JSON representation of matrices",
        examples=[[[1, 0, 0], [0, 1, 0], [0, 0, 1]]],
        max_length=3,
        min_length=3,
        title="Matrix3D",
    )


class MdnsConfig(BaseModel):
    """Pydantic model representing the MdnsConfig schema."""

    mdns_enabled: bool
    scan_period_ms: int | None = 600


class Service1(BaseModel):
    """Pydantic model representing the Service1 schema."""

    hostname: str = Field(..., description="Hostname of the device providing the service")
    ip: str = Field(..., description="IP Address of the service")
    name: str = Field(..., description="Instance name")
    port: int = Field(..., description="port to access the service")
    protocol: str = Field(..., description="service protocol")
    txt: dict[str, str] = Field(
        ...,
        description="Dictionary of TXT records",
        examples=[{"txtvers": "1", "version": "2.1.1"}],
    )
    type: str = Field(..., description="service mdns type")
    hosname: str | None = Field(None, description="Hostname of the device providing the service")


class MdnsState(BaseModel):
    """Pydantic model representing the MdnsState schema."""

    services: list[Service1]


class MetaDataConfig(Enum):
    """Pydantic model representing the MetaDataConfig schema."""

    NONE = "NONE"
    REFERENCED = "REFERENCED"
    FULL = "FULL"


class ObjectType1(Enum):
    """Pydantic model representing the ObjectType1 schema."""

    PERSON = "PERSON"
    GROUP = "GROUP"
    BICYCLE = "BICYCLE"
    PRAM = "PRAM"
    WHEELCHAIR = "WHEELCHAIR"
    SHOPPING_CART = "SHOPPING_CART"


class ZoneOfInterest(BaseModel):
    """Pydantic model representing the ZoneOfInterest schema."""

    enabled: bool | None = None
    zoi_id: int | None = Field(None, description="id of zone of interest")


class MonitorConfig(BaseModel):
    """Pydantic model representing the MonitorConfig schema."""

    daily_quota: int | None = Field(
        65000,
        description="Number of bytes the connection is allowed to use per day",
        examples=[65000],
    )
    enabled: bool | None = True


class MonitorState(BaseModel):
    """Pydantic model representing the MonitorState schema."""

    daily_quota: int | None = Field(
        None,
        description="Number of bytes the connection is allowed to use per day",
        examples=[65000],
    )
    remaining_quota: int | None = Field(
        None, description="Number of bytes allowed to use", examples=[64000]
    )
    total_used_since_boot: int | None = Field(
        None, description="Number of bytes already used since boot", examples=[1000]
    )


class MonitorUpload(BaseModel):
    """Pydantic model representing the MonitorUpload schema."""

    could_reach_xovis: bool = Field(..., description="Did last attemp reach out Xovis")
    error: Error | None = Field(
        None, description="Error details of the last time an attemp to reach out Xovis was done"
    )
    last_valid_reach_utc: str = Field(
        ...,
        description="Last time that Xovis could be reached out by Monitor service",
        examples=["2020-07-17T11:15:46"],
    )


class Multisensor(BaseModel):
    """Pydantic model representing the Multisensor schema."""

    enabled: bool | None = Field(None, description="State of module")


class License1(BaseModel):
    """Pydantic model representing the License1 schema."""

    feature: str | None = Field(None, examples=["PIPAB"])
    id: int | None = Field(None, examples=[1000])
    state: State5 | None = Field(None, description="State of the license", examples=["ENABLED"])


class MultisensorsLimits(BaseModel):
    """Pydantic model representing the MultisensorsLimits schema."""

    max_number_of_multisensors: int | None = Field(None, examples=[8])
    max_number_of_sensors_per_multisensor: int | None = Field(None, examples=[200])
    min_number_of_multisensors: int | None = Field(None, examples=[0])


class NetworkIpv4Settings(BaseModel):
    """Pydantic model representing the NetworkIpv4Settings schema."""

    address: IPv4Address | None = Field(
        None, description="IPv4 address of sensor.", examples=["10.10.20.12"]
    )
    dhcp_enabled: bool | None = Field(
        None,
        description="Indicates whether DHCP is enabled or not. Missing properties defaults to false.",
        examples=[False],
    )
    dns_entries: list[IPv4Address] | None = Field(
        None,
        description="List of DNS (domain name servers).",
        examples=[["1.1.1.1", "4.4.4.4", "8.8.8.8"]],
    )
    fallback_enabled: bool | None = Field(
        None,
        description="Enable the IPv4 address fallback to 192.168.1.168 when no DHCP lease is obtained",
        examples=[True],
    )
    gateway: IPv4Address | None = Field(
        None,
        description="Default route in IPv4 subnet for outbound traffic.",
        examples=["10.10.20.1"],
    )
    netmask: IPv4Address | None = Field(
        None, description="Network mask of IPv4 subnet.", examples=["255.255.255.0"]
    )


class NetworkIpv6Settings(BaseModel):
    """Pydantic model representing the NetworkIpv6Settings schema."""

    address: str | None = Field(
        None,
        description="IPv6 address of sensor, if DHCPv6 is disabled. Must include a prefix.",
        examples=["2001:db8:6b2:bfe7:9880:abcd:1234:5678/64"],
    )
    dhcp_enabled: bool = Field(
        ...,
        description="Indicates whether DHCPv6 / IA_NA is enabled or not. Default is disabled.",
        examples=[False],
    )
    dns_entries: list[str] | None = Field(
        None, description="List of DNS servers to use.", examples=[["2001:db8::abcd:1234:5678"]]
    )
    gateway: str | None = Field(
        None,
        description="Default gateway for IPv6 traffic.",
        examples=["fe80::ae1f:abcd:1234:5678"],
    )
    ipv6_enabled: bool = Field(
        ..., description="Enable the IPv6 protocol, default is disabled.", examples=[False]
    )
    slaac_enabled: bool = Field(
        ...,
        description="Enable stateless IPv6 address configuration, default is enabled.",
        examples=[True],
    )


class NetworkProxy(BaseModel):
    """Pydantic model representing the NetworkProxy schema."""

    enabled: bool = Field(
        ..., description="Indicates whether proxy is enabled or not.", examples=[True]
    )
    pass_: constr(max_length=128) | None = Field(
        None, alias="pass", description="User password", examples=["test"]
    )
    port: conint(ge=0, le=65535) | None = Field(
        None, description="Port of proxy server.", examples=[8080]
    )
    server: constr(max_length=255) | None = Field(
        None, description="Proxy url.", examples=["www.example.com"]
    )
    user: constr(max_length=128) | None = Field(
        None, description="User identifier", examples=["root"]
    )


class DhcpState(Enum):
    """Pydantic model representing the DhcpState schema."""

    disabled = "disabled"
    init = "init"
    requesting = "requesting"
    bound = "bound"
    fallback = "fallback"
    shutdown = "shutdown"
    unknown = "unknown"


class Ipv4(NetworkIpv4Settings):
    """Pydantic model representing the Ipv4 schema."""

    dhcp_state: DhcpState | None = Field(
        None,
        description="When DHCP is enabled indicate in which state DHCP client is located",
        examples=["bound"],
    )


class Ipv6(BaseModel):
    """Pydantic model representing the Ipv6 schema."""

    addresses: list[str] | None = None
    dns_entries: list[str] | None = None
    gateways: list[str] | None = None


class Link(BaseModel):
    """Pydantic model representing the Link schema."""

    mac: str = Field(..., description="MAC (link-layer address)", examples=["08:80:39:5e:6c:2b"])
    mtu: int = Field(..., description="MTU (maximum transmission unit)", examples=[1500])
    rx_bytes: int | None = Field(None, examples=[64633124])
    rx_dropped: int | None = Field(None, examples=[0])
    rx_errors: int | None = Field(None, examples=[0])
    rx_frame_errors: int | None = Field(None, examples=[123781])
    rx_over_errors: int | None = Field(None, examples=[0])
    rx_packets: int | None = Field(None, examples=[64633124])
    tx_errors: int | None = None
    tx_packets: int | None = Field(None, examples=[123781])


class Details2(BaseModel):
    """Pydantic model representing the Details2 schema."""

    ipv4: Ipv4 = Field(..., description="IPv4 related status information")
    ipv6: Ipv6 = Field(..., description="IPv4 related status information")
    link: Link


class State7(Enum):
    """Pydantic model representing the State7 schema."""

    OK = "OK"
    WARN = "WARN"
    ERROR = "ERROR"


class NetworkState(BaseModel):
    """Pydantic model representing the NetworkState schema."""

    details: Details2
    state: State7 = Field(..., description="State of module")


class Normalization(Enum):
    """Pydantic model representing the Normalization schema."""

    NONE = "NONE"
    LEVEL_1 = "LEVEL_1"


class Type14(Enum):
    """Pydantic model representing the Type14 schema."""

    XLT_BICYCLE_LINE_IN_OUT_COUNT = "XLT_BICYCLE_LINE_IN_OUT_COUNT"
    XLT_BICYCLE_LINE_LATE_COUNT = "XLT_BICYCLE_LINE_LATE_COUNT"
    XLT_WHEELCHAIR_LINE_IN_OUT_COUNT = "XLT_WHEELCHAIR_LINE_IN_OUT_COUNT"
    XLT_WHEELCHAIR_LINE_LATE_COUNT = "XLT_WHEELCHAIR_LINE_LATE_COUNT"
    XLT_SHOPPING_CART_LINE_IN_OUT_COUNT = "XLT_SHOPPING_CART_LINE_IN_OUT_COUNT"
    XLT_SHOPPING_CART_LINE_LATE_COUNT = "XLT_SHOPPING_CART_LINE_LATE_COUNT"
    XLT_PRAM_LINE_IN_OUT_COUNT = "XLT_PRAM_LINE_IN_OUT_COUNT"
    XLT_PRAM_LINE_LATE_COUNT = "XLT_PRAM_LINE_LATE_COUNT"


class ObjectLineCountLogicTemplate(BaseModel):
    """Pydantic model representing the ObjectLineCountLogicTemplate schema."""

    options: BaseLineCountTemplateOptions | None = None
    type: Literal[
        "XLT_BICYCLE_LINE_IN_OUT_COUNT",
        "XLT_BICYCLE_LINE_LATE_COUNT",
        "XLT_PRAM_LINE_IN_OUT_COUNT",
        "XLT_PRAM_LINE_LATE_COUNT",
        "XLT_SHOPPING_CART_LINE_IN_OUT_COUNT",
        "XLT_SHOPPING_CART_LINE_LATE_COUNT",
        "XLT_WHEELCHAIR_LINE_IN_OUT_COUNT",
        "XLT_WHEELCHAIR_LINE_LATE_COUNT",
    ]


class ObjectType2(Enum):
    """Pydantic model representing the ObjectType2 schema."""

    PERSON = "PERSON"
    BICYCLE = "BICYCLE"
    GROUP = "GROUP"
    PRAM = "PRAM"
    WHEELCHAIR = "WHEELCHAIR"
    SHOPPING_CART = "SHOPPING_CART"


class ObjectTypes1(Enum):
    """Pydantic model representing the ObjectTypes1 schema."""

    ALL = "ALL"
    NONE = "NONE"


class ObjectTypes(RootModel[list[ObjectType2] | ObjectTypes1]):
    """Pydantic model representing the ObjectTypes schema."""

    root: list[ObjectType2] | ObjectTypes1


class Type15(Enum):
    """Pydantic model representing the Type15 schema."""

    true = "true"
    false = "false"


class Operand(BaseModel):
    """Pydantic model representing the Operand schema."""

    type: Literal["true", "false"]


class FaceMask(Enum):
    """Pydantic model representing the FaceMask schema."""

    MASK = "MASK"
    NO_MASK = "NO_MASK"
    NOT_SURE = "NOT_SURE"


class Type16(Enum):
    """Pydantic model representing the Type16 schema."""

    has_face_mask = "has_face_mask"


class OperandHasFaceMask(BaseModel):
    """Pydantic model representing the OperandHasFaceMask schema."""

    face_mask: FaceMask | None = None
    type: Literal["has_face_mask"]


class Gender(Enum):
    """Pydantic model representing the Gender schema."""

    NOT_SURE = "NOT_SURE"
    MALE = "MALE"
    FEMALE = "FEMALE"


class Type17(Enum):
    """Pydantic model representing the Type17 schema."""

    has_gender = "has_gender"


class OperandHasGender(BaseModel):
    """Pydantic model representing the OperandHasGender schema."""

    gender: Gender | None = None
    type: Literal["has_gender"]


class Type18(Enum):
    """Pydantic model representing the Type18 schema."""

    has_first_interaction_face_mask = "has_first_interaction_face_mask"


class OperandHasInteractionFaceMask(BaseModel):
    """Pydantic model representing the OperandHasInteractionFaceMask schema."""

    face_mask: FaceMask | None = None
    geometry_id: int | None = None
    type: Literal["has_first_interaction_face_mask"]


class Type19(Enum):
    """Pydantic model representing the Type19 schema."""

    has_first_interaction_gender = "has_first_interaction_gender"


class OperandHasInteractionGender(BaseModel):
    """Pydantic model representing the OperandHasInteractionGender schema."""

    gender: Gender | None = None
    geometry_id: int | None = None
    type: Literal["has_first_interaction_gender"]


class Tag(Enum):
    """Pydantic model representing the Tag schema."""

    NO_TAG = "NO_TAG"
    TAG_1 = "TAG_1"
    TAG_2 = "TAG_2"
    TAG_3 = "TAG_3"
    NOT_SURE = "NOT_SURE"


class Type20(Enum):
    """Pydantic model representing the Type20 schema."""

    has_first_interaction_tag = "has_first_interaction_tag"


class OperandHasInteractionTag(BaseModel):
    """Pydantic model representing the OperandHasInteractionTag schema."""

    geometry_id: int | None = None
    tag: Tag | None = None
    type: Literal["has_first_interaction_tag"]


class Type21(Enum):
    """Pydantic model representing the Type21 schema."""

    has_tag = "has_tag"


class OperandHasTag(BaseModel):
    """Pydantic model representing the OperandHasTag schema."""

    tag: Tag | None = None
    type: Literal["has_tag"]


class Type22(Enum):
    """Pydantic model representing the Type22 schema."""

    first_interaction_person_height_bigger_than = "first_interaction_person_height_bigger_than"
    first_interaction_person_height_smaller_than = "first_interaction_person_height_smaller_than"
    first_interaction_person_height_strictly_bigger_than = (
        "first_interaction_person_height_strictly_bigger_than"
    )
    first_interaction_person_height_strictly_smaller_than = (
        "first_interaction_person_height_strictly_smaller_than"
    )


class OperandInteractionPersonHeight(BaseModel):
    """Pydantic model representing the OperandInteractionPersonHeight schema."""

    geometry_id: int | None = None
    height: float | None = None
    type: Literal[
        "first_interaction_person_height_bigger_than",
        "first_interaction_person_height_smaller_than",
        "first_interaction_person_height_strictly_bigger_than",
        "first_interaction_person_height_strictly_smaller_than",
    ]


class Type23(Enum):
    """Pydantic model representing the Type23 schema."""

    has_crossed_line = "has_crossed_line"


class OperandLine(BaseModel):
    """Pydantic model representing the OperandLine schema."""

    line_id: int | None = None
    type: Literal["has_crossed_line"]


class Direction(Enum):
    """Pydantic model representing the Direction schema."""

    forward = "forward"
    backward = "backward"
    nocross = "nocross"


class Type24(Enum):
    """Pydantic model representing the Type24 schema."""

    first_line_cross_direction = "first_line_cross_direction"
    last_line_cross_direction = "last_line_cross_direction"


class OperandLineCrossDirection(BaseModel):
    """Pydantic model representing the OperandLineCrossDirection schema."""

    direction: Direction | None = None
    line_id: int | None = None
    type: Literal["first_line_cross_direction", "last_line_cross_direction"]


class Type25(Enum):
    """Pydantic model representing the Type25 schema."""

    number_of_line_crossings = "number_of_line_crossings"
    number_of_forward_line_crossings = "number_of_forward_line_crossings"
    number_of_backward_line_crossings = "number_of_backward_line_crossings"


class OperandLineCrossings(BaseModel):
    """Pydantic model representing the OperandLineCrossings schema."""

    line_id: int | None = None
    type: Literal[
        "number_of_line_crossings",
        "number_of_forward_line_crossings",
        "number_of_backward_line_crossings",
    ]
    value: int | None = None


class Type26(Enum):
    """Pydantic model representing the Type26 schema."""

    person_height_bigger_than = "person_height_bigger_than"
    person_height_smaller_than = "person_height_smaller_than"
    person_height_strictly_bigger_than = "person_height_strictly_bigger_than"
    person_height_strictly_smaller_than = "person_height_strictly_smaller_than"


class OperandPersonHeight(BaseModel):
    """Pydantic model representing the OperandPersonHeight schema."""

    height: float | None = None
    type: Literal[
        "person_height_bigger_than",
        "person_height_smaller_than",
        "person_height_strictly_bigger_than",
        "person_height_strictly_smaller_than",
    ]


class Type27(Enum):
    """Pydantic model representing the Type27 schema."""

    has_visited_zone = "has_visited_zone"
    is_in_zone = "is_in_zone"
    is_created_in_zone = "is_created_in_zone"


class OperandZone(BaseModel):
    """Pydantic model representing the OperandZone schema."""

    type: Literal["has_visited_zone", "is_in_zone", "is_created_in_zone"]
    zone_id: int | None = None


class Type28(Enum):
    """Pydantic model representing the Type28 schema."""

    zone_dwell_time_bigger_than = "zone_dwell_time_bigger_than"
    zone_dwell_time_smaller_than = "zone_dwell_time_smaller_than"
    zone_dwell_time_cumulative_bigger_than = "zone_dwell_time_cumulative_bigger_than"
    zone_dwell_time_cumulative_smaller_than = "zone_dwell_time_cumulative_smaller_than"
    zone_dwell_time_strictly_bigger_than = "zone_dwell_time_strictly_bigger_than"
    zone_dwell_time_strictly_smaller_than = "zone_dwell_time_strictly_smaller_than"
    zone_dwell_time_cumulative_strictly_bigger_than = (
        "zone_dwell_time_cumulative_strictly_bigger_than"
    )
    zone_dwell_time_cumulative_strictly_smaller_than = (
        "zone_dwell_time_cumulative_strictly_smaller_than"
    )


class OperandZoneDwellTime(BaseModel):
    """Pydantic model representing the OperandZoneDwellTime schema."""

    time: float | None = None
    type: Literal[
        "zone_dwell_time_bigger_than",
        "zone_dwell_time_smaller_than",
        "zone_dwell_time_strictly_bigger_than",
        "zone_dwell_time_strictly_smaller_than",
        "zone_dwell_time_cumulative_bigger_than",
        "zone_dwell_time_cumulative_smaller_than",
        "zone_dwell_time_cumulative_strictly_bigger_than",
        "zone_dwell_time_cumulative_strictly_smaller_than",
    ]
    zone_id: int | None = None


class Type29(Enum):
    """Pydantic model representing the Type29 schema."""

    number_of_zone_entries = "number_of_zone_entries"
    number_of_zone_exits = "number_of_zone_exits"


class OperandZoneVisits(BaseModel):
    """Pydantic model representing the OperandZoneVisits schema."""

    type: Literal["number_of_zone_entries", "number_of_zone_exits"]
    value: int | None = None
    zone_id: int | None = None


class PasswordStrengthPolicy(BaseModel):
    """Pydantic model representing the PasswordStrengthPolicy schema."""

    max_characters: conint(ge=4, le=64) = Field(
        ..., description="Maximal number of characters", examples=[64]
    )
    min_characters: conint(ge=4, le=64) = Field(
        ..., description="Minimal number of characters", examples=[4]
    )
    min_lowercase_characters: int = Field(
        ..., description="Minimal number of lowercase characters", examples=[0]
    )
    min_numeric_characters: int = Field(
        ..., description="Minimal number of numerical characters", examples=[0]
    )
    min_special_characters: int = Field(
        ...,
        description="Minimal number of special characters such as\n```\n!\" #$%&'()*+,-./:;<=>?@[\\]^_`{|}~\n```\n",
        examples=[0],
    )
    min_uppercase_characters: int = Field(
        ..., description="Minimal number of uppercase characters", examples=[0]
    )
    smk: str | None = Field(None, description="SMK", examples=["abcdef"])


class PathStitchingSettings(BaseModel):
    """Pydantic model representing the PathStitchingSettings schema."""

    enabled: bool | None = None
    max_distance: float | None = Field(
        None, description="The maximum distance between two tracks in [m].", examples=[2.0]
    )
    max_time: float | None = Field(
        None, description="The maximum time a track is kept for stitching in [s].", examples=[5.0]
    )
    zone_ids: list[float] | None = Field(
        None, description="The ids of the zone where disapearing tracks should be stitched"
    )


class PersonHeightSettings(BaseModel):
    """Pydantic model representing the PersonHeightSettings schema."""

    height_correction: float | None = None


class Options2(BaseLineCountTemplateOptions, BasePersonLineCountTemplateOptions):
    """Pydantic model representing the Options2 schema."""

    recognize_face_mask: bool | None = None


class Type30(Enum):
    """Pydantic model representing the Type30 schema."""

    XLT_LINE_IN_OUT_COUNT = "XLT_LINE_IN_OUT_COUNT"
    XLT_LINE_LATE_COUNT = "XLT_LINE_LATE_COUNT"


class PersonLineCountLogicTemplate(BaseModel):
    """Pydantic model representing the PersonLineCountLogicTemplate schema."""

    options: Options2 | None = None
    type: Literal["XLT_LINE_IN_OUT_COUNT", "XLT_LINE_LATE_COUNT"]


class PipSettings(BaseModel):
    """Pydantic model representing the PipSettings schema."""

    enabled: bool
    max_bytes_per_second: int | None = Field(
        None,
        description="Maximum number of bytes the PIP connection is allowed to use per second (5 second average)",
        examples=[4000],
    )
    monthly_quota: int | None = Field(
        None,
        description="Number of bytes the connection is allowed to use per month",
        examples=[50000000],
    )


class PipState(BaseModel):
    """Pydantic model representing the PipState schema."""

    connected: bool = Field(..., description="Is the sensor currently connected to Xovis PIP")
    quota_used: int = Field(
        ..., description="How many bytes of the monthly quota is already used up"
    )
    settings: PipSettings


class Polygon(RootModel[list[Coord2d]]):
    """Pydantic model representing the Polygon schema."""

    root: list[Coord2d] = Field(
        ...,
        description="JSON representation of polygons",
        examples=[[[23.3, 12.0], [47.2, 3.141], [12.0, 0.0]]],
        min_length=3,
        title="Polygon",
    )


class PrivacyMode1(IntEnum):
    """Pydantic model representing the PrivacyMode1 schema."""

    integer_0 = 0
    integer_1 = 1
    integer_2 = 2
    integer_3 = 3


class PrivacyMode(BaseModel):
    """Pydantic model representing the PrivacyMode schema."""

    privacy_mode: PrivacyMode1 = Field(..., description="Level of privacy", examples=[0])
    smk: str | None = Field(None, examples=["abcdef"])


class PrivacySaltSettings(BaseModel):
    """Pydantic model representing the PrivacySaltSettings schema."""

    salt: str = Field(
        ...,
        description="Salt added to MAC address before hashing. Allowed length between 0 and 128.",
        examples=["yourSalt"],
    )
    smk: str | None = Field(None, examples=["23db64b5"])


class Algorithm(Enum):
    """Pydantic model representing the Algorithm schema."""

    MD5 = "MD5"
    SHA1 = "SHA1"
    SHA256 = "SHA256"
    SHA512 = "SHA512"


class MacHashing(BaseModel):
    """Pydantic model representing the MacHashing schema."""

    algorithm: Algorithm | None = Field(
        None, description="Algorithm used to hash MAC addresses.", examples=["MD5"]
    )
    bluetooth: bool | None = Field(
        None, description="Enable MAC address hashing of Bluetooth devices.", examples=[True]
    )
    wifi: bool | None = Field(
        None, description="Enable MAC address hashing of WiFi devices.", examples=[False]
    )


class PrivacySettings(BaseModel):
    """Pydantic model representing the PrivacySettings schema."""

    mac_hashing: MacHashing | None = Field(
        None, description="Configuration for the hashing of monitored MAC addresses."
    )
    smk: str | None = Field(None, examples=["23db64b5"])


class Type31(Enum):
    """Pydantic model representing the Type31 schema."""

    None_ = "None"
    RCM1 = "RCM1"
    RCM2 = "RCM2"
    RCM3 = "RCM3"


class RecalibrationSettings(BaseModel):
    """Pydantic model representing the RecalibrationSettings schema."""

    period: float | None = Field(
        None,
        description="Optional value. The period for continuous recalibration.",
        examples=[60.0],
    )
    type: Type31 | None = Field(None, description="The recalibration type.", examples=["RCM3"])


class ActiveType(Enum):
    """Pydantic model representing the ActiveType schema."""

    None_ = "None"
    RCM1 = "RCM1"
    RCM2 = "RCM2"
    RCM3 = "RCM3"


class Status3(Enum):
    """Pydantic model representing the Status3 schema."""

    None_ = "None"
    Update_images = "Update_images"
    In_progress = "In_progress"
    Interrupted = "Interrupted"
    Ready = "Ready"
    Failed = "Failed"
    Applied = "Applied"


class RecalibrationSettingsWithStatus(BaseModel):
    """Pydantic model representing the RecalibrationSettingsWithStatus schema."""

    active_type: ActiveType | None = Field(
        None, description="The recalibration type in use.", examples=["RCM3"]
    )
    period: float | None = Field(
        None,
        description="Optional value. The period for continuous recalibration.",
        examples=[60.0],
    )
    status: Status3 | None = Field(
        None, description="The status of the recalibration.", examples=["applied"]
    )
    type: Type31 | None = Field(None, description="The recalibration type.", examples=["RCM3"])


class Status4(Enum):
    """Pydantic model representing the Status4 schema."""

    scheduled = "scheduled"
    in_progress = "in_progress"
    complete = "complete"


class RecordingSchedule(BaseModel):
    """Pydantic model representing the RecordingSchedule schema."""

    include_singlesensor_recordings: bool | None = None
    time_end: float | None = Field(
        None,
        description="End of time interval (milliseconds since epoch in UTC).",
        examples=[1758894300000],
    )
    time_start: float | None = Field(
        None,
        description="Begin of time interval (milliseconds since epoch in UTC).",
        examples=[1758894000000],
    )


class Type33(Enum):
    """Pydantic model representing the Type33 schema."""

    none = "none"
    sensor = "sensor"
    floor_plan = "floor_plan"


class Reference(BaseModel):
    """Pydantic model representing the Reference schema."""

    mac_address: str | None = Field(
        None, description="MAC address of the sensor", examples=["00:00:00:00:00:00"]
    )
    type: Type33 | None = Field(None, examples=["sensor"])


class RemoteConnection(BaseModel):
    """Pydantic model representing the RemoteConnection schema."""

    enabled: bool = Field(..., description="Is the remote connection enabled")
    host: str = Field(
        ..., description="URI to remote connection server", examples=["support.xovis.com"]
    )
    port: int = Field(..., description="Port of remote connection server", examples=[8234])
    token: str | None = Field(
        None,
        description="Token/password provided by server side base64 encoded",
        examples=["cGFzc3dvcmQ="],
    )
    uri: AnyUrl = Field(..., description="URI of remote connection server", examples=["/support"])
    use_proxy: bool | None = Field(None, description="Use the proxy if configured")


class RemoteConnectionState(RemoteConnection):
    """Pydantic model representing the RemoteConnectionState schema."""

    connected: bool = Field(
        ..., description="Indicates whether remote connection is connected or not", examples=[True]
    )
    last_status_string: str | None = Field(
        None,
        description="Last status report",
        examples=["X509 - Certificate verification failed, e.g. CRL, CA or signature check failed"],
    )
    last_status_time: float | None = Field(
        None,
        description="Timestamp of the status string (seconds since epoch in UTC).",
        examples=[1654871622],
    )
    last_status_time_ms: float | None = Field(
        None,
        description="Timestamp of the status string (milliseconds since epoch in UTC).",
        examples=[1654871622000],
    )


class RemoteServicesSettings(BaseModel):
    """Pydantic model representing the RemoteServicesSettings schema."""

    alt_server_ip: str | None = Field(
        None,
        description="Alternative IP address for iot.xovis.com that needs to forward there on TCP level.",
        examples=["17.23.45.200"],
    )
    alt_server_port: float | None = Field(
        None,
        description="Alternative port for iot.xovis.com that needs to forward there on TCP level.",
        examples=[12345],
    )
    enabled: bool
    max_bytes_per_second: int | None = Field(
        None,
        description="Maximum number of bytes the remote connection is allowed to use per second (10 second average)",
        examples=[4000],
    )


class RemoteServicesState(BaseModel):
    """Pydantic model representing the RemoteServicesState schema."""

    active_services: dict[str, bool] | None = Field(
        None,
        description="Dictionary of service:enabled",
        examples=[{"monitor_service": False, "update_service": True}],
    )
    connected: bool = Field(..., description="Is the sensor currently connected to Xovis PIP")


class Method1(Enum):
    """Pydantic model representing the Method1 schema."""

    GET = "GET"
    PUT = "PUT"
    POST = "POST"
    DELETE = "DELETE"


class Resolutions(Enum):
    """Pydantic model representing the Resolutions schema."""

    ONE_DAY = "ONE_DAY"
    TWELVE_HOURS = "TWELVE_HOURS"
    SIX_HOURS = "SIX_HOURS"
    ONE_HOUR = "ONE_HOUR"
    THIRTY_MINUTES = "THIRTY_MINUTES"
    FIFTEEN_MINUTES = "FIFTEEN_MINUTES"
    FIVE_MINUTES = "FIVE_MINUTES"
    ONE_MINUTE = "ONE_MINUTE"
    FIVE_SECONDS = "FIVE_SECONDS"
    TWO_AND_A_HALF_SECONDS = "TWO_AND_A_HALF_SECONDS"
    ONE_SECOND = "ONE_SECOND"
    HALF_SECOND = "HALF_SECOND"
    QUARTER_SECOND = "QUARTER_SECOND"
    MAX = "MAX"


class SandboxStatus(BaseModel):
    """Pydantic model representing the SandboxStatus schema."""

    ram_usage: int = Field(..., examples=[10000000])
    running: bool


class Method2(Enum):
    """Pydantic model representing the Method2 schema."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class Rights(Enum):
    """Pydantic model representing the Rights schema."""

    public = "public"
    admin = "admin"
    viewer = "viewer"


class SandboxUrlRegistration(BaseModel):
    """Pydantic model representing the SandboxUrlRegistration schema."""

    ext_url: str = Field(..., examples=["/sandbox/"])
    int_url: str = Field(..., examples=["/"])
    method: Method2
    port: int = Field(..., examples=[24000])
    rights: Rights


class SceneEventType(Enum):
    """Pydantic model representing the SceneEventType schema."""

    TRACK_CREATE = "TRACK_CREATE"
    TRACK_DELETE = "TRACK_DELETE"
    LINE_CROSS_FORWARD = "LINE_CROSS_FORWARD"
    LINE_CROSS_BACKWARD = "LINE_CROSS_BACKWARD"
    ZONE_ENTRY = "ZONE_ENTRY"
    ZONE_EXIT = "ZONE_EXIT"
    DOOR_OPEN = "DOOR_OPEN"
    DOOR_CLOSED = "DOOR_CLOSED"


class SceneEventTypes1(Enum):
    """Pydantic model representing the SceneEventTypes1 schema."""

    ALL = "ALL"
    NONE = "NONE"


class SceneEventTypes(RootModel[list[SceneEventType] | SceneEventTypes1]):
    """Pydantic model representing the SceneEventTypes schema."""

    root: list[SceneEventType] | SceneEventTypes1


class SceneGeometriesLimits(BaseModel):
    """Pydantic model representing the SceneGeometriesLimits schema."""

    max_elements: int | None = None
    max_elements_per_layer: int | None = None
    max_total_perimeter: int | None = None
    max_total_vertices: int | None = None
    max_vertices_per_element: int | None = None


class Type34(Enum):
    """Pydantic model representing the Type34 schema."""

    LINE = "LINE"
    ZONE = "ZONE"


class SceneGeometry(BaseModel):
    """Pydantic model representing the SceneGeometry schema."""

    geometry: Polygon | Line | None = None
    id: int | None = Field(None, description="Identification of geometry.")
    layer_id: int | None = Field(None, description="Identification of layer.")
    name: str | None = Field(
        None,
        description="Name of the geometry. Can be displayed in the scene and is attached to the geometry events",
    )
    type: Type34 | None = None


class Type35(Enum):
    """Pydantic model representing the Type35 schema."""

    BOARDING = "BOARDING"
    EXCLUSION = "EXCLUSION"
    LEGACY_EXCLUSION = "LEGACY_EXCLUSION"


class SceneMask(BaseModel):
    """Pydantic model representing the SceneMask schema."""

    id: int | None = Field(None, description="Identification of the mask", examples=[21])
    polygon: Polygon | None = None
    type: Type35 | None = Field(None, description="Type of mask")


class SceneMasksLimits(BaseModel):
    """Pydantic model representing the SceneMasksLimits schema."""

    max_elements: int | None = None
    max_total_perimeter: int | None = None
    max_total_vertices: int | None = None


class SchedulerIntervals(Enum):
    """Pydantic model representing the SchedulerIntervals schema."""

    ONE_DAY = "ONE_DAY"
    ONE_HOUR = "ONE_HOUR"
    FIFTEEN_MINUTES = "FIFTEEN_MINUTES"
    FIVE_MINUTES = "FIVE_MINUTES"
    ONE_MINUTE = "ONE_MINUTE"
    THIRTY_SECONDS = "THIRTY_SECONDS"
    FIVE_SECONDS = "FIVE_SECONDS"


class SchedulerRetryModes(Enum):
    """Pydantic model representing the SchedulerRetryModes schema."""

    DROP = "DROP"
    INTERVAL = "INTERVAL"
    INCREASING_DELAY = "INCREASING_DELAY"
    INCREASING_DELAY_EXPONENTIAL = "INCREASING_DELAY_EXPONENTIAL"


class SchedulerTypes(Enum):
    """Pydantic model representing the SchedulerTypes schema."""

    PERIODIC = "PERIODIC"
    IMMEDIATE = "IMMEDIATE"
    INTERVAL = "INTERVAL"


class SensorDirection(BaseModel):
    """Pydantic model representing the SensorDirection schema."""

    active_alpha_deg: float | None = Field(
        None, description="The active rotation angle around the x-axis in degrees.", examples=[6.1]
    )
    active_beta_deg: float | None = Field(
        None, description="The active rotation angle around the y-axis in degrees.", examples=[3.2]
    )
    active_sensor_direction: Coord3d | None = None
    measured_alpha_deg: float | None = Field(
        None,
        description="The measured rotation angle around the x-axis in degrees.",
        examples=[6.1],
    )
    measured_beta_deg: float | None = Field(
        None,
        description="The measured rotation angle around the y-axis in degrees.",
        examples=[3.2],
    )
    measured_sensor_direction: Coord3d | None = None


class Feature(BaseModel):
    """Pydantic model representing the Feature schema."""

    feature: str = Field(..., examples=["PIFLT"])
    id: int = Field(..., examples=[104])


class SensorFeatures(BaseModel):
    """Pydantic model representing the SensorFeatures schema."""

    features: list[Feature]


class SensorGeometry(BaseModel):
    """Pydantic model representing the SensorGeometry schema."""

    alpha_deg: float | None = Field(
        None, description="The rotation angle around the x-axis in degrees.", examples=[6.1]
    )
    beta_deg: float | None = Field(
        None, description="The rotation angle around the y-axis in degrees.", examples=[3.2]
    )
    sensor_direction: Coord3d | None = Field(
        None,
        description="A optional vector pointing into the direction of the sensor. If no vector is specified, the measured sensor direction is used instead.",
    )
    sensor_height: float | None = Field(
        None,
        description="The mounting height of the sensor in meters above the floor.",
        examples=[2.6],
    )


class SensorHeight(BaseModel):
    """Pydantic model representing the SensorHeight schema."""

    active_sensor_height: float | None = Field(
        None,
        description="The mounting height of the sensor in meters above the floor.",
        examples=[2.5],
    )
    measured_sensor_height: float | None = Field(
        None,
        description="The mounting height of the sensor in meters above the floor.",
        examples=[2.6],
    )


class SensorHeightConfiguration(BaseModel):
    """Pydantic model representing the SensorHeightConfiguration schema."""

    center: Coord2d | None = Field(
        None, description="The center of the measurement window.", examples=[[0, 0]]
    )
    coordinate_system: CoordinateSystem | None = None
    radius: float | None = Field(
        None, description="The radius of the measurement window.", examples=[0.125]
    )


class SensorHeightConfigurationLimits(BaseModel):
    """Pydantic model representing the SensorHeightConfigurationLimits schema."""

    coordinate_system: CoordinateSystem | None = None
    max_center_distance: float | None = Field(None, examples=[0.5])
    max_radius: float | None = Field(None, examples=[0.5])
    min_radius: float | None = Field(None, examples=[0.1])


class Illumination(Enum):
    """Pydantic model representing the Illumination schema."""

    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"


class State8(Enum):
    """Pydantic model representing the State8 schema."""

    ENABLED = "ENABLED"
    TEST_ENABLED = "TEST_ENABLED"
    EXPIRED = "EXPIRED"
    NOT_LICENSED = "NOT_LICENSED"


class License2(BaseModel):
    """Pydantic model representing the License2 schema."""

    feature: str | None = Field(None, examples=["PIPAB"])
    id: int | None = Field(None, examples=[1000])
    state: State8 | None = Field(None, description="State of the license", examples=["ENABLED"])


class Protocol7(Enum):
    """Pydantic model representing the Protocol7 schema."""

    http = "http"
    https = "https"


class Status5(Enum):
    """Pydantic model representing the Status5 schema."""

    unknown = "unknown"
    disconnected = "disconnected"
    connecting = "connecting"
    ok = "ok"
    out_of_sync = "out_of_sync"
    mismatch = "mismatch"
    unsupported = "unsupported"
    incompatible = "incompatible"
    unauthorized = "unauthorized"
    privacy_protection = "privacy_protection"
    wlan_multisensor = "wlan_multisensor"
    remote_connection_multisensor = "remote_connection_multisensor"
    wlan_sensor = "wlan_sensor"
    remote_connection_sensor = "remote_connection_sensor"
    unused = "unused"


class SensorInformation(BaseModel):
    """Pydantic model representing the SensorInformation schema."""

    firmware: str | None = Field(None, description="The firmware version", examples=["5.1.0"])
    group: str | None = Field(None, description="Sensor group", examples=["group"])
    illumination: Illumination | None = None
    ip_address: str | None = Field(
        None, description="IP adddress of sensors", examples=["10.10.20.123"]
    )
    licenses: list[License2] | None = None
    mac_address: str | None = Field(
        None, description="MAC address of sensor", examples=["00:00:00:c7:f9:28"]
    )
    name: str | None = Field(None, description="Sensor name", examples=["name"])
    port: float | None = Field(None, description="Port of sensor", examples=[80])
    privacy_mode: float | None = None
    protocol: Protocol7 | None = Field(None, description="Protocol")
    reference: bool | None = Field(None, examples=[True])
    status: Status5 | None = Field(None, description="The status of the sensor", examples=["ok"])
    username: str | None = Field(None, description="User of sensor", examples=["user"])


class SensorInformationPut(BaseModel):
    """Pydantic model representing the SensorInformationPut schema."""

    ip_address: str | None = Field(
        None, description="IP adddress of sensors", examples=["10.10.20.123"]
    )
    password: str | None = Field(None, description="Password of user", examples=["password"])
    port: float | None = Field(None, description="Port of sensor", examples=[80])
    protocol: Protocol7 | None = Field(None, description="Protocol")
    username: str | None = Field(None, description="User of sensor", examples=["username"])


class Metric(Enum):
    """Pydantic model representing the Metric schema."""

    METRIC = "METRIC"
    IMPERIAL = "IMPERIAL"


class SensorRegionInfo(BaseModel):
    """Pydantic model representing the SensorRegionInfo schema."""

    country: str | None = Field("", description="ISO 3166-1 alpha-2 country code", examples=["CH"])
    metric: Metric | None = Field("METRIC", description="Measurement system", examples=["METRIC"])


class Rotation(Enum):
    """Pydantic model representing the Rotation schema."""

    ROTATION_0 = "ROTATION_0"
    ROTATION_90 = "ROTATION_90"
    ROTATION_180 = "ROTATION_180"
    ROTATION_270 = "ROTATION_270"


class SensorRotation(BaseModel):
    """Pydantic model representing the SensorRotation schema."""

    rotation: Rotation | None = Field(
        "ROTATION_0", description="Scene rotation in degrees", examples=["ROTATION_180"]
    )


class SensorShowWizard(BaseModel):
    """Pydantic model representing the SensorShowWizard schema."""

    showWizard: bool | None = Field(None, description="show setup wizard")


class SensorsInformation(BaseModel):
    """Pydantic model representing the SensorsInformation schema."""

    sensors: list[SensorInformation]


class Sequence(BaseModel):
    """Pydantic model representing the Sequence schema."""

    duration: float | None = Field(None, description="Duration of recorded sequence in seconds.")
    frame_number_begin: float | None = None
    frame_number_end: float | None = Field(
        None, description="The frame following the last frame of the sequence."
    )
    hw_bom_revision: str | None = Field(None, examples=["E"])
    hw_pcb_revision: str | None = Field(None, examples=["B"])
    hw_prod_revision: str | None = Field(None, examples=["AB"])
    id: str | None = Field(None, examples=["80:1F:12:73:FE:D7-5497723383564"])
    mac_address: str | None = Field(None, examples=["80:1F:12:73:FE:D7"])
    multisensor_id: float | None = None
    sensor_id: str | None = Field(None, description="DEPRECATED", examples=["80:1F:12:73:FE:D7"])
    sensor_type: str | None = Field(None, examples=["PC2SE"])
    sw_version: str | None = Field(None, examples=["5.3.4-2ca1ffb659"])
    timestamp_ms_begin: float | None = Field(
        None, description="Begin of time interval (milliseconds since epoch in UTC)."
    )
    timestamp_ms_end: float | None = Field(
        None, description="End of time interval (milliseconds since epoch in UTC)."
    )


class Sequences(BaseModel):
    """Pydantic model representing the Sequences schema."""

    sequences: list[Sequence] | None = None


class ServiceModel(BaseModel):
    """Pydantic model representing the ServiceModel schema."""

    hostname: str = Field(..., description="Hostname of the device providing the service")
    ip: str = Field(..., description="IP Address of the service")
    name: str = Field(..., description="Instance name")
    port: int = Field(..., description="port to access the service")
    protocol: str = Field(..., description="service protocol")
    txt: dict[str, str] = Field(
        ...,
        description="Dictionary of TXT records",
        examples=[{"txtvers": "1", "version": "2.1.0"}],
    )
    type: str = Field(..., description="service mdns type")


class Status6(Enum):
    """Pydantic model representing the Status6 schema."""

    scheduled = "scheduled"
    in_progress = "in_progress"
    complete = "complete"


class SinglesensorRecording(BaseModel):
    """Pydantic model representing the SinglesensorRecording schema."""

    mac_address: str | None = Field(None, examples=["00:00:00:00:00:00"])
    recording_id: float | None = None
    sensor_group: str | None = None
    sensor_name: str | None = None
    size: float | None = None
    status: Status6 | None = None


class DigitalInput(Enum):
    """Pydantic model representing the DigitalInput schema."""

    LOW = "LOW"
    HIGH = "HIGH"


class Illumination1(Enum):
    """Pydantic model representing the Illumination1 schema."""

    UNKNOWN = "UNKNOWN"
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"


class SinglesensorStatus(BaseModel):
    """Pydantic model representing the SinglesensorStatus schema."""

    digital_input: DigitalInput | None = Field(
        None, description="Status of digital input (PCT only).", examples=["LOW"]
    )
    exposure_time: float | None = Field(None, examples=[0.01])
    frames_processed: int | None = Field(None, examples=[57])
    gain: float | None = Field(None, examples=[5.0])
    illumination: Illumination1 | None = Field(None, examples=["SUFFICIENT"])
    measured_alpha_deg: float | None = Field(
        None,
        description="The measured rotation angle around the x-axis in degrees.",
        examples=[6.1],
    )
    measured_beta_deg: float | None = Field(
        None,
        description="The measured rotation angle around the y-axis in degrees.",
        examples=[3.2],
    )
    measured_sensor_direction: Coord3d | None = None


class SmkBody(BaseModel):
    """Pydantic model representing the SmkBody schema."""

    smk: str | None = Field(None, examples=["abcdef"])


class State9(Enum):
    """Pydantic model representing the State9 schema."""

    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"


class StereoSettings(BaseModel):
    """Pydantic model representing the StereoSettings schema."""

    disparity_shift: float | None = None


class StitcherLimits(BaseModel):
    """Pydantic model representing the StitcherLimits schema."""

    max_number_of_sensors: float | None = Field(None, examples=[9])


class DataStatus(Enum):
    """Pydantic model representing the DataStatus schema."""

    none = "none"
    available = "available"
    outdated = "outdated"


class Protocol9(Enum):
    """Pydantic model representing the Protocol9 schema."""

    http = "http"
    https = "https"
    unknown = "unknown"


class Status7(Enum):
    """Pydantic model representing the Status7 schema."""

    unknown = "unknown"
    disconnected = "disconnected"
    ok = "ok"
    mismatch = "mismatch"
    incompatible = "incompatible"
    unauthorized = "unauthorized"
    privacy_protection = "privacy_protection"


class StitcherSensorInformation(BaseModel):
    """Pydantic model representing the StitcherSensorInformation schema."""

    data_status: DataStatus | None = Field(
        None, description="Indicates if stitching data available"
    )
    group: str | None = Field(None, description="Sesnor group", examples=["group"])
    id: float | None = None
    ip_address: str | None = Field(
        None, description="IP adddress of sensors", examples=["10.10.20.123"]
    )
    mac_address: str | None = Field(
        None, description="MAC address of sensor", examples=["00:00:00:c7:f9:28"]
    )
    name: str | None = Field(None, description="Sensor name", examples=["name"])
    port: float | None = Field(None, description="Port of sensor", examples=[80])
    protocol: Protocol9 | None = None
    reference: bool | None = Field(None, examples=[True])
    status: Status7 | None = Field(None, description="The status of the sensor")
    username: str | None = Field(None, description="User of sensor", examples=["username"])


class StitcherSensorInformationPost(BaseModel):
    """Pydantic model representing the StitcherSensorInformationPost schema."""

    ip_address: str | None = Field(
        None, description="IP adddress of sensors", examples=["10.20.30.40"]
    )
    mac_address: str | None = Field(
        None, description="MAC address of sensor", examples=["00:00:00:c7:f9:28"]
    )
    password: str | None = Field(None, description="Password of user", examples=["password"])
    port: float | None = Field(None, description="Port of sensor", examples=[80])
    protocol: Protocol9 | None = None
    username: str | None = Field(None, description="User of sensor", examples=["username"])


class StitcherSensorInformationPut(BaseModel):
    """Pydantic model representing the StitcherSensorInformationPut schema."""

    ip_address: str | None = Field(
        None, description="IP adddress of sensors", examples=["10.20.30.40"]
    )
    password: str | None = Field(None, description="Password of user", examples=["password"])
    port: float | None = Field(None, description="Port of sensor", examples=[80])
    protocol: Protocol9 | None = None
    username: str | None = Field(None, description="User of sensor", examples=["username"])


class StitcherSensorsInformation(BaseModel):
    """Pydantic model representing the StitcherSensorsInformation schema."""

    sensors: list[StitcherSensorInformation]


class Mode3(Enum):
    """Pydantic model representing the Mode3 schema."""

    floor = "floor"
    space = "space"


class StitcherSettings(BaseModel):
    """Pydantic model representing the StitcherSettings schema."""

    custom_id: float | None = Field(None, examples=[57])
    group: str | None = Field(None, examples=["my group"])
    mode: Mode3 | None = None
    name: str | None = Field(None, examples=["my multisensor"])


class Status8(Enum):
    """Pydantic model representing the Status8 schema."""

    empty = "empty"
    missing_background = "missing_background"
    complete = "complete"
    applied = "applied"


class StitcherStatus(BaseModel):
    """Pydantic model representing the StitcherStatus schema."""

    status: Status8 | None = None


class Quality(Enum):
    """Pydantic model representing the Quality schema."""

    good = "good"
    acceptable = "acceptable"
    bad = "bad"
    weak = "weak"


class StitchingInfo(BaseModel):
    """Pydantic model representing the StitchingInfo schema."""

    mac_address_1: str | None = Field(None, examples=["00:00:00:00:00:01"])
    mac_address_2: str | None = Field(None, examples=["00:00:00:00:00:02"])
    quality: Quality | None = None


class CoordinateSystem1(Enum):
    """Pydantic model representing the CoordinateSystem1 schema."""

    VIEW = "VIEW"
    STEREOGRAPHIC = "STEREOGRAPHIC"
    IMAGE = "IMAGE"
    UNKNOWN = "UNKNOWN"


class CoordinateSystem2(Enum):
    """Pydantic model representing the CoordinateSystem2 schema."""

    VIEW = "VIEW"
    STEREOGRAPHIC = "STEREOGRAPHIC"
    IMAGE = "IMAGE"
    UNKNOWN = "UNKNOWN"


class Status9(Enum):
    """Pydantic model representing the Status9 schema."""

    disconnected = "disconnected"
    semi_connected = "semi_connected"
    connected = "connected"


class StitchingPoint(BaseModel):
    """Pydantic model representing the StitchingPoint schema."""

    error: float | None = Field(None, examples=[0.02])
    point_1: Coord2d | None = None
    point_2: Coord2d | None = None


class StitchingPoints(BaseModel):
    """Pydantic model representing the StitchingPoints schema."""

    coordinate_system_1: CoordinateSystem1 | None = None
    coordinate_system_2: CoordinateSystem2 | None = None
    mac_address_1: str | None = Field(
        None, description="MAC address of first sensor", examples=["00:00:00:00:00:01"]
    )
    mac_address_2: str | None = Field(
        None, description="MAC address of second sensor", examples=["00:00:00:00:00:02"]
    )
    status: Status9 | None = None
    stitching_points: list[StitchingPoint] | None = None


class StoredBlobs(BaseModel):
    """Pydantic model representing the StoredBlobs schema."""

    entries: list[str] = Field(..., examples=[["ui_settings.json", "rotate_scene.json"]])


class SubscribeRequest1(BaseModel):
    """Pydantic model representing the SubscribeRequest1 schema."""

    model_config = ConfigDict(json_schema_extra={"xml": {"name": "SubscribeRequest"}})
    Client_IP_Address: str | None = Field(
        None,
        description="IP of APC Receiver",
        examples=["192.168.1.1"],
        json_schema_extra={"xml": {"name": "Client-IP-Address"}},
    )
    ReplyPath: str = Field(..., description="Path of APC Receiver", examples=["/test"])
    ReplyPort: str = Field(..., description="Port of APC Receiver", examples=["1234"])


class TagPosition(Enum):
    """Pydantic model representing the TagPosition schema."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    BOTH = "BOTH"


class TagSettings(BaseModel):
    """Pydantic model representing the TagSettings schema."""

    tag_position: TagPosition | None = Field(
        None, description="The tag position.", examples=["LEFT"]
    )


class TimeFormats(Enum):
    """Pydantic model representing the TimeFormats schema."""

    UNIX_TIME_MS = "UNIX_TIME_MS"
    UNIX_TIME_S = "UNIX_TIME_S"
    RFC3339 = "RFC3339"


class TimeInstant(RootModel[int]):
    """Pydantic model representing the TimeInstant schema."""

    root: int = Field(
        ...,
        description="JSON representation of an instant of time as milliseconds since epoch in UTC",
        examples=[1579537614000],
        title="Instant of time",
    )


class TimeManualSettings1(BaseModel):
    """Pydantic model representing the TimeManualSettings1 schema."""

    time_utc: AwareDatetime | None = Field(
        None,
        description="UTC time in RFC3339 format. Must specify timezone Z or 00:00",
        examples=["2017-07-21T17:32:28Z"],
    )


class TimeManualSettings2(BaseModel):
    """Pydantic model representing the TimeManualSettings2 schema."""

    time_local: AwareDatetime | None = Field(
        None,
        description="Local time in RFC3339 format. With or without timezone",
        examples=["2017-07-21T17:32:28+02:00 or 2017-07-21T17:32:28"],
    )


class TimeManualSettings(RootModel[TimeManualSettings1 | TimeManualSettings2]):
    """Pydantic model representing the TimeManualSettings schema."""

    root: TimeManualSettings1 | TimeManualSettings2 = Field(
        ..., description="Current time", title="Current time"
    )


class TimeSettings(BaseModel):
    """Pydantic model representing the TimeSettings schema."""

    ntp_enabled: bool = Field(
        ..., description="Indicates whether NTP is enabled or not.", examples=[False]
    )
    ntp_server_enabled: bool | None = Field(
        None, description="Indicates whether sensor acts as an NTP server", examples=[False]
    )
    ntp_servers: list[str] | None = Field(
        None,
        description="List of NTP peers to synchronized time with",
        examples=[["pool.ntp.org", "192.168.1.1"]],
    )
    time_zone: str = Field(
        ..., description="Time zone identification.", examples=["America/New_York"]
    )


class Details4(BaseModel):
    """Pydantic model representing the Details4 schema."""

    ntp_host: str | None = Field(
        None, description="NTP server for synchronizing time", examples=["123.43.53.2"]
    )
    ntp_host_stratum: int | None = Field(None, description="NTP stratum", examples=[2])
    ntp_rms_offset: float | None = Field(None, description="NTP RMS offset", examples=[0.001813])
    ntp_root_delay: float | None = Field(None, description="NTP root delay", examples=[0.010808])
    ntp_root_dispersion: float | None = Field(
        None, description="NTP root dispersion", examples=[32.566299]
    )
    time: str = Field(
        ...,
        description="Current sensor time (format RFC3339)",
        examples=["2021-03-31T09:15:53+0100"],
    )
    tz_offset_sec: int = Field(..., description="Time zone offset in seconds", examples=[-3600])


class Error2(BaseModel):
    """Pydantic model representing the Error2 schema."""

    code: int | None = Field(None, description="Error number, more details in the documentation")
    info: str | None = Field(None, description="Short english description of the error")


class State10(Enum):
    """Pydantic model representing the State10 schema."""

    SELECTED_SOURCE = "SELECTED_SOURCE"
    COMBINED_SOURCE = "COMBINED_SOURCE"
    NOT_COMBINED = "NOT_COMBINED"
    FALSETICKER = "FALSETICKER"
    UNSTABLE = "UNSTABLE"
    UNREACHABLE = "UNREACHABLE"
    UNKNOWN = "UNKNOWN"


class Source1(BaseModel):
    """Pydantic model representing the Source1 schema."""

    ip_addr: IPv4Address = Field(..., description="IP of NTP server", examples=["192.168.1.1"])
    n_failed: int | None = Field(None, description="Number of failed NTP request")
    n_successful: int = Field(..., description="Number of valid NTP request")
    name: (
        constr(
            pattern="^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\\-]{0,61}[a-zA-Z0-9])\\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\\-]{0,61}[A-Za-z0-9])$"
        )
        | None
    ) = Field(None, description="Hostname of the source", examples=["time.cloudflare.com"])
    sec_since_last_success: int | None = Field(
        None, description="Last time in seconds a valid request succeed"
    )
    state: State10 = Field(..., description="Information of the source state")


class State11(Enum):
    """Pydantic model representing the State11 schema."""

    OK = "OK"
    ERROR = "ERROR"


class TimeState(BaseModel):
    """Pydantic model representing the TimeState schema."""

    details: Details4
    error: Error2 | None = None
    last_downtime_sec: int | None = Field(
        None,
        description="Duration in seconds of the last downtime (shutdown -> turn on)",
        examples=[3600],
    )
    sources: list[Source1] = Field(..., description="Details about each NTP Server")
    state: State11 = Field(..., description="State of module")


class TimestampRfc3339(RootModel[AwareDatetime]):
    """Pydantic model representing the TimestampRfc3339 schema."""

    root: AwareDatetime = Field(
        ..., description="time string in RFC3339 format", examples=["2022-06-07T12:15:20+02:00"]
    )


class TimestampUnixMs(RootModel):
    """Pydantic model representing the TimestampUnixMs schema."""

    root: int = Field(..., ge=0, le=9223372036854775807, examples=[1651504350792])


class TimestampUnixS(RootModel):
    """Pydantic model representing the TimestampUnixS schema."""

    root: int = Field(..., ge=0, le=4294967295, examples=[1651504350])


class Timezones(BaseModel):
    """Pydantic model representing the Timezones schema."""

    time_zones: list[str] = Field(..., examples=[["UTC", "America/New_York"]])


class FaceMask2(Enum):
    NO_MASK = "NO_MASK"
    MASK = "MASK"
    NOT_SURE = "NOT_SURE"


class Gender2(Enum):
    FEMALE = "FEMALE"
    MALE = "MALE"
    NOT_SURE = "NOT_SURE"


class Tag2(Enum):
    NO_TAG = "NO_TAG"
    TAG_1 = "TAG_1"
    NOT_SURE = "NOT_SURE"


class Attributes1(BaseModel):
    face_mask: FaceMask2 | None = Field(
        None, description="Classification result of face mask detection", examples=["MASK"]
    )
    gender: Gender2 | None = Field(
        None, description="Classification result of gender estimation", examples=["MALE"]
    )
    members: int | None = Field(
        None,
        description="Number of group members. Only applicable if object type is GROUP.",
        examples=[5],
    )
    members_with_tag: int | None = Field(
        None,
        description="Number of group members wearing a tag. Only applicable if object type is GROUP and tag detection is enabled.",
        examples=[1],
    )
    tag: Tag2 | None = Field(
        None, description="Classification result of tag detection", examples=["NO_TAG"]
    )
    view_direction: Coord2d | None = Field(
        None,
        description="Vector in 2d-plane in parallel to floor, pointing to view direction of persion",
    )


class Type36(Enum):
    PERSON = "PERSON"
    GROUP = "GROUP"
    BICYCLE = "BICYCLE"
    WHEELCHAIR = "WHEELCHAIR"
    PRAM = "PRAM"


class TrackedObject(BaseModel):
    attributes: Attributes1 | None = None
    position: Coord3d | None = Field(None, description="3d point")
    tail: list[Coord3d] | None = Field(
        None, description="Short history of object positions", max_length=3
    )
    track_id: int | None = Field(None, description="Identification of object", examples=[167])
    track_id_str: str | None = Field(
        None, description="Used to workaround issues with JSON 64-bit numbers."
    )
    type: Type36 | None = Field(None, description="Type of object", examples=["PERSON"])


class TrackedObjects(RootModel[list[TrackedObject]]):
    root: list[TrackedObject] = Field(
        ..., description="JSON representation of object positions", title="Tracked objects"
    )


class TrackingArea(BaseModel):
    tracking_area: Polygon | None = None


class TrackingAreaSettings(BaseModel):
    aspect_ratio: float | None = Field(
        None, description="The aspect ratio width/height.", examples=[0.75]
    )
    horizontal_shift: float | None = Field(
        None, description="Relative horizontal shift", examples=[0]
    )
    shift_possible: bool | None = None
    tracking_area: Polygon | None = None
    vertical_shift: float | None = Field(None, description="Relative vertical shift", examples=[0])


class Type37(Enum):
    dwell_time_reached = "dwell_time_reached"
    cumulated_dwell_time_reached = "cumulated_dwell_time_reached"


class TriggerDwellTime(BaseModel):
    time: float | None = None
    type: Literal["cumulated_dwell_time_reached", "dwell_time_reached"]
    zone_id: int | None = None


class Type38(Enum):
    line_cross = "line_cross"
    line_cross_forward = "line_cross_forward"
    line_cross_backward = "line_cross_backward"


class TriggerLine(BaseModel):
    line_id: int | None = None
    type: Literal["line_cross", "line_cross_backward", "line_cross_forward"]


class Type39(Enum):
    reset = "reset"


class TriggerReset(BaseModel):
    counter_id: int | None = None
    type: Literal["reset"]


class Type40(Enum):
    track_created = "track_created"
    track_deleted = "track_deleted"


class TriggerTrack(BaseModel):
    type: Literal["track_created", "track_deleted"]


class Type41(Enum):
    zone_entry = "zone_entry"
    zone_exit = "zone_exit"


class TriggerZone(BaseModel):
    type: Literal["zone_entry", "zone_exit"]
    zone_id: int | None = None


class UiProperties(BaseModel):
    customBranding: str | None = Field(
        "", description="Forces UI use this name instead of Xovis", examples=["Company Name"]
    )
    hideMultisensor: bool | None = Field(False, description="Hide all multisensor functionality")
    hidePip: bool | None = Field(False, description="Hide all pip functionality")
    title: str | None = Field(
        "",
        description="Title of webpage, to be shown in title bar of browser",
        examples=["Xovis PC-Series Sensor"],
    )
    version: int = Field(..., description="Version of this file", examples=["1"])


class Uint(RootModel):
    """Pydantic model representing the Uint schema."""

    root: int = Field(..., ge=0)


class Update(BaseModel):
    date_utc: str = Field(
        ..., description="Date when update was done.", examples=["2020-07-17T11:15:46Z"]
    )
    fail_reason: str | None = Field(None, examples=["Hardware not compatible"])
    failed: bool | None = Field(None, examples=[True])
    version: str = Field(..., examples=["5.1.0"])


class UpdateHistory(BaseModel):
    updates: list[Update] = Field(..., description="list of update installed or failed to install")


class UpdateInfo(BaseModel):
    min_sw_version: str = Field(..., description="minimal version or unset", examples=["5.3.0"])
    version: str = Field(..., examples=["5.5.0"])


class UpdatePackages(BaseModel):
    updates: list[str] = Field(
        ..., description="List of update packages", examples=[["5.0.0", "5.0.7", "5.1.0"]]
    )


class UpdateSchedule(BaseModel):
    time_utc: XovisTime = Field(
        ...,
        description="Date and time (in UTC) to begin with installation of update package.",
        examples=["2020-07-17T11:15:46Z"],
    )
    version: str = Field(
        ..., description="Version of update package to install", examples=["5.0.1"]
    )


class LastUpdate(BaseModel):
    error_message: str | None = Field(None, examples=["Hardware not compatible"])
    successful: bool = Field(..., examples=[False])
    time: str = Field(..., examples=["2021-03-31T09:15:53+01:00"])
    version: str = Field(..., examples=["5.2.0-pcf"])


class RunningUpdate(BaseModel):
    runtime_s: int = Field(..., examples=[85])
    time: str = Field(..., examples=["2021-03-31T09:15:53+01:00"])
    version: str = Field(..., examples=["5.2.0"])


class State12(Enum):
    OK = "OK"
    WARN = "WARN"
    INSTALLING = "INSTALLING"
    REBOOTING = "REBOOTING"


class UpdateState(BaseModel):
    last_update: LastUpdate | None = None
    running_update: RunningUpdate | None = None
    state: State12 = Field(..., examples=["INSTALLING"])
    version: str = Field(..., examples=["5.1.0"])


class UpdateVersion(BaseModel):
    version: str = Field(..., description="update package version", examples=["5.0.0-43df7c1"])


class AvailableUpdate(BaseModel):
    size_bytes: int | None = Field(None, examples=[12415212])
    version: str | None = Field(None, examples=["5.0.0"])


class UpdatesAvailable(BaseModel):
    available_updates: list[AvailableUpdate] | None = Field(
        None, description="List of update packages to download"
    )
    last_refresh_time: str = Field(
        ...,
        description="Last time the updates server was successfully reached",
        examples=["2020-07-17T11:15:46Z"],
    )
    refreshing: bool = Field(
        ..., description="True when retrying values from updates server, false otherwise"
    )


class UserActivation(BaseModel):
    active: bool = Field(..., description="Whether user is activated or deactivated")


class UserCredentials(BaseModel):
    password: str = Field(..., description="User's new password", examples=["asdf"])


class UserDetail(BaseModel):
    active: bool = Field(..., description="Indicate whether user is active or not", examples=[True])
    factory_default: bool = Field(
        ..., description="Indicate whether user is factory default or not"
    )
    id: str = Field(..., description="User identifier", examples=["admin"])
    privileges: list[str] = Field(
        ..., examples=[["netcfg_read", "netcfg_write", "other_users_read", "own_user_read"]]
    )
    roles: list[str]


class UserDetails(BaseModel):
    users: list[UserDetail]


class UserSession(BaseModel):
    max_unused_for: int = Field(
        ...,
        description="Maximum idle period after which this session is deleted in seconds",
        examples=[3600],
    )
    token: str = Field(
        ...,
        description="Session token to be used as bearer token for requests",
        examples=["ZHNmZ2tsaHNhZGhqa2dmaGphZGtsZ2hqa"],
    )
    valid_for: int = Field(
        ..., description="Maximum number of seconds this session is valid", examples=[86400]
    )


class UserSmk(BaseModel):
    smk: str = Field(..., description="SMK", examples=["abcdef"])


class Type42(Enum):
    TABOO = "TABOO"
    VISIBLE_FLOOR = "VISIBLE_FLOOR"
    ILLUMINATION = "ILLUMINATION"


class ViewMask(BaseModel):
    coordinate_system: CoordinateSystem | None = None
    id: int | None = Field(None, description="Identification of the mask", examples=[21])
    polygon: Polygon | None = None
    type: Type42 | None = Field(None, description="Type of mask")


class ViewMasksLimits(BaseModel):
    max_elements: int | None = None
    max_total_vertices: int | None = None


class WifiSettings(BaseModel):
    allowlist_enabled: bool | None = Field(
        None, description="Allowlist enabled for WiFi monitoring.", examples=[True]
    )
    channel_dwell_ms: int | None = Field(
        None,
        description="Time in milliseconds during which one channel is monitored, before switching to the next one. Allowed values between 50 and 3000.",
    )
    channels: list[int] | None = Field(
        None,
        description="List of channels which will be monitored. Allowed values between 1 and 13",
        examples=[[1, 6, 11]],
    )
    denylist_enabled: bool | None = Field(
        None, description="Denylist enabled for WiFi monitoring.", examples=[False]
    )
    enabled: bool | None = Field(None, description="WiFi monitoring enabled.", examples=[True])
    filter_expr: str | None = Field(
        "not subtype beacon",
        description="[PCAP expression](https://www.tcpdump.org/manpages/pcap-filter.7.html) to specifically filter and monitor wireless traffic.",
        examples=["subtype probe-req"],
    )


class WlanAp(BaseModel):
    bssid: str | None = Field(None, description="BSSID", examples=["00:00:00:00:00:00"])
    channel: int | None = Field(None, description="Channel", examples=[36])
    connected: bool | None = Field(
        None, description="Indicates whether this Access Point is connected.", examples=[False]
    )
    frequency: int | None = Field(None, description="Frequency", examples=[5240])
    last_seen: str | None = Field(None, description="Time when access point was seen")
    max_signal: int | None = Field(
        None, description="Maximum signal strength observed so far in dBm", examples=[-45]
    )
    signal: int | None = Field(None, description="Signal strength in dBm", examples=[-47])
    validated: bool | None = Field(
        None, description="Indicates whether testing this network was successful", examples=[True]
    )


class Auth(Enum):
    WPA2_PSK = "WPA2-PSK"
    OPEN = "OPEN"


class WlanNetwork(BaseModel):
    auth: Auth | None = Field(
        None, description="Type of authentication. Either WPA2-PSK or OPEN", examples=["WPA2-PSK"]
    )
    bssid: str | None = Field(
        None, description="Require specific BSSID", examples=["00:00:00:00:00:00"]
    )
    enabled: bool = Field(..., description="Network is enabled.", examples=[True])
    hidden: bool | None = Field(None, description="Network is hidden.", examples=[True])
    id: int | None = Field(None, description="Configuration id", examples=[0])
    priority: int | None = Field(None, description="Network priority", examples=[0])
    psk: str | None = Field(
        None, description="Password (Pre-Shared Key) WPA2-PSK", examples=["password"]
    )
    ssid: str = Field(..., description="Network identification.", examples=["My Network"])


class WlanNetworks(BaseModel):
    networks: list[WlanNetwork] | None = Field(None, description="Collection of networks")


class BandPreference(Enum):
    auto = "auto"
    field_2_4 = "2.4"
    field_5 = "5"


class WlanSettings(BaseModel):
    band_preference: BandPreference | None = Field(
        None,
        description="Selects preferred ISM band. Either 2.4 or 5 GHz or both (automatically)",
        examples=["auto"],
    )
    enabled: bool | None = Field(
        None, description="Enable or disable wireless networking.", examples=[True]
    )
    periodic_scan_interval: int | None = Field(
        None, description="Interval of period scanning. Use 0 for disabling.", examples=[0]
    )
    wlan_preference: bool | None = Field(
        None,
        description="Sets preference of WLAN over Ethernet for outgoing traffic",
        examples=[False],
    )


class Options3(BaseModel):
    zone_1_id: int | None = None
    zone_2_id: int | None = None
    zone_of_interest_id: int | None = None


class Type43(Enum):
    XLT_WRONG_WAY_DETECTION = "XLT_WRONG_WAY_DETECTION"


class WrongWayCountLogicTemplate(BaseModel):
    options: Options3 | None = None
    type: Literal["XLT_WRONG_WAY_DETECTION"]


class MinTlsVersion(IntEnum):
    integer_0 = 0
    integer_1 = 1
    integer_2 = 2
    integer_3 = 3


class WwwConfig(BaseModel):
    custom_http_headers: dict[str, str] | None = Field(
        None,
        description="Key-value dictionary for custom HTTP headers to be delivered on response (only for statically served files, not applicable for reverse proxy back-end services)",
        examples=[
            {"Access-Control-Allow-Origin": "https://foo.bar", "SomeHTTPHeader": "SomeValue"}
        ],
    )
    dh_size: int | None = Field(
        2048,
        description="Diffie-Hellman key size used to exchange session keys while establishing TLS connection.",
        examples=[2048],
    )
    http_enabled: bool = Field(
        ..., description="Indicating whether plain HTTP connection are allowed.", examples=[False]
    )
    http_port: int = Field(
        ..., description="TCP port listening plain HTTP connections.", examples=[80]
    )
    https_port: int = Field(
        ..., description="TCP port listening for secured HTTPS connections.", examples=[443]
    )
    min_tls_version: MinTlsVersion | None = Field(
        None,
        deprecated=True,
        description="Minimum TLS version web-server accepts for HTTPS connections. Possible values are [0, 1, 2, 3] 0: SSL v3.0 1: TLS v1.0 2: TLS v1.1 3: TLS v1.2 This parameter is deprecated and will be removed. TLS 1.2 and 1.3 will be supported.",
        examples=[1],
    )


class WwwRoute(BaseModel):
    method: str = Field(..., description="HTTP method", examples=["GET"])
    uri: str = Field(..., description="URI", examples=["/api/v5/www/config"])


class WwwRoutes(BaseModel):
    routes: list[WwwRoute]


class X509Certificate(BaseModel):
    fingerprint_sha1: Base64Str = Field(..., examples=["4abdeeec950d359c89aec752a12c5b29f6d6aa0c"])
    issuer: str = Field(..., examples=["OU = Domain Control Validated, CN = example.com"])
    san: list[str] | None = Field(None, examples=[["xovis.com"]])
    serial_number: str = Field(..., examples=["04:7a:f7:95:47:c0:7d:0f:ef:80:a5:b2:1f:51:e3:63"])
    subject: str = Field(
        ...,
        examples=[
            "C = CH, ST = Bern, L = Zollikofen, O = Example CA Limited, CN = RSA Domain Validation Secure Server CA"
        ],
    )
    valid_from: str = Field(..., examples=["2000-09-30 21:12:19"])
    valid_to: str = Field(..., examples=["2021-09-30 14:01:15"])


class X509CertificateChain(BaseModel):
    chain: list[X509Certificate] | None = None


class X509Certificates(BaseModel):
    x509_certificates_custom: list[X509Certificate]
    x509_certificates_default: list[X509Certificate]


class X509TruststoreConfig(BaseModel):
    defaults_enabled: bool = Field(
        ..., description="Indicates whether default public certificates are used", examples=[True]
    )


class XovisRemoteSupportCtrl(BaseModel):
    enabled: bool
    use_proxy: bool | None = Field(None, description="Use the proxy if configured")


class XovisRemoteSupportState(XovisRemoteSupportCtrl):
    connected: bool = Field(
        ..., description="Is the sensor currently connected to Xovis remote support"
    )


class Options4(BaseZoneCountTemplateOptions):
    count_bicycles: bool | None = None
    count_prams: bool | None = None
    count_wheelchairs: bool | None = None
    door_id: int | None = None
    max_child_height: float | None = None


class Type44(Enum):
    XLT_ZONE_DOOR_COUNT = "XLT_ZONE_DOOR_COUNT"


class ZoneDoorCountLogicTemplate(BaseModel):
    options: Options4 | None = None
    type: Literal["XLT_ZONE_DOOR_COUNT"]


class Options5(BaseZoneCountTemplateOptions):
    max_person_height: float | None = None
    min_person_height: float | None = None


class Type45(Enum):
    XLT_ZONE_IN_OUT_COUNT = "XLT_ZONE_IN_OUT_COUNT"


class ZoneInOutCountLogicTemplate(BaseModel):
    options: Options5 | None = None
    type: Literal["XLT_ZONE_IN_OUT_COUNT"]


class Options6(BaseZoneCountTemplateOptions):
    max_dwell_time: float | None = None
    max_person_height: float | None = None
    min_dwell_time: float | None = None
    min_person_height: float | None = None


class Type46(Enum):
    XLT_ZONE_OCCUPANCY_COUNT = "XLT_ZONE_OCCUPANCY_COUNT"


class ZoneOccupancyCountLogicTemplate(BaseModel):
    options: Options6 | None = None
    type: Literal["XLT_ZONE_OCCUPANCY_COUNT"]


class Count(BaseModel):
    CountQuality_1: CountQuality | None = Field(None, alias="CountQuality", examples=["Regular"])
    In: IBISIPInt | None = None
    ObjectClass_1: ObjectClass | None = Field(None, alias="ObjectClass", examples=["ADULT"])
    Out: IBISIPInt | None = None


class OpenState(BaseModel):
    ErrorCode: IBISIPErrorCode | None = None
    Value_1: Value | None = Field(None, alias="Value", examples=["SingleDoorOpen"])


class State(BaseModel):
    OpenState_1: OpenState | None = Field(None, alias="OpenState")


class OpenState1(BaseModel):
    ErrorCode: IBISIPErrorCode | None = None
    Value: Value1 | None = Field(None, examples=["SingleDoorOpen"])


class IBISIPNMTOKEN(BaseModel):
    ErrorCode: IBISIPErrorCode | None = None
    Value: str = Field(..., description="xs:nmtoken")


class IBISIPAnyURI(BaseModel):
    ErrorCode: IBISIPErrorCode | None = None
    Value: str = Field(..., description="xs:anyURI")


class IBISIPBoolean(BaseModel):
    ErrorCode: IBISIPErrorCode | None = None
    Value: bool = Field(..., description="xs:boolean", examples=[True])


class IBISIPDateTime(BaseModel):
    ErrorCode: IBISIPErrorCode | None = None
    Value: str = Field(..., description="xs:dateTime", examples=["2001-10-26T21:32:52"])


class ServiceSpecification(BaseModel):
    IBIS_IP_Version: IBISIPNMTOKEN | None = Field(None, alias="IBIS-IP-Version")
    ServiceName_1: ServiceName | None = Field(
        None, alias="ServiceName", examples=["PassengerCountingService"]
    )


class SubscribeResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"xml": {"name": "SubscribeResponse"}})
    Active: IBISIPBoolean | None = None
    OperationErrorMessage: IBISIPString | None = None


class UnsubscribeResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"xml": {"name": "SubscribeResponse"}})
    Active: IBISIPBoolean | None = None
    OperationErrorMessage: IBISIPString | None = None


class AffineTransformation2d(BaseModel):
    linear: Matrix2d
    translation: Coord2d


class AffineTransformation3d(BaseModel):
    linear: Matrix3d | None = None
    translation: Coord3d | None = None


class Format(BaseModel):
    pretty: bool | None = None
    time: TimeFormats | None = None
    type: Formats | None = None
    version: constr(max_length=128) | None = None


class Data(BaseModel):
    format: Format
    include_empty: bool | None = None
    meta_data_config: MetaDataConfig | None = None
    meta_data_package_full: bool | None = None
    meta_data_sensor_full: bool | None = None
    normalization: Normalization | None = None
    package_size: int | None = None
    resolution: Resolutions
    resources: list[Resource] | None = None


class Filters(BaseModel):
    filter_events_by_objects: bool | None = None
    included_count_events: CountEventTypes
    included_info_events: InfoEventTypes
    included_objects: ObjectTypes
    included_scene_events: SceneEventTypes


class Filters1(BaseModel):
    included_logics: IncludedLogics


class Retry(BaseModel):
    delay_increase_const: confloat(ge=1.0, le=3600.0) | None = None
    delay_increase_factor: confloat(ge=1.0, le=10.0) | None = None
    delay_interval_max: confloat(ge=0.0, le=86400.0) | None = None
    delay_interval_min: confloat(ge=0.0, le=86400.0) | None = None
    delay_start_max: confloat(ge=0.0, le=86400.0) | None = None
    delay_start_min: confloat(ge=0.0, le=86400.0) | None = None
    max_number: conint(ge=0) | None = None
    mode: SchedulerRetryModes
    reset_on_next_push_schedule: bool | None = None


class Scheduler(BaseModel):
    cron: str | None = None
    interval: SchedulerIntervals | None = None
    retry: Retry | None = None
    type: SchedulerTypes


class Config(BaseModel):
    data: Data | None = None
    filters: Filters | Filters1 | None = None
    scheduler: Scheduler


class AgentConfig(BaseModel):
    config: Config | None = None
    connection: int | None = None
    enabled: bool | None = None
    id: int | None = None
    name: constr(max_length=128) | None = None
    type: AgentTypes | None = None


class AgentConfigCollection(BaseModel):
    agents: list[AgentConfig] | None = None


class AgentTrigger(BaseModel):
    file_name_prefix: constr(max_length=64) | None = None
    package_id_start: conint(ge=0) | None = None
    time_from: XovisTime | None = None
    time_to: XovisTime | None = None
    type: AgentTriggerTypes


class AgentTriggerStatus(BaseModel):
    details: str | None = None
    status: Status | None = None
    trigger_config: AgentTrigger | None = None
    trigger_time: XovisTime | None = None


class AgentTxStatus(BaseModel):
    download: AgentTxStatusDataStats | None = None
    duration_ms: int | None = Field(
        None,
        description="duration of the whole data transfer incl. connection, name resolving etc.",
    )
    port: conint(ge=1, le=65535) | None = None
    protocol: ConnectionProtocols | None = None
    reason: Reason | None = None
    server: AnyUrl | None = None
    time: XovisTime | None = None
    upload: AgentTxStatusDataStats | None = None


class AllSceneMasks(BaseModel):
    scene_masks: list[SceneMask] | None = None
    total_perimeter: float | None = None
    total_vertices: int | None = None


class AllViewMasks(BaseModel):
    total_vertices: int | None = None
    view_masks: list[ViewMask] | None = None


class BlockedSpace(BaseModel):
    coordinate_system: CoordinateSystem | None = None
    id: int | None = Field(None, description="Identification of the space", examples=[21])
    invalid_pixel_mode: InvalidPixelMode | None = Field(
        "BACKGROUND", description="mode defining how to use the invalid stereo pixels"
    )
    lower_threshold: float | None = Field(None, description="threshold for events", examples=[0.3])
    name: str | None = Field(None, examples=["Space 1"])
    polygon: Polygon | None = None
    upper_threshold: float | None = Field(None, description="threshold for events", examples=[0.5])


class Changesets(BaseModel):
    checksum: str = Field(..., description="Checksum", examples=["0422d752"])
    details: list[ConfigEndpoint] | None = None
    last_change: str = Field(
        ..., description="Time of last change", examples=["2021-12-08T09:22:12Z"]
    )


class ConnectionConfig(
    RootModel[
        ConnectionConfigHttp
        | ConnectionConfigFtp
        | ConnectionConfigSftp
        | ConnectionConfigMqtt
        | ConnectionConfigTcp
        | ConnectionConfigUdp
    ]
):
    root: (
        ConnectionConfigHttp
        | ConnectionConfigFtp
        | ConnectionConfigSftp
        | ConnectionConfigMqtt
        | ConnectionConfigTcp
        | ConnectionConfigUdp
    )


class ConnectionConfigCollection(BaseModel):
    connections: list[ConnectionConfig] | None = None


class CountRecordStatus(BaseModel):
    data_size: Uint
    duration_s: Uint
    id: int
    time_begin: XovisTime


class CountStatus(BaseModel):
    id: int
    last_stored_total_value: Uint
    logic_id: int
    name: str
    reset_offset: Uint | None = None
    reset_time: XovisTime | None = None


class DiscoverScanResult(BaseModel):
    sensors: list[DiscoverSensor]


class ExistingBlockedSpace(BlockedSpace):
    percentage: float | None = Field(
        None, description="percentage of blocked space", examples=[0.13]
    )
    type: Type5 | None = None


class FormattedTimestamp(RootModel[TimestampUnixMs | TimestampUnixS | TimestampRfc3339]):
    root: TimestampUnixMs | TimestampUnixS | TimestampRfc3339


class Measurement(BaseModel):
    begin: FormattedTimestamp | None = None
    counts: list[Count1] | None = None
    end: FormattedTimestamp | None = None
    records: int | None = Field(
        None, description="Number of count records found within the measurement bin's time frame"
    )


class Logic(BaseModel):
    geometries: list[int] | None = None
    id: int | None = None
    last_modified: FormattedTimestamp | None = None
    name: str | None = Field(None, description="name of the logic")
    optional_data: str | None = Field(None, description="optional string associated with the logic")


class HistoryLogicsConfig(BaseModel):
    counts: list[Count2] | None = None
    geometries: list[Geometry] | None = None
    logics: list[Logic] | None = None


class Capacity(BaseModel):
    count_records: Uint
    fill_level_percent: float
    memory: Uint
    time: str | None = None
    time_s: Uint


class IbisipConfigDoorApcPathOptional(BaseModel):
    adult: IbisipApcObjectDetails | None = Field(
        None, description="Details for adult objects counting"
    )
    apc_door_id: int = Field(..., description="Identification used for door in APC message")
    apc_path: str | None = Field(
        "/api/v5/ibisip/DoorID/{apc_door_id}",
        description="Path for APC operations as used in mdns txt record path",
    )
    bicycle: IbisipApcObjectDetails | None = Field(
        None, description="Details for bicycle objects counting"
    )
    child: IbisipApcObjectDetails | None = Field(
        None, description="Details for child objects counting"
    )
    id: int | None = Field(None, description="Identification of door")
    pram: IbisipApcObjectDetails | None = Field(
        None, description="Details for pram objects counting"
    )
    sensor_door_config: IbisipSensorDoorConfig | None = Field(
        None, description="Details for the sensor door configuration"
    )
    wheelchair: IbisipApcObjectDetails | None = Field(
        None, description="Details for wheelchair objects counting"
    )


class IbisipConfigDoorApcPathRequired(BaseModel):
    adult: IbisipApcObjectDetails | None = Field(
        None, description="Details for adult objects counting"
    )
    apc_door_id: int = Field(..., description="Identification used for door in APC message")
    apc_path: str = Field(
        ..., description="Path for APC operations as used in mdns txt record path"
    )
    bicycle: IbisipApcObjectDetails | None = Field(
        None, description="Details for bicycle objects counting"
    )
    child: IbisipApcObjectDetails | None = Field(
        None, description="Details for child objects counting"
    )
    id: int | None = Field(None, description="Identification of door")
    pram: IbisipApcObjectDetails | None = Field(
        None, description="Details for pram objects counting"
    )
    sensor_door_config: IbisipSensorDoorConfig | None = Field(
        None, description="Details for the sensor door configuration"
    )
    wheelchair: IbisipApcObjectDetails | None = Field(
        None, description="Details for wheelchair objects counting"
    )


class IbisipConfigDoorCollection(BaseModel):
    doors: list[IbisipConfigDoorApcPathRequired] | None = None


class IbisipServicesState(BaseModel):
    consumers: list[Consumer] = Field(..., description="Devices consuming our services published")
    services_published: list[ServiceModel] = Field(..., description="Sensor services published")


class ImageMetadata(BaseModel):
    height_px: int | None = Field(None, description="Image height in pixels", examples=[421])
    pixel_to_ref: AffineTransformation2d | None = None
    ref_coordinate_system: RefCoordinateSystem | None = Field(
        None, description="Reference coordinate system of the image"
    )
    ref_to_pixel: AffineTransformation2d | None = None
    width_px: int | None = Field(None, description="Image width in pixels", examples=[234])


class IndexedMultisensor(Multisensor):
    id: int | None = Field(
        None, description="Identification of the multisensor instance", examples=[21]
    )


class IndexedRecordingSchedule(BaseModel):
    id: float | None = Field(None, examples=[5])
    singlesensor_recordings: list[SinglesensorRecording] | None = None
    time_end: float | None = Field(
        None,
        description="End of time interval (milliseconds since epoch in UTC).",
        examples=[1758894300000],
    )
    time_start: float | None = Field(
        None,
        description="Begin of time interval (milliseconds since epoch in UTC).",
        examples=[1758894000000],
    )


class IndexedRemoteConnection(RemoteConnection):
    id: int = Field(..., description="Identifier of remote connection configuration", examples=[1])


class IndexedRemoteConnectionState(RemoteConnectionState):
    id: int = Field(..., description="Identifier of remote connection", examples=[1])


class ItxptConfigDoorApcPathOptional(BaseModel):
    adult: ItxptApcObjectDetails | None = Field(
        None, description="Details for adult objects counting"
    )
    apc_door_id: int = Field(..., description="Identification used for door in APC message")
    apc_path: str | None = Field(
        "/api/v5/itxpt/services/apc/passengerdoorcount",
        description="Path for APC operations (reflected in mdns record)",
    )
    bicycle: ItxptApcObjectDetails | None = Field(
        None, description="Details for bicycle objects counting"
    )
    child: ItxptApcObjectDetails | None = Field(
        None, description="Details for child objects counting"
    )
    id: int | None = Field(None, description="Identification of door")
    pram: ItxptApcObjectDetails | None = Field(
        None, description="Details for pram objects counting"
    )
    sensor_door_config: ItxptSensorDoorConfig | None = Field(
        None, description="Details for the sensor door configuration"
    )
    wheelchair: ItxptApcObjectDetails | None = Field(
        None, description="Details for wheelchair objects counting"
    )


class ItxptConfigDoorApcPathRequired(BaseModel):
    adult: ItxptApcObjectDetails | None = Field(
        None, description="Details for adult objects counting"
    )
    apc_door_id: int = Field(..., description="Identification used for door in APC message")
    apc_path: str = Field(..., description="Path for APC operations (reflected in mdns record)")
    bicycle: ItxptApcObjectDetails | None = Field(
        None, description="Details for bicycle objects counting"
    )
    child: ItxptApcObjectDetails | None = Field(
        None, description="Details for child objects counting"
    )
    id: int | None = Field(None, description="Identification of door")
    pram: ItxptApcObjectDetails | None = Field(
        None, description="Details for pram objects counting"
    )
    sensor_door_config: ItxptSensorDoorConfig | None = Field(
        None, description="Details for the sensor door configuration"
    )
    wheelchair: ItxptApcObjectDetails | None = Field(
        None, description="Details for wheelchair objects counting"
    )


class ItxptConfigDoorCollection(BaseModel):
    doors: list[ItxptConfigDoorApcPathRequired] | None = None


class ItxptServicesState(BaseModel):
    apc_devices: list[ServiceModel] = Field(
        ..., description="Devices on the network also having apc service"
    )
    consumers: list[Consumer] = Field(..., description="Devices consuming our services published")
    services_published: list[ServiceModel] = Field(..., description="Sensor services published")
    services_subscribed: list[ServiceModel] = Field(..., description="Sensor subscribed services")


class Layer(BaseModel):
    id: int | None = Field(None, description="Identification of layer.")
    name: str | None = Field(None, description="Name of the layer.")
    zone_of_interest: Polygon | None = None


class Layers(BaseModel):
    layers: list[Layer] | None = None
    total_perimeter: float | None = None
    total_vertices: int | None = None


class LegacyConfigGet(BaseModel):
    available: bool | None = None
    enabled: bool | None = None
    sensor_geometry: SensorGeometry | None = None


class LinearTransformation2d(BaseModel):
    pass


class LinearTransformation3d(BaseModel):
    pass


class LiveCountCollection(BaseModel):
    counts: list[LiveCountItem] | None = None
    time: AwareDatetime | None = Field(
        None, description="RFC3339 timestamp including timezone offset of contained measurements"
    )


class LiveLogicsCollection(BaseModel):
    logics: list[LiveLogicsItem] | None = None
    time: AwareDatetime | None = Field(
        None, description="RFC3339 timestamp including timezone offset of contained measurements"
    )


class LogicStatus(BaseModel):
    count_records: Uint
    geometry_id: int
    geometry_name: str
    geometry_type: str
    id: Uint
    info: str
    name: str
    retention_time: str | None = None
    retention_time_s: Uint
    time_begin: AwareDatetime


class LogicTemplate(BaseModel):
    id: int | None = Field(None, description="Identification of logic.")
    layer_id: int | None = Field(None, description="Identification of layer.")
    name: str | None = None
    template: (
        CustomLogicTemplate
        | PersonLineCountLogicTemplate
        | LegacyPersonLineCountLogicTemplate
        | GroupLineCountLogicTemplate
        | ObjectLineCountLogicTemplate
        | ZoneOccupancyCountLogicTemplate
        | ZoneInOutCountLogicTemplate
        | LegacyZoneInOutCountLogicTemplate
        | WrongWayCountLogicTemplate
        | ZoneDoorCountLogicTemplate
        | None
    ) = Field(None, discriminator="type")


class LogicTemplateCollection(BaseModel):
    logics: list[LogicTemplate] | None = None


class MapInfo(BaseModel):
    begin: TimeInstant | None = None
    end: TimeInstant | None = None
    max: float | None = None
    min: float | None = None


class Filter(
    RootModel[
        FilterOperator
        | Operand
        | OperandLine
        | OperandLineCrossings
        | OperandLineCrossDirection
        | OperandZone
        | OperandZoneVisits
        | OperandZoneDwellTime
        | OperandPersonHeight
        | OperandInteractionPersonHeight
        | OperandHasGender
        | OperandHasTag
        | OperandHasFaceMask
        | OperandHasInteractionGender
        | OperandHasInteractionTag
        | OperandHasInteractionFaceMask
    ]
):
    root: (
        FilterOperator
        | Operand
        | OperandLine
        | OperandLineCrossings
        | OperandLineCrossDirection
        | OperandZone
        | OperandZoneVisits
        | OperandZoneDwellTime
        | OperandPersonHeight
        | OperandInteractionPersonHeight
        | OperandHasGender
        | OperandHasTag
        | OperandHasFaceMask
        | OperandHasInteractionGender
        | OperandHasInteractionTag
        | OperandHasInteractionFaceMask
    ) = Field(..., discriminator="type")


class Modifier(BaseModel):
    count_events: list[CountEvent] | None = None
    filter: list[Filter] | None = None
    id: int | None = Field(None, description="Identification of modifier.")
    logic_id: int | None = Field(None, description="Identification of logic.")
    name: str | None = None
    object_type: ObjectType1 | None = None
    trigger: TriggerTrack | TriggerLine | TriggerZone | TriggerDwellTime | TriggerReset | None = (
        Field(None, discriminator="type")
    )
    zone_of_interest: ZoneOfInterest | None = None


class ModifierCollection(BaseModel):
    modifiers: list[Modifier] | None = None


class MultisensorStatus(BaseModel):
    alignment: bool | None = Field(None, description="Multisensor alignment set")
    alignment_id: str | None = Field(
        None, description="alignment id", examples=["e33f0a1a9f6fc2f5ffa1726537357b0d546ffeea"]
    )
    custom_id: int | None = Field(
        None, description="A custom id of the multisensor alignment", examples=[57]
    )
    enabled: bool | None = Field(None, description="State of module")
    frames_processed: int | None = Field(None, examples=[57])
    group: str | None = Field(None, description="Multisensor group", examples=["My Group"])
    id: str | None = Field(
        None, description="DEPRECATED | old alignment id", examples=["00:00:00:00:00:00"]
    )
    licenses: list[License1] | None = None
    mac_address: str | None = Field(
        None, description="the serial number of the device", examples=["00:00:00:00:00:00"]
    )
    migrated: bool | None = Field(
        None, description="Multisensor alignment migrated from 3.x/4.x version"
    )
    name: str | None = Field(None, description="Multisensor name", examples=["My Multisenosor"])
    sensors: list[SensorInformation] | None = None


class Multisensors(BaseModel):
    multisensors: list[IndexedMultisensor] | None = None


class MultisensorsStatus(BaseModel):
    multisensors_status: list[MultisensorStatus] | None = None


class Projections(BaseModel):
    sensor_to_ref: AffineTransformation3d | None = None


class Recording(IndexedRecordingSchedule):
    sequences: list[Sequence] | None = None
    size: float | None = None
    status: Status4 | None = None


class Recordings(BaseModel):
    recordings: list[Recording] | None = None


class RemoteConnectionStates(BaseModel):
    remote_states: list[IndexedRemoteConnectionState]


class RemoteConnections(BaseModel):
    remotes: list[IndexedRemoteConnection]


class Request(BaseModel):
    body: (
        Logic1
        | Counter
        | Modifier
        | LogicCollection
        | CounterCollection
        | ModifierCollection
        | None
    ) = None
    method: Method1 | None = Field(None, examples=["POST"])
    target: str | None = Field(None, examples=["logics"])


class ScanResult(WlanNetwork):
    access_points: list[WlanAp] | None = Field(None, description="Collection of access types")
    connected: bool | None = Field(
        None, description="Indicates whether network is connected", examples=[False]
    )


class ScanResults(BaseModel):
    networks: list[ScanResult] | None = Field(None, description="Collection of networks")


class SceneGeometries(BaseModel):
    geometries: list[SceneGeometry] | None = None
    total_perimeter: float | None = None
    total_vertices: int | None = None


class SensorAlignment(BaseModel):
    group: str | None = Field(None, examples=["My group"])
    ip_address: str | None = Field(None, examples=["0.0.0.0"])  # nosec B104
    mac_address: str | None = Field(None, examples=["00:00:00:00:00:00"])
    multisensor_to_singlesensor: AffineTransformation3d | None = None
    name: str | None = Field(None, examples=["My Sensor 1"])
    sensor_geometry: SensorGeometry | None = None
    singlesensor_to_multisensor: AffineTransformation3d | None = None
    tracking_area: Polygon | None = None


class StartStop(BaseModel):
    begin: TimeInstant | None = None
    end: TimeInstant | None = None
    start_points: list[Coord3d] | None = None
    stop_points: list[Coord3d] | None = None


class Link1(BaseModel):
    connected: bool | None = Field(
        None, description="Indiactes whether we are connected or not", examples=[True]
    )
    last_connect: str | None = Field(None, description="Time of last connection")
    last_disconnect: str | None = Field(None, description="Time of last disconnection")
    mac: str | None = Field(None, description="MAC address of wlan interface")
    network: ScanResult | None = None


class Details3(BaseModel):
    enabled: bool | None = Field(None, description="Indiactes whether WLAN networking is enabled.")
    ipv4: NetworkIpv4Settings | None = None
    link: Link1 | None = None


class StateResult(BaseModel):
    details: Details3 | None = None
    state: State9 | None = Field(None, description="", examples=["OK"])


class StaticImageMetaHeaders(BaseModel):
    image_metadata: ImageMetadata | None = None
    mac_address: str | None = Field(None, description="MAC of sensor")
    projections: Projections | None = None


class Transaction(BaseModel):
    requests: list[Request] | None = None


class CountingData(BaseModel):
    Count_1: Count | None = Field(None, alias="Count")
    DoorID: IBISIPNMTOKEN | None = None
    State_1: State | None = Field(None, alias="State")


class AllData1(BaseModel):
    CountingData_1: CountingData | None = Field(None, alias="CountingData")
    Timestamp: IBISIPDateTime | None = None


class AllData(BaseModel):
    AllData: AllData1 | None = None


class DataAcceptedResponseData1(BaseModel):
    DataAccepted: IBISIPBoolean | None = None
    ErrorCode: IBISIPErrorCode | None = None
    ErrorInformation: IBISIPString | None = None
    TimeStamp: IBISIPDateTime | None = None


class DataAcceptedResponseData(BaseModel):
    DataAcceptedResponseData: DataAcceptedResponseData1 | None = None


class DeviceManagementServiceGetDeviceConfigurationResponseData(BaseModel):
    DeviceID: IBISIPInt | None = None
    Timestamp: IBISIPDateTime | None = None


class GetDeviceConfigurationResponseData(BaseModel):
    DeviceManagementService_GetDeviceConfigurationResponseData: (
        DeviceManagementServiceGetDeviceConfigurationResponseData | None
    ) = Field(None, alias="DeviceManagementService.GetDeviceConfigurationResponseData")


class DeviceInformation(BaseModel):
    DeviceClass_1: DeviceClass | None = Field(None, alias="DeviceClass", examples=["APC"])
    DeviceName: IBISIPString | None = None
    Manufacturer: IBISIPString | None = None
    SerialNumber: IBISIPNMTOKEN | None = None
    WebInterfaceAddress: IBISIPAnyURI | None = None


class DeviceManagementServiceGetDeviceInformationResponseData(BaseModel):
    DeviceInformation_1: DeviceInformation | None = Field(None, alias="DeviceInformation")
    Timestamp: IBISIPDateTime | None = None


class GetDeviceInformationResponseData(BaseModel):
    DeviceManagementService_GetDeviceInformationResponseData: (
        DeviceManagementServiceGetDeviceInformationResponseData | None
    ) = Field(None, alias="DeviceManagementService.GetDeviceInformationResponseData")


class DeviceManagementServiceGetDeviceStatusResponseData(BaseModel):
    DeviceState_1: DeviceState | None = Field(None, alias="DeviceState", examples=["running"])
    Timestamp: IBISIPDateTime | None = None


class GetDeviceStatusResponseData(BaseModel):
    DeviceManagementService_GetDeviceStatusResponseData: (
        DeviceManagementServiceGetDeviceStatusResponseData | None
    ) = Field(None, alias="DeviceManagementService.GetDeviceStatusResponseData")


class DoorOpenState(BaseModel):
    DoorID: IBISIPNMTOKEN | None = None
    OpenState: OpenState1 | None = None
    TimeStamp: IBISIPDateTime | None = None


class GetDoorOpenStatesResponseData1(BaseModel):
    DoorOpenStates: list[DoorOpenState] | None = None
    TimeStamp: IBISIPDateTime | None = None


class GetDoorOpenStatesResponseData(BaseModel):
    GetDoorOpenStatesResponseData: GetDoorOpenStatesResponseData1 | None = None


class ServiceInformation(BaseModel):
    Autostart: IBISIPBoolean | None = None
    Service: ServiceSpecification | None = None


class ServiceInformationList(BaseModel):
    ServiceInformation_1: ServiceInformation | None = Field(None, alias="ServiceInformation")


class DeviceManagementServiceGetDeviceInformationResponseData1(BaseModel):
    ServiceInformationList_1: ServiceInformationList | None = Field(
        None, alias="ServiceInformationList"
    )
    Timestamp: IBISIPDateTime | None = None


class GetServiceInformationResponseData(BaseModel):
    DeviceManagementService_GetDeviceInformationResponseData: (
        DeviceManagementServiceGetDeviceInformationResponseData1 | None
    ) = Field(None, alias="DeviceManagementService.GetDeviceInformationResponseData")


class ServiceSpecificationWithState(BaseModel):
    ServiceSpecification_1: ServiceSpecification | None = Field(None, alias="ServiceSpecification")
    ServiceState_1: ServiceState | None = Field(None, alias="ServiceState", examples=["running"])


class ServiceSpecificationWithStateList(BaseModel):
    ServiceSpecificationWithState_1: ServiceSpecificationWithState | None = Field(
        None, alias="ServiceSpecificationWithState"
    )


class DeviceManagementServiceGetServiceStatusResponseData(BaseModel):
    ServiceSpecificationWithStateList_1: ServiceSpecificationWithStateList | None = Field(
        None, alias="ServiceSpecificationWithStateList"
    )
    Timestamp: IBISIPDateTime | None = None


class GetServiceStatusResponseData(BaseModel):
    DeviceManagementService_GetServiceStatusResponseData: (
        DeviceManagementServiceGetServiceStatusResponseData | None
    ) = Field(None, alias="DeviceManagementService.GetServiceStatusResponseData")


class TransmitInfo(BaseModel):
    last_failed: AgentTxStatus | None = None
    last_successful: AgentTxStatus | None = None
    no_of_failed: conint(ge=0) | None = None
    no_of_successful: conint(ge=0) | None = None
    received: str | None = Field(None, description="string representation of received_bytes")
    received_bytes: int | None = Field(
        None, description="received bytes sincelast reboot or reconfiguration of the agent"
    )
    received_total: str | None = Field(
        None, description="string representation of received_total_bytes"
    )
    received_total_bytes: int | None = Field(
        None,
        description="received bytes (e.g. connection headers, etc.) since first config of agent (persisted)",
    )
    sent: str | None = Field(None, description="string representation of sent_bytes")
    sent_bytes: int | None = Field(
        None, description="sent bytes sincelast reboot or reconfiguration of the agent"
    )
    sent_total: str | None = Field(None, description="string representation of sent_total_bytes")
    sent_total_bytes: int | None = Field(
        None, description="sent bytes since first config of agent (persisted)"
    )


class AgentStatus(BaseModel):
    id: conint(ge=1) | None = None
    name: constr(max_length=128) | None = None
    package_info: PackageInfo | None = None
    transmit_info: TransmitInfo | None = None
    type: AgentTypes | None = None


class AgentStatusAll(BaseModel):
    agent_states: list[AgentStatus] | None = None
    last_stored: AwareDatetime | None = None


class AllBlockedSpaces(BaseModel):
    spaces: list[ExistingBlockedSpace] | None = None


class HeatHeightMap(BaseModel):
    data: list[list[float]] | None = None
    info: MapInfo | None = None
    metadata: ImageMetadata | None = None


class HistoryLogics(BaseModel):
    begin: FormattedTimestamp | None = None
    begin_data: FormattedTimestamp | None = None
    config: HistoryLogicsConfig | None = None
    end: FormattedTimestamp | None = None
    end_data: FormattedTimestamp | None = None
    index_begin: int | None = None
    index_end: int | None = None
    measurements: list[Measurement] | None = None
    number_of_bins: int | None = None
    number_of_bins_requested: int | None = None
    resolution_ms: int | None = None


class StoredData(BaseModel):
    counts: list[CountStatus]
    logics: list[LogicStatus]
    newest_count_record: CountRecordStatus
    number_of_count_records: Uint
    oldest_count_record: CountRecordStatus
    retention_time: str | None = None
    retention_time_s: Uint
    time_begin: AwareDatetime
    time_end: AwareDatetime


class Storage(BaseModel):
    capacity: Capacity
    stored_data: StoredData


class HistoryStatus(BaseModel):
    storage: Storage


class LiveImageMetaHeaders(StaticImageMetaHeaders):
    framenumber: int | None = None
    time: TimeInstant | None = None


class LiveViewImageMetaHeaders(LiveImageMetaHeaders):
    events: Events | None = None
    tracked_objects: TrackedObjects | None = None
    tracking_area: Polygon | None = None


class MultisensorAlignment(BaseModel):
    custom_id: int | None = Field(
        None, description="A custom id of the multisensor alignment", examples=[57]
    )
    group: str | None = Field(None, examples=["my group"])
    id: str | None = Field(None, examples=["e33f0a1a9f6fc2f5ffa1726537357b0d546ffeea"])
    name: str | None = Field(None, examples=["my multisensor"])
    reference: str | None = Field(None, examples=["00:00:00:00:00:00"])
    sensor_alignment: list[SensorAlignment] | None = None
    stitching_info: list[StitchingInfo] | None = None


class DataAcceptedResponse(RootModel[DataAcceptedResponseData | OperationErrorMessage]):
    root: DataAcceptedResponseData | OperationErrorMessage
