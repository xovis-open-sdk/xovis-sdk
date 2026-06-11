"""
Xovis SDK - Global Configuration

Governs universal behaviors like caching aggressiveness, polling rates, and
background tasks across the Data, Control, and State Planes.
"""

from pydantic import BaseModel, ConfigDict, Field


class XovisConfigModel(BaseModel):
    """
    Global configuration object for the Xovis SDK.

    This model defines the runtime parameters for the SDK, including
    background watcher behavior and polling intervals. It uses Pydantic V2
    for validation and settings management.

    Attributes:
        CACHE_ENABLED (bool): Determines if DeviceClients should spawn
            background workers to monitor configuration state.
        POLL_INTERVAL_SECONDS (int): The frequency at which background
            workers poll the hardware or HUB for state changes.
    """

    model_config = ConfigDict(validate_assignment=True)

    CACHE_ENABLED: bool = Field(
        default=False,
        description="If True, DeviceClients spawn background workers to fetch and monitor the config hash.",
    )
    POLL_INTERVAL_SECONDS: int = Field(default=10, description="Interval in seconds for the background watcher polling loop.")


config = XovisConfigModel()
