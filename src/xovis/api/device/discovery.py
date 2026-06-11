"""
Xovis SDK - Discovery & Firmware Autonomy
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Default path for discovery data - Not publicly shared
DISCOVERY_PATH = Path("discovery_delta.json")


class FieldDelta(BaseModel):
    """Represents a discovered unknown field and its observed values/types."""

    observed_types: set[str] = Field(default_factory=set)
    sample_values: list[Any] = Field(default_factory=list, max_length=5)
    first_seen_version: Optional[str] = None
    last_seen_version: Optional[str] = None
    endpoint: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def update(self, value: Any, version: Optional[str], endpoint: Optional[str]):
        """
        Updates the delta with a new observed value.

        Args:
            value (Any): The observed value of the unknown field.
            version (Optional[str]): The firmware version where it was seen.
            endpoint (Optional[str]): The API endpoint where it was seen.
        """
        type_name = type(value).__name__
        self.observed_types.add(type_name)
        if value not in self.sample_values:
            self.sample_values.append(value)
            if len(self.sample_values) > 5:
                self.sample_values.pop(0)
        self.last_seen_version = version or self.last_seen_version
        if not self.first_seen_version:
            self.first_seen_version = version
        self.endpoint = endpoint or self.endpoint


class DiscoveryDelta(BaseModel):
    """Aggregated discovery report for a specific model/entity."""

    entity_name: str
    fields: dict[str, FieldDelta] = Field(default_factory=dict)


class DiscoveryManager:
    """
    Manages the passive capture of unknown hardware API fields.

    Operates in the Control Plane to identify firmware drift without breaking
    production stability.
    """

    def __init__(self, persist_path: Path = DISCOVERY_PATH):
        """
        Initializes the DiscoveryManager.

        Args:
            persist_path (Path): File path where discovery deltas are persisted.
        """
        self.persist_path = persist_path
        self.deltas: dict[str, DiscoveryDelta] = {}
        self._load()
        self._enabled = os.getenv("XOVIS_DISCOVERY_MODE", "0") == "1"

    def _load(self):
        if self.persist_path.exists():
            try:
                with open(self.persist_path) as f:
                    data = json.load(f)
                    for entity, delta_data in data.items():
                        # Convert sets back from lists
                        for _field_name, field_data in delta_data.get("fields", {}).items():
                            if "observed_types" in field_data:
                                field_data["observed_types"] = set(field_data["observed_types"])
                        self.deltas[entity] = DiscoveryDelta(**delta_data)
            except Exception as e:
                logger.error(f"Failed to load discovery delta: {e}")

    def _save(self):
        if not self.persist_path.parent.exists():
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            output = {}
            for entity, delta in self.deltas.items():
                delta_dict = delta.model_dump()
                # Convert sets to lists for JSON serialization
                for field_name, field_data in delta_dict.get("fields", {}).items():
                    field_data["observed_types"] = list(self.deltas[entity].fields[field_name].observed_types)
                output[entity] = delta_dict

            # Use atomic-ish write
            temp_path = self.persist_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(output, f, indent=4)

            if os.name == "nt" and self.persist_path.exists():
                os.remove(self.persist_path)
            os.rename(temp_path, self.persist_path)
        except Exception as e:
            logger.error(f"Failed to save discovery delta: {e}")

    def capture(
        self,
        entity_name: str,
        raw_data: dict[str, Any],
        known_fields: set[str],
        version: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        """
        Captures unknown fields from a raw payload.

        Args:
            entity_name (str): The logical name of the model being validated.
            raw_data (Dict[str, Any]): The raw JSON payload from the sensor.
            known_fields (Set[str]): The set of fields currently known to the SDK.
            version (Optional[str]): The firmware version of the sensor.
            endpoint (Optional[str]): The API endpoint that returned the data.
        """
        if not self._enabled:
            return

        unknown_fields = set(raw_data.keys()) - known_fields
        if not unknown_fields:
            return

        if entity_name not in self.deltas:
            self.deltas[entity_name] = DiscoveryDelta(entity_name=entity_name)

        delta = self.deltas[entity_name]
        changed = False
        for field in unknown_fields:
            if field not in delta.fields:
                delta.fields[field] = FieldDelta()
                changed = True

            delta.fields[field].update(raw_data[field], version, endpoint)
            changed = True  # Types or values might have updated

        if changed:
            self._save()


# Global instance for easy access within the SDK
discovery_manager = DiscoveryManager()
