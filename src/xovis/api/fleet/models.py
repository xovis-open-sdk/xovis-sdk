"""Models for the fleet orchestration module."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BulkOperationResult(BaseModel, Generic[T]):
    """
    Structured outcome mapping successes and exceptions per device.

    Attributes:
        successes (dict[str, T]): Mapping of device hosts to their successful results.
        exceptions (dict[str, Exception]): Mapping of device hosts to their exceptions.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    successes: dict[str, T] = Field(default_factory=dict)
    exceptions: dict[str, Exception] = Field(default_factory=dict)
