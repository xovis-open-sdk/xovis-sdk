"""
Xovis SDK - Tier 1: Smoke & Stateless Tests

Validates the XovisTime Pydantic parser and relative time normalization.
Ensures zero-dependency, high-performance time calculations.
"""

import time
from datetime import datetime

import pytest
from pydantic import BaseModel, ValidationError

from xovis.utils.time import XovisTime


class TimeModel(BaseModel):
    """Test model for validating XovisTime Annotated type."""

    timestamp: XovisTime


def test_xovis_time_integer_passthrough() -> None:
    """Validates that raw integer milliseconds are passed through unchanged."""
    raw_ms = 1717968000000
    model = TimeModel(timestamp=raw_ms)
    assert model.timestamp == raw_ms


def test_xovis_time_numeric_string() -> None:
    """Validates that numeric strings are correctly cast to integers."""
    raw_ms_str = "1717968000000"
    model = TimeModel(timestamp=raw_ms_str)
    assert model.timestamp == 1717968000000
    assert isinstance(model.timestamp, int)


def test_xovis_time_relative_now() -> None:
    """Validates the 'now' keyword normalization."""
    before = int(time.time() * 1000)
    model = TimeModel(timestamp="now")
    after = int(time.time() * 1000)

    assert before <= model.timestamp <= after


@pytest.mark.parametrize(
    "input_str,multiplier",
    [
        ("-1s", 1_000),
        ("-1m", 60_000),
        ("-1h", 3_600_000),
        ("-1d", 86_400_000),
        ("-1w", 604_800_000),
        ("-1M", 2_592_000_000),
        ("-1y", 31_536_000_000),
    ],
)
def test_xovis_time_relative_offsets(input_str: str, multiplier: int) -> None:
    """Validates relative time offsets (s, m, h, d, w, M, y)."""
    expected_approx = int(time.time() * 1000) - multiplier
    model = TimeModel(timestamp=input_str)

    # Allow for 100ms drift during execution
    assert abs(model.timestamp - expected_approx) < 100


def test_xovis_time_complex_relative() -> None:
    """Validates multi-unit offsets (e.g., -24h)."""
    offset_ms = 24 * 3_600_000
    expected_approx = int(time.time() * 1000) - offset_ms
    model = TimeModel(timestamp="-24h")

    assert abs(model.timestamp - expected_approx) < 100


def test_xovis_time_invalid_format() -> None:
    """Validates that invalid strings raise ValueError."""
    with pytest.raises(ValidationError) as excinfo:
        TimeModel(timestamp="invalid")
    assert "Invalid Xovis time format" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        TimeModel(timestamp="1d")  # Missing minus sign
    assert "Invalid Xovis time format" in str(excinfo.value)


def test_xovis_time_datetime_object() -> None:
    """Validates that datetime objects are correctly converted to Unix milliseconds."""
    dt = datetime(2024, 6, 9, 12, 0, 0)
    expected_ms = int(dt.timestamp() * 1000)
    model = TimeModel(timestamp=dt)
    assert model.timestamp == expected_ms


def test_xovis_time_iso8601_string() -> None:
    """Validates that ISO 8601 strings are correctly converted."""
    iso_str = "2024-06-09T12:00:00"
    dt = datetime.fromisoformat(iso_str)
    expected_ms = int(dt.timestamp() * 1000)
    model = TimeModel(timestamp=iso_str)
    assert model.timestamp == expected_ms


def test_xovis_time_iso8601_zulu() -> None:
    """Validates that ISO 8601 'Z' suffix is handled as UTC."""
    iso_str = "2024-06-09T12:00:00Z"
    # Replacing Z with +00:00 is what the parser does
    dt = datetime.fromisoformat("2024-06-09T12:00:00+00:00")
    expected_ms = int(dt.timestamp() * 1000)
    model = TimeModel(timestamp=iso_str)
    assert model.timestamp == expected_ms


def test_xovis_time_timezone_offset() -> None:
    """Validates that ISO 8601 with timezone offsets are correctly normalized to UTC."""
    # 12:00 in UTC+2 should be 10:00 in UTC
    iso_str = "2024-06-09T12:00:00+02:00"
    expected_dt = datetime.fromisoformat("2024-06-09T10:00:00+00:00")
    expected_ms = int(expected_dt.timestamp() * 1000)
    model = TimeModel(timestamp=iso_str)
    assert model.timestamp == expected_ms


def test_xovis_time_datetime_with_tz() -> None:
    """Validates that datetime objects with timezone are correctly normalized."""
    from datetime import timedelta, timezone

    tz = timezone(timedelta(hours=5))
    dt = datetime(2024, 6, 9, 12, 0, 0, tzinfo=tz)
    # 12:00 UTC+5 is 07:00 UTC
    expected_ms = int(datetime(2024, 6, 9, 7, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    model = TimeModel(timestamp=dt)
    assert model.timestamp == expected_ms


def test_xovis_time_invalid_type() -> None:
    """Validates that invalid types raise ValueError (wrapped by Pydantic)."""
    with pytest.raises(ValidationError) as excinfo:
        TimeModel(timestamp=["not", "a", "string"])
    assert "Expected int, datetime, or str" in str(excinfo.value)
