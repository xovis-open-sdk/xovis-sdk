import functools
import json
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Callable

from pydantic import BaseModel
from pydantic_core import Url


def serialize_mcp_value(obj: Any) -> Any:
    """Recursively serializes complex objects into JSON-compatible primitives,
    enforcing a 100-record slice on lists.
    """
    if isinstance(obj, list):
        # Enforce strict max_records=100 pagination slice
        truncated_list = obj[:100]
        return [serialize_mcp_value(item) for item in truncated_list]

    if isinstance(obj, dict):
        return {key: serialize_mcp_value(val) for key, val in obj.items()}

    if isinstance(obj, BaseModel):
        try:
            dumped = obj.model_dump(mode="json", exclude_unset=True)
            return serialize_mcp_value(dumped)
        except Exception:
            try:
                dumped = obj.model_dump()
                return serialize_mcp_value(dumped)
            except Exception:
                pass

    if isinstance(obj, Enum):
        return obj.value

    if isinstance(obj, (Url, IPv4Address, IPv6Address)):
        return str(obj)

    return obj


def mcp_safe_serializer(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to intercept and serialize complex Pydantic V2 objects and paginate lists."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)

            # If the result is already a string (potentially JSON)
            if isinstance(result, str):
                try:
                    parsed = json.loads(result)
                    serialized = serialize_mcp_value(parsed)
                    return json.dumps(serialized, indent=2)
                except json.JSONDecodeError:
                    return result

            serialized = serialize_mcp_value(result)
            return json.dumps(serialized, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    return wrapper
