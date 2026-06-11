"""
Xovis SDK - Time Utilities

Provides high-performance, zero-dependency time parsing and normalization
for Xovis-specific time formats, including relative offsets and Unix milliseconds.
"""

import re
import time
from datetime import datetime
from typing import Annotated, Any, Optional, Union

from pydantic import BeforeValidator

_TIME_REGEX = re.compile(r"^(now)|(?:-(\d+)([smhdwMy]))$")

_MULTIPLIERS = {
    "s": 1_000,
    "m": 60_000,
    "h": 3_600_000,
    "d": 86_400_000,
    "w": 604_800_000,
    "M": 2_592_000_000,
    "y": 31_536_000_000,
}


def _parse_relative_time(value: Any, _now: Optional[float] = None) -> int:
    """Parses raw ms, datetime, or strings (ISO 8601, relative) to Unix ms in UTC.

    Returns:
        int: Unix timestamp in milliseconds.
    """
    if not value:
        return 0

    result_int = 0
    if isinstance(value, int):
        result_int = value
    elif isinstance(value, datetime):
        # We ensure it's UTC or convert to UTC if it has timezone info
        if value.tzinfo is None:
            # Naive datetimes are assumed to be in system local time by .timestamp()
            # but for SDK consistency with relative 'now', we keep it as is.
            result_int = int(value.timestamp() * 1000)
        else:
            result_int = int(value.timestamp() * 1000)
    elif isinstance(value, str):
        val_str = value.strip()
        if val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit()):
            result_int = int(val_str)
        else:
            match = _TIME_REGEX.match(val_str)
            if match:
                now_ts = _now if _now is not None else time.time()
                if match.group(1) == "now":
                    result_int = int(now_ts * 1000)
                else:
                    amount, unit = int(match.group(2)), match.group(3)
                    result_int = int(now_ts * 1000) - (amount * _MULTIPLIERS[unit])
            else:
                try:
                    dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
                    result_int = int(dt.timestamp() * 1000)
                except ValueError:
                    raise ValueError(f"Invalid Xovis time format: {value}")
    else:
        raise ValueError(f"Expected int, datetime, or str, got {type(value)}")

    return result_int


XovisTime = Annotated[Union[int, str, datetime], BeforeValidator(_parse_relative_time)]
"""Annotated type for Xovis-compliant time inputs.

Accepts Unix milliseconds (int), datetime objects, ISO 8601 strings,
or relative time strings (e.g., 'now', '-1h', '-30d').
Normalizes all inputs to Unix milliseconds (int) during Pydantic validation.
"""
