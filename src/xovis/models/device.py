"""
Xovis SDK - Device Models

Operates within the Control Plane.
Provides strict Pydantic V2 data validation and alias mapping for local edge sensor endpoints
that fall outside the scope of the auto-generated OpenAPI schema.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_serializer,
    model_validator,
)

from xovis.utils.time import _parse_relative_time

XovisTime = Annotated[int, BeforeValidator(_parse_relative_time)]


class Zone(BaseModel):
    """
    Represents a spatial Zone geometry mapped to a local Xovis sensor context.

    Attributes:
        id (int): Unique identifier for the zone.
        name (str): Human-readable topological name of the zone.
        coordinates (List[Tuple[float, float]]): Bounding polygon coordinates.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    name: str
    coordinates: list[tuple[float, float]] = Field(
        alias="polygon",
        default_factory=list,
        description="List of (x, y) coordinates forming the zone polygon.",
    )


class Line(BaseModel):
    """
    Represents a spatial Line geometry used for crossing-based analytics.

    Attributes:
        id (int): Unique identifier for the line.
        name (str): Human-readable topological name of the line.
        coordinates (List[Tuple[float, float]]): The line segments coordinates.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    name: str
    coordinates: list[tuple[float, float]] = Field(
        alias="geometry",
        default_factory=list,
        description="List of (x, y) coordinates forming the line segments.",
    )


class SceneMaskType(Enum):
    """Types of masks applied to the 3D scene."""

    BOARDING = "BOARDING"
    EXCLUSION = "EXCLUSION"
    LEGACY_EXCLUSION = "LEGACY_EXCLUSION"


class SceneMask(BaseModel):
    """
    Represents a Scene Mask (e.g., Exclusion or Boarding) in the 3D environment.

    Attributes:
        id (int): Unique identifier for the mask.
        type (SceneMaskType): The functional type of the mask.
        coordinates (List[Tuple[float, float]]): Bounding polygon coordinates.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    type: SceneMaskType
    coordinates: list[tuple[float, float]] = Field(
        alias="polygon",
        default_factory=list,
        description="List of (x, y) coordinates forming the mask polygon. Max 15 scene masks per sensor context.",
    )

    def model_dump(self, **kwargs):
        """Ensures Enum values are serialized as strings even without by_alias=True."""
        kwargs.setdefault("mode", "json")
        return super().model_dump(**kwargs)


class ViewMaskType(Enum):
    """Types of masks applied to the sensor's 2D view projection."""

    TABOO = "TABOO"
    VISIBLE_FLOOR = "VISIBLE_FLOOR"
    ILLUMINATION = "ILLUMINATION"


class ViewMask(BaseModel):
    """
    Represents a View Mask (e.g., Taboo or Illumination) on the sensor's image plane.

    Attributes:
        id (int): Unique identifier for the mask.
        type (ViewMaskType): The functional type of the mask.
        coordinates (List[Tuple[float, float]]): Bounding polygon coordinates.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    type: ViewMaskType
    coordinates: list[tuple[float, float]] = Field(
        alias="polygon",
        default_factory=list,
        description="List of (x, y) coordinates forming the mask polygon. Max 15 view masks per sensor context.",
    )

    def model_dump(self, **kwargs):
        """Ensures Enum values are serialized as strings even without by_alias=True."""
        kwargs.setdefault("mode", "json")
        return super().model_dump(**kwargs)


class BlockedSpace(BaseModel):
    """
    Represents a Blocked Space zone where the sensor's view is obstructed.

    Attributes:
        id (int): Unique identifier for the blocked space zone.
        name (str): Human-readable name of the blocked space.
        coordinates (List[Tuple[float, float]]): Bounding polygon coordinates.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    name: str = Field(default="Blocked Space")
    coordinates: list[tuple[float, float]] = Field(
        alias="polygon",
        default_factory=list,
        description="List of (x, y) coordinates forming the blocked space polygon.",
    )


XovisGeometry = Union[Zone, Line]


class ObjectType(Enum):
    """
    Standardized object classifications for Xovis sensors.

    Bridges differences between firmware versions where ObjectType vs ObjectType1
    definitions may vary.
    """

    PERSON = "PERSON"
    GROUP = "GROUP"
    BICYCLE = "BICYCLE"
    PRAM = "PRAM"
    WHEELCHAIR = "WHEELCHAIR"
    SHOPPING_CART = "SHOPPING_CART"


class CounterType(Enum):
    """Available types for logic counters."""

    STATE = "state"
    ACCUMULATION = "accumulation"


class CounterQuantity(Enum):
    """Measurement unit for the counter."""

    COUNT = "count"
    TIME = "time"


class CounterName(str, Enum):
    """
    Standardized counter names that trigger specific UI rendering/icons.
    Relying on these strings enables the 'Naming Trick' for high-fidelity representation in the device UI.
    """

    # Directional
    FORWARD = "fw"
    BACKWARD = "bw"
    # Gender (Triggers CSS Icon Overrides)
    FORWARD_MALE = "fw-male"
    BACKWARD_MALE = "bw-male"
    FORWARD_FEMALE = "fw-female"
    BACKWARD_FEMALE = "bw-female"
    # Object Specific
    FORWARD_BICYCLE = "fw-bicycle"
    BACKWARD_BICYCLE = "bw-bicycle"
    FORWARD_WHEELCHAIR = "fw-wheelchair"
    BACKWARD_WHEELCHAIR = "bw-wheelchair"
    FORWARD_PRAM = "fw-pram"
    BACKWARD_PRAM = "bw-pram"
    # Mask Detection
    FORWARD_MASK = "fw-mask"
    FORWARD_NO_MASK = "fw-no_mask"
    # Occupancy / Balance
    BALANCE = "balance"
    VISITS = "visits"
    DWELL_TIME = "dwell_time"
    IN = "in"
    OUT = "out"
    # Queue Logic
    QUEUE_LENGTH = "queue-length"
    OUTFLOW = "outflow"
    QUEUEING_TIME = "queueing-time"


class HistogramType(str, Enum):
    """Available histogram types for logic counters."""

    PERSON_AGE = "PERSON_AGE"


class Counter(BaseModel):
    """
    Represents a logic counter in a Custom Logic.

    Bridges the simplified counter definition with the hardware's internal ID/Name/Type slots.

    Age Histograms:
        Typically an ACCUMULATION counter with:
        - histogram: HistogramType.PERSON_AGE
        - bins: [20.0, 40.0, 60.0] (example boundaries)

    Hardware Limit: Sensors typically handle ~60-80 Counters per layer.
    UI Tip: Use CounterName values to trigger specific dashboard icons (Male, Female, etc.).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int | None = Field(None, description="System-assigned or CLIENT-forced unique identifier.")
    name: CounterName | str = Field(..., description="Name of the counter. Use CounterName for UI icons.")
    type: CounterType = Field(default=CounterType.ACCUMULATION, description="Behavior: state (inc/dec) or accumulation.")
    quantity: CounterQuantity = Field(default=CounterQuantity.COUNT, description="Measurement unit (count or time).")
    logic_id: int | None = Field(None, description="The parent logic ID this counter belongs to.")
    histogram: HistogramType | str | None = Field(None, description="Optional histogram trigger (e.g., PERSON_AGE).")
    bins: list[float] | None = Field(None, description="Pre-defined histogram bins (e.g., [20, 40, 60]).")

    def model_dump(self, **kwargs):
        kwargs.setdefault("mode", "json")
        return super().model_dump(**kwargs)


class TriggerType(Enum):
    """Timing and evaluation triggers for logic modifiers."""

    TRACK_DELETED = "track_deleted"
    LINE_CROSS_FORWARD = "line_cross_forward"
    LINE_CROSS_BACKWARD = "line_cross_backward"
    ZONE_ENTRY = "zone_entry"
    ZONE_EXIT = "zone_exit"
    DWELL_TIME_REACHED = "dwell_time_reached"


class CountAction(Enum):
    """Types of count actions triggered by a modifier."""

    INCREMENT = "INCREMENT"
    DECREMENT = "DECREMENT"
    WRONG_WAY = "WRONG_WAY"


class CountEvent(BaseModel):
    """Links a modifier trigger to a specific counter action."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    counter_id: int
    type: CountAction = Field(default=CountAction.INCREMENT)
    histogram: HistogramType | str | None = Field(None, description="Trigger for age histograms (e.g., PERSON_AGE).")
    geometry_id: int | None = Field(None, description="Optional geometry reference for dwell-time calculations.")

    def model_dump(self, **kwargs):
        kwargs.setdefault("mode", "json")
        return super().model_dump(**kwargs)


class FilterType(str, Enum):
    """
    Comprehensive list of available filter types (Operands and Operators) for Custom Logic.
    Used in the RPN (Reverse Polish Notation) filter stack.
    """

    # Logical Operators
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    # Basic
    TRUE = "true"
    FALSE = "false"
    # Attributes
    HAS_GENDER = "has_gender"
    HAS_TAG = "has_tag"
    HAS_FACE_MASK = "has_face_mask"
    # Geometry Interactions
    HAS_CROSSED_LINE = "has_crossed_line"
    HAS_VISITED_ZONE = "has_visited_zone"
    IS_IN_ZONE = "is_in_zone"
    IS_CREATED_IN_ZONE = "is_created_in_zone"
    # Height
    PERSON_HEIGHT_BIGGER_THAN = "person_height_bigger_than"
    PERSON_HEIGHT_SMALLER_THAN = "person_height_smaller_than"
    PERSON_HEIGHT_STRICTLY_BIGGER_THAN = "person_height_strictly_bigger_than"
    PERSON_HEIGHT_STRICTLY_SMALLER_THAN = "person_height_strictly_smaller_than"
    # Interaction Attributes (Evaluated at the moment of geometry interaction)
    HAS_FIRST_INTERACTION_GENDER = "has_first_interaction_gender"
    HAS_FIRST_INTERACTION_TAG = "has_first_interaction_tag"
    HAS_FIRST_INTERACTION_FACE_MASK = "has_first_interaction_face_mask"
    # Interaction Height
    FIRST_INTERACTION_HEIGHT_BIGGER_THAN = "first_interaction_person_height_bigger_than"
    FIRST_INTERACTION_HEIGHT_SMALLER_THAN = "first_interaction_person_height_smaller_than"
    FIRST_INTERACTION_HEIGHT_STRICTLY_BIGGER_THAN = "first_interaction_person_height_strictly_bigger_than"
    FIRST_INTERACTION_HEIGHT_STRICTLY_SMALLER_THAN = "first_interaction_person_height_strictly_smaller_than"
    # Advanced Geometry Counters
    NUMBER_OF_LINE_CROSSINGS = "number_of_line_crossings"
    NUMBER_OF_FORWARD_LINE_CROSSINGS = "number_of_forward_line_crossings"
    NUMBER_OF_BACKWARD_LINE_CROSSINGS = "number_of_backward_line_crossings"
    NUMBER_OF_ZONE_ENTRIES = "number_of_zone_entries"
    NUMBER_OF_ZONE_EXITS = "number_of_zone_exits"
    # Dwell Time
    ZONE_DWELL_TIME_BIGGER_THAN = "zone_dwell_time_bigger_than"
    ZONE_DWELL_TIME_SMALLER_THAN = "zone_dwell_time_smaller_than"
    ZONE_DWELL_TIME_STRICTLY_BIGGER_THAN = "zone_dwell_time_strictly_bigger_than"
    ZONE_DWELL_TIME_STRICTLY_SMALLER_THAN = "zone_dwell_time_strictly_smaller_than"
    ZONE_DWELL_TIME_CUMULATIVE_BIGGER_THAN = "zone_dwell_time_cumulative_bigger_than"
    ZONE_DWELL_TIME_CUMULATIVE_SMALLER_THAN = "zone_dwell_time_cumulative_smaller_than"
    ZONE_DWELL_TIME_CUMULATIVE_STRICTLY_BIGGER_THAN = "zone_dwell_time_cumulative_strictly_bigger_than"
    ZONE_DWELL_TIME_CUMULATIVE_STRICTLY_SMALLER_THAN = "zone_dwell_time_cumulative_strictly_smaller_than"
    # Directions
    FIRST_LINE_CROSS_DIRECTION = "first_line_cross_direction"
    LAST_LINE_CROSS_DIRECTION = "last_line_cross_direction"


class Filter(BaseModel):
    """
    Represents a single filter operand or operator in a Reverse Polish Notation (RPN) stack.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    type: FilterType | str = Field(..., description="Operand type (e.g., has_gender) or Operator (AND, OR).")
    payload: dict[str, Any] = Field(default_factory=dict, description="Additional parameters for the filter.")

    def model_dump(self, **kwargs):
        """Flat serialization for RPN compatibility."""
        # Use mode="json" by default for Filter to ensure nested types are converted
        kwargs.get("mode")
        kwargs.setdefault("mode", "json")

        # Get the standard dump
        data = super().model_dump(**kwargs)

        # Extract payload and flatten it
        payload = data.pop("payload", {})
        if isinstance(payload, dict):
            data.update(payload)

        return data


class Modifier(BaseModel):
    """
    Defines the precise conditions (Modifiers) for triggering counts in a Custom Logic.

    Hardware Limit: Sensors typically handle ~80 Modifiers per layer. Exceeding this
    will return a 'Max number of modifiers reached' error.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int | None = Field(None, description="System-assigned or CLIENT-forced unique identifier.")
    name: str | None = Field(None, description="Optional description of the modifier.")
    logic_id: int | None = Field(None, description="Parent logic identifier.")
    object_type: ObjectType = Field(default=ObjectType.PERSON)
    trigger: TriggerType | dict[str, Any] = Field(..., description="The event that triggers evaluation.")
    count_events: list[CountEvent] = Field(default_factory=list)
    filter: list[Filter] = Field(default_factory=list, description="RPN filter stack.")
    zone_of_interest: int | None = Field(alias="zoi", default=None, description="Optional linked geometry ID.")

    def model_dump(self, **kwargs):
        kwargs.setdefault("mode", "json")
        data = super().model_dump(**kwargs)
        # Ensure filters are also flattened if they were dumped recursively
        if "filter" in data and isinstance(data["filter"], list):
            # Modifier contains a list of Filters. Each Filter's model_dump
            # flattens its payload. If Pydantic's recursive dump didn't use our override,
            # we check for 'payload' and flatten it here.
            flattened_filters = []
            for f in data["filter"]:
                if isinstance(f, dict) and "payload" in f:
                    payload = f.pop("payload", {})
                    if isinstance(payload, dict):
                        f.update(payload)
                flattened_filters.append(f)
            data["filter"] = flattened_filters
        return data


class LogicType(Enum):
    """
    Standardized logic template types for counting and analytics.

    Normalizes the diverse set of template strings (e.g., XLT_LINE_IN_OUT_COUNT)
    into a stable enumeration.
    """

    CUSTOM = "XLT_CUSTOM"
    ZONE_OCCUPANCY = "XLT_ZONE_OCCUPANCY_COUNT"
    LINE_IN_OUT = "XLT_LINE_IN_OUT_COUNT"
    LINE_LATE = "XLT_LINE_LATE_COUNT"
    ZONE_IN_OUT = "XLT_ZONE_IN_OUT_COUNT"
    GROUP_LINE_IN_OUT = "XLT_GROUP_LINE_IN_OUT_COUNT"
    GROUP_LINE_LATE = "XLT_GROUP_LINE_LATE_COUNT"
    BICYCLE_LINE_IN_OUT = "XLT_BICYCLE_LINE_IN_OUT_COUNT"
    BICYCLE_LINE_LATE = "XLT_BICYCLE_LINE_LATE_COUNT"
    PRAM_LINE_IN_OUT = "XLT_PRAM_LINE_IN_OUT_COUNT"
    PRAM_LINE_LATE = "XLT_PRAM_LINE_LATE_COUNT"
    WHEELCHAIR_LINE_IN_OUT = "XLT_WHEELCHAIR_LINE_IN_OUT_COUNT"
    WHEELCHAIR_LINE_LATE = "XLT_WHEELCHAIR_LINE_LATE_COUNT"
    SHOPPING_CART_LINE_IN_OUT = "XLT_SHOPPING_CART_LINE_IN_OUT_COUNT"
    SHOPPING_CART_LINE_LATE = "XLT_SHOPPING_CART_LINE_LATE_COUNT"
    ZONE_DOOR = "XLT_ZONE_DOOR_COUNT"
    QUEUE_STATISTICS = "XLT_QUEUE_STATISTICS"
    WRONG_WAY_DETECTION = "XLT_WRONG_WAY_DETECTION"
    # Legacy/v4-compatible templates
    LEGACY_LINE_IN_OUT = "XLT_4X_LINE_IN_OUT_COUNT"
    LEGACY_LINE_LATE = "XLT_4X_LINE_LATE_COUNT"
    LEGACY_ZONE_COUNT = "XLT_4X_ZONE_COUNT"


class PathStitchingZone(BaseModel):
    """
    Represents a zone assigned to the Path Stitcher.
    Tracks lost in these zones are prolonged and potentially merged with new tracks.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    zone_id: int
    radius_mm: float = Field(alias="radius", default=1000.0, description="Max distance for merging tracks.")
    time_sec: float = Field(alias="time", default=2.0, description="Max duration to prolong lost tracks.")


class Logic(BaseModel):
    """
    Defines a counting or analytics logic applied to a geometry.

    Bridges Logic1, LogicStatus, and LogicTemplate into a stable interface.
    Supports Custom Logic via associated Counters and Modifiers.

    API Tip: When creating complex custom logics, use '?id_mode=CLIENT' on the
    Counter/Modifier endpoints to force the sensor to respect your provided IDs,
    ensuring the Web UI renders them correctly.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(description="Unique identifier for the logic.")
    name: str = Field(description="Human-readable name of the logic.")
    type: LogicType = Field(description="The template type of this logic.")
    layer_id: int | None = Field(default=None, description="The ID of the virtual counting layer.")
    optional_data: str | None = Field(default=None, description="Associated metadata or user-defined data.")

    def model_dump(self, **kwargs):
        """Ensures LogicType is serialized as a string value."""
        kwargs.setdefault("mode", "json")
        return super().model_dump(**kwargs)


class Layer(BaseModel):
    """
    Represents a virtual counting layer in the Xovis scene.

    Layers are used to group logics and define the spatial Zone of Interest (ZOI).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(description="Unique identifier for the layer.")
    name: str = Field(description="Human-readable name of the layer.")
    zone_of_interest: list[tuple[float, float]] = Field(
        alias="zoi",
        default_factory=list,
        description="The spatial polygon defining the area of interest for this layer.",
    )


class TimeFormat(str, Enum):
    """Supported time formats for historical data serialization."""

    UNIX_TIME_MS = "UNIX_TIME_MS"
    UNIX_TIME_S = "UNIX_TIME_S"
    RFC3339 = "RFC3339"


class HistoryMeasurement(BaseModel):
    """
    Represents a single time-series bin in the historical data output.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    begin: int | str = Field(..., description="Start of the bin interval.")
    end: int | str = Field(..., description="End of the bin interval.")
    records: int = Field(..., description="Number of 1-minute records covered by this bin.")
    counts: list[dict[str, Any]] = Field(default_factory=list, description="List of counter values (id, value).")


class HistoryQuery(BaseModel):
    """
    Internal model used to validate and normalize historical data query parameters.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    begin: XovisTime = Field(..., description="Start of the time range (Unix ms or relative).")
    end: XovisTime = Field(default="now", description="End of the time range (Unix ms or relative).")
    resolution_min: int = Field(default=0, description="Aggregation resolution in minutes.")
    time_format: TimeFormat = Field(default=TimeFormat.UNIX_TIME_MS)
    include_empty: bool = Field(default=False)


class HistoryLogics(BaseModel):
    """
    Bridge model for historical logic data.

    Provides a stable interface for time-series count data, abstracting
    away firmware-specific metadata structures.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    begin: int | str
    end: int | str
    begin_data: int | str | None = None
    end_data: int | str | None = None
    resolution_ms: int | None = None
    number_of_bins: int | None = None
    measurements: list[HistoryMeasurement] = Field(default_factory=list)
    config: dict[str, Any] | None = None


class StorageCapacity(BaseModel):
    """Hardware information related to data persistence capacity."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    memory: int = Field(..., description="Total memory in bytes.")
    count_records: int = Field(..., description="Maximum number of records.")
    time: str = Field(..., description="Remaining recording time as human readable string (e.g., 2y 126d).")
    time_s: int = Field(..., description="Remaining recording time in seconds.")
    fill_level_percent: float = Field(..., description="Percentage of used storage.")


class StoredDataRecord(BaseModel):
    """Metadata about a specific count record in the database."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: int
    time_begin: str
    duration_s: int
    data_size: int


class StoredData(BaseModel):
    """Status of the internally stored historical data."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    time_begin: str = Field(..., description="Timestamp of the oldest stored data (RFC3339).")
    time_end: str = Field(..., description="Timestamp of the latest stored data (RFC3339).")
    retention_time_s: int | None = None
    retention_time: str | None = None
    number_of_count_records: int
    oldest_count_record: StoredDataRecord | None = None
    newest_count_record: StoredDataRecord | None = None
    logics: list[dict[str, Any]] = Field(default_factory=list)
    counts: list[dict[str, Any]] = Field(default_factory=list)


class HistoryStatus(BaseModel):
    """
    Bridge model for the historical data storage status.

    Combines hardware capacity metrics and stored data metadata into a
    firmware-agnostic diagnostic object.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    capacity: StorageCapacity = Field(..., alias="storage_capacity", validation_alias=AliasChoices("capacity", "storage"))
    stored_data: StoredData = Field(..., description="Details about current data on flash.")

    @model_validator(mode="before")
    @classmethod
    def _flatten_storage(cls, data: Any) -> Any:
        """Handles cases where capacity is nested under 'storage'."""
        if isinstance(data, dict) and "storage" in data and "capacity" in data["storage"]:
            # firmware v5 style
            storage = data["storage"]
            return {"capacity": storage["capacity"], "stored_data": storage.get("stored_data", {})}
        return data


class HeatHeightMap(BaseModel):
    """
    Bridge model for spatial heat and height map data.

    Abstracts the 2D floating-point array and its mapping metadata.
    Note: The two-dimensional 'data' array must be scaled to the background image.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    width_px: int = Field(..., alias="width", validation_alias=AliasChoices("width", "width_px"))
    height_px: int = Field(..., alias="height", validation_alias=AliasChoices("height", "height_px"))
    data: list[list[float]] = Field(..., description="2D array of spatial metrics.")


class StartStopQuery(BaseModel):
    """
    Internal model used to validate and normalize start/stop points query parameters.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    begin: XovisTime = Field(..., description="Start of the time range (Unix ms or relative).")
    end: XovisTime = Field(default="now", description="End of the time range (Unix ms or relative).")
    max: int = Field(default=1000, description="Maximum number of points.")
    points: bool = Field(default=True)


class StartStopPoints(BaseModel):
    """
    Bridge model for track start and stop coordinates.

    Used by agents to optimize geometry placement by analyzing
    where tracks typically appear and vanish.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    begin: int
    end: int
    start_points: list[list[float]] = Field(default_factory=list, description="List of [x, y, z] vectors.")
    stop_points: list[list[float]] = Field(default_factory=list, description="List of [x, y, z] vectors.")


# --- DataPush Bridge Models ---


class DataPushType(str, Enum):
    """Supported types of data push agents."""

    LOGICS = "LOGICS"
    LIVE_DATA = "LIVE_DATA"
    STATUS = "STATUS"
    WIFI_BT = "WIFI_BT"
    RECORDING = "RECORDING"


class SchedulerType(str, Enum):
    """Scheduling strategies for data push."""

    INTERVAL = "INTERVAL"
    PERIODIC = "PERIODIC"
    IMMEDIATE = "IMMEDIATE"
    ADVANCED = "ADVANCED"


class IntervalType(str, Enum):
    """Discrete time intervals for data push."""

    ONE_DAY = "ONE_DAY"
    ONE_HOUR = "ONE_HOUR"
    FIFTEEN_MINUTES = "FIFTEEN_MINUTES"
    FIVE_MINUTES = "FIVE_MINUTES"
    ONE_MINUTE = "ONE_MINUTE"
    THIRTY_SECONDS = "THIRTY_SECONDS"
    FIVE_SECONDS = "FIVE_SECONDS"


class RetryMode(str, Enum):
    """Strategies for handling transmission failures."""

    DROP = "DROP"
    INTERVAL = "INTERVAL"
    INCREASING_DELAY = "INCREASING_DELAY"
    INCREASING_DELAY_EXPONENTIAL = "INCREASING_DELAY_EXPONENTIAL"


class RetryConfig(BaseModel):
    """Configuration for data push retry logic."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    mode: RetryMode = Field(default=RetryMode.DROP)
    max_number: int = Field(default=0)
    reset_on_next_push_schedule: bool = Field(default=True)
    delay_start_min: float = Field(default=2.0)
    delay_start_max: float = Field(default=2.0)
    delay_interval_min: Optional[float] = None
    delay_interval_max: Optional[float] = None
    delay_increase_const: Optional[float] = None
    delay_increase_factor: Optional[float] = None


class Scheduler(BaseModel):
    """Data push scheduling and retry policy."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    type: SchedulerType = Field(..., alias="type")
    interval: Optional[IntervalType] = None
    cron: Optional[str] = None
    retry: RetryConfig = Field(default_factory=RetryConfig)

    def model_dump(self, **kwargs) -> dict[str, Any]:
        # Always exclude none for scheduler to be safe with hardware schemas
        kwargs["exclude_none"] = True
        data = super().model_dump(**kwargs)
        if self.type != SchedulerType.INTERVAL:
            data.pop("interval", None)
        return data


class DataFormatType(str, Enum):
    """Available serialization formats for pushed data."""

    JSON = "JSON"
    PROTOBUF = "PROTOBUF"
    BINARY = "BINARY"
    LEGACY_XOVIS_XML = "LEGACY_XOVIS_XML"
    RECORDING = "RECORDING"


class DataFormat(BaseModel):
    """Configuration for data serialization."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    type: DataFormatType = Field(default=DataFormatType.JSON)
    version: str = Field(default="5.x")
    pretty: bool = Field(default=False)
    time: TimeFormat = Field(default=TimeFormat.UNIX_TIME_MS)


class DataConfig(BaseModel):
    """Core configuration for data content and resolution."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    resolution: Optional[str] = None
    package_size: int = Field(default=1)
    include_empty: Optional[bool] = None
    empty_frames: Optional[str] = None
    meta_data_package_full: bool = Field(default=False)
    meta_data_sensor_full: bool = Field(default=False)
    meta_data_config_enable: bool = Field(default=False)
    format: DataFormat = Field(default_factory=DataFormat)
    normalization: Optional[Union[list[str], Literal["ALL", "NONE"]]] = Field(default=None)


class DataPushFilters(BaseModel):
    """Fine-grained filters for data push content."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # Literal MUST come first to prevent Pydantic from coercing "ALL" into ["ALL"]
    included_objects: Optional[Union[Literal["ALL", "NONE"], list[str]]] = Field(
        default=None, validation_alias=AliasChoices("included_objects", "includedObjects")
    )
    included_scene_events: Optional[Union[Literal["ALL", "NONE"], list[str]]] = Field(
        default=None, validation_alias=AliasChoices("included_scene_events", "includedSceneEvents")
    )
    included_count_events: Optional[Union[Literal["ALL", "NONE"], list[str]]] = Field(
        default=None, validation_alias=AliasChoices("included_count_events", "includedCountEvents")
    )
    included_info_events: Optional[Union[Literal["ALL", "NONE"], list[str]]] = Field(
        default=None, validation_alias=AliasChoices("included_info_events", "includedInfoEvents")
    )
    filter_events_by_objects: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("filter_events_by_objects", "filterEventsByObjects"),
    )
    included_logics: Optional[Union[Literal["ALL", "NONE"], list[int]]] = Field(
        default=None, validation_alias=AliasChoices("included_logics", "includedLogics")
    )


class AgentConfig(BaseModel):
    """Composite configuration for a data push agent."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    scheduler: Scheduler
    data: DataConfig
    filters: Optional[DataPushFilters] = None


class DataPushAgent(BaseModel):
    """
    Bridge model for a DataPush Agent.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: Optional[int] = None
    name: str
    type: DataPushType
    enabled: bool = Field(default=True)
    connection: int = Field(..., validation_alias=AliasChoices("connection", "connectionId"))
    config: AgentConfig


class DataPushAgentCollection(BaseModel):
    """Collection of DataPush Agents."""

    agents: list[DataPushAgent] = Field(default_factory=list)


class DataPushProtocol(str, Enum):
    """Supported data transfer protocols for connections."""

    HTTP = "HTTP"
    FTP = "FTP"
    SFTP = "SFTP"
    MQTT = "MQTT"
    TCP = "TCP"
    UDP = "UDP"


class HTTPAuthMethod(str, Enum):
    """HTTP authentication methods."""

    NONE = "NONE"
    BASIC = "BASIC"
    DIGEST = "DIGEST"
    DIGEST_IE = "DIGEST_IE"
    BEARER_TOKEN = "BEARER_TOKEN"


class HTTPHeaderField(BaseModel):
    """Custom HTTP header field."""

    name: str
    value: str


class HTTPConfig(BaseModel):
    """Configuration for HTTP(S) data push connections."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    uri: str
    port: Optional[int] = None
    ssl_enable: bool = Field(default=False)
    auth_method: HTTPAuthMethod = Field(default=HTTPAuthMethod.NONE)
    auth_data: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    connection_timeout_s: float = Field(default=2.0)
    chunked_transfer_enabled: bool = Field(default=False)
    ignore_proxy: bool = Field(default=False)
    custom_header_fields: Optional[list[HTTPHeaderField]] = Field(default=None)


class FTPDirectoryMode(str, Enum):
    """FTP directory traversing method."""

    SINGLECWD = "SINGLECWD"
    MULTICWD = "MULTICWD"
    NOCWD = "NOCWD"


class FTPFileMode(str, Enum):
    """FTP file transmission mode."""

    PACKAGE = "PACKAGE"
    APPEND_INTERVAL = "APPEND_INTERVAL"
    APPEND_MAX_SIZE = "APPEND_MAX_SIZE"


class FTPConfig(BaseModel):
    """Configuration for FTP(S) data push connections."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    uri: str
    user: str
    password: str
    port: Optional[int] = None
    path: Optional[str] = None
    ssl_enable: bool = Field(default=False)
    account_info: Optional[str] = None
    alternative_to_user: Optional[str] = None
    connection_timeout_s: float = Field(default=2.0)
    response_timeout_s: float = Field(default=2.0)
    create_directories: bool = Field(default=True)
    directory_mode: FTPDirectoryMode = Field(default=FTPDirectoryMode.SINGLECWD)
    file_mode: FTPFileMode = Field(default=FTPFileMode.PACKAGE)
    max_file_size: int = Field(default=0)
    ignore_proxy: bool = Field(default=False)
    use_pret: bool = Field(default=False)


class SFTPConfig(BaseModel):
    """Configuration for SFTP data push connections."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    uri: str
    user: str
    password: str
    port: int = Field(default=22)
    path: Optional[str] = None
    host_key: Optional[str] = None
    create_directories: bool = Field(default=True)
    file_mode: FTPFileMode = Field(default=FTPFileMode.PACKAGE)
    max_file_size: int = Field(default=0)
    new_directory_permission: str = Field(default="rwxr-xr-x")
    new_file_permission: str = Field(default="rw-r--r--")
    ssh_compression_enable: bool = Field(default=True)
    connection_timeout_s: float = Field(default=2.0)
    ignore_proxy: bool = Field(default=False)


class MQTTConfig(BaseModel):
    """Configuration for MQTT(S) data push connections."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    uri: str
    topic: str
    port: Optional[int] = None
    auth_enable: bool = Field(default=False)
    user: Optional[str] = None
    password: Optional[str] = None
    ssl_enable: bool = Field(default=False)
    qos_level: int = Field(default=0)
    websocket_enable: bool = Field(default=False)
    client_id: Optional[str] = None
    connection_timeout_s: float = Field(default=0.0)


class TCPUDPMode(str, Enum):
    """Operating modes for TCP and UDP connections."""

    CLIENT = "CLIENT"
    SERVER = "SERVER"
    LEGACY_EVENT_STREAM_SERVER = "LEGACY_EVENT_STREAM_SERVER"
    LEGACY_OBJECT_STREAM_SERVER = "LEGACY_OBJECT_STREAM_SERVER"


class TCPConfig(BaseModel):
    """Configuration for TCP data push connections."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    mode: TCPUDPMode = Field(default=TCPUDPMode.CLIENT)
    uri: Optional[str] = None
    port: Optional[int] = None
    connection_timeout_s: float = Field(default=2.0)

    def model_dump(self, **kwargs) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Force camelCase for hardware compatibility
        data["connectionTimeoutS"] = data.get("connection_timeout_s", 2.0)
        return data


class UDPConfig(BaseModel):
    """Configuration for UDP data push connections."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    mode: TCPUDPMode = Field(default=TCPUDPMode.CLIENT)
    uri: Optional[str] = None
    port: Optional[int] = None
    connection_timeout_s: float = Field(default=2.0)

    def model_dump(self, **kwargs) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Force camelCase for hardware compatibility
        data["connectionTimeoutS"] = data.get("connection_timeout_s", 2.0)
        return data


class DataPushConnection(BaseModel):
    """
    Bridge model for a DataPush Connection.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: Optional[int] = None
    name: str
    protocol: DataPushProtocol
    config: Union[HTTPConfig, FTPConfig, SFTPConfig, MQTTConfig, TCPConfig, UDPConfig]

    def model_dump(self, **kwargs) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Ensure config field is present and serialized correctly
        if "config" not in data:
            data["config"] = self.config.model_dump(**kwargs)
        return data


class DataPushTestResponse(BaseModel):
    """Result of a DataPush connection test."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    status: str = Field(..., alias="connection_test.status")
    code: Optional[int] = Field(None, alias="connection_test.server_response.code")
    info: Optional[str] = Field(None, alias="connection_test.server_response.info")

    @model_validator(mode="before")
    @classmethod
    def _flatten_response(cls, data: Any) -> Any:
        if isinstance(data, dict) and "connection_test" in data:
            test = data["connection_test"]
            if isinstance(test, dict):
                data["connection_test.status"] = test.get("status")
                resp = test.get("server_response")
                if isinstance(resp, dict):
                    data["connection_test.server_response.code"] = resp.get("code")
                    data["connection_test.server_response.info"] = resp.get("info")
        return data


class DataPushConnectionCollection(BaseModel):
    """Collection of DataPush Connections."""

    connections: list[DataPushConnection] = Field(default_factory=list)


class TransmitStatus(BaseModel):
    """Detailed statistics for data transmission."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    protocol: Optional[str] = None
    server: Optional[str] = None
    port: Optional[int] = None
    time: Optional[str] = None
    duration_ms: Optional[int] = None
    size_b: Optional[int] = None
    size: Optional[str] = None
    speed_bps: Optional[int] = None
    speed: Optional[str] = None
    code: Optional[int] = None
    info: Optional[str] = None


class DataPushStatus(BaseModel):
    """
    Bridge model for DataPush Agent status and diagnostics.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: int
    name: str
    type: DataPushType
    no_of_successful: int = Field(default=0, alias="transmit.no_of_successful")
    last_successful: Optional[TransmitStatus] = Field(None, alias="transmit.last_successful")
    no_of_failed: int = Field(default=0, alias="transmit.no_of_failed")
    last_failed: Optional[TransmitStatus] = Field(None, alias="transmit.last_failed")
    sent_total: str = Field(default="0B", alias="transmit.sent_total")
    sent_total_bytes: int = Field(default=0, alias="transmit.sent_total_bytes")

    @model_validator(mode="before")
    @classmethod
    def _flatten_transmit(cls, data: Any) -> Any:
        if isinstance(data, dict) and "transmit" in data:
            transmit = data.pop("transmit")
            if isinstance(transmit, dict):
                for k, v in transmit.items():
                    data[f"transmit.{k}"] = v
        return data


class DataPushStatusCollection(BaseModel):
    """Collection of DataPush Agent statuses."""

    agent_states: list[DataPushStatus] = Field(default_factory=list, alias="status")
    last_stored: Optional[Union[dict[str, Any], str]] = None

    @model_validator(mode="before")
    @classmethod
    def _flatten_collection(cls, data: Any) -> Any:
        if isinstance(data, dict) and "status" in data and "agent_states" not in data:
            data["agent_states"] = data.pop("status")
        return data


class DataPushTriggerType(str, Enum):
    """Available trigger modes for manual data recovery."""

    ALL = "ALL"
    TIME_RANGE = "TIME_RANGE"
    LAST_PACKAGE = "LAST_PACKAGE"
    DUMMY_DATA = "DUMMY_DATA"


class DataPushTriggerConfig(BaseModel):
    """Configuration for a manual data push trigger."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    type: DataPushTriggerType
    time_from: Optional[XovisTime] = None
    time_to: Optional[XovisTime] = None
    package_id_start: Optional[int] = None
    file_name_prefix: Optional[str] = None

    @field_serializer("time_from", "time_to")
    def _serialize_as_iso8601(self, value: Optional[int]) -> Optional[str]:
        """Ensures timestamps are serialized as ISO-8601 UTC strings for the Trigger API."""
        if value is not None:
            dt = datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        return None


class DataPushTriggerStatus(str, Enum):
    """Operational status of a trigger push."""

    IDLE = "IDLE"
    BUSY = "BUSY"


class DataPushTriggerInfo(BaseModel):
    """Status information for a running or finished trigger push."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    status: DataPushTriggerStatus
    trigger_time: Optional[str] = None
    trigger_config: Optional[DataPushTriggerConfig] = None


class SystemInfo(BaseModel):
    """
    Core hardware and firmware details extracted during the Control Plane bootstrap phase.

    Attributes:
        mac_address (str): The sensor's MAC address (mapped from network serial).
        sw_version (str): The firmware version running on the edge device.
        serial_number (str): The physical hardware identifier.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    mac_address: str = Field(alias="serial", default="", json_schema_extra={"ai_privacy": "HASH"})
    sw_version: str = Field(alias="fw_version", default="")
    serial_number: str = Field(alias="hw_id", default="")
