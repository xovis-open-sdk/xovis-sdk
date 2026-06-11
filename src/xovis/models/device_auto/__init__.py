"""
Xovis SDK - Auto-generated Device Models Facade

Operates within the Control Plane.
Provides a unified entry point for Pydantic V2 models generated from
Xovis edge sensor OpenAPI specifications. This facade defaults to the
latest stable model version for static typing purposes while allowing
the SDK to handle multiple firmware versions at runtime.
"""

from __future__ import annotations

from .versions import v5_9_2 as v5_9_2_models

# 2. Expose the specific version modules so the DeviceClient can dynamically swap them
from .versions import v5_9_11 as stable_models

# 1. Export the latest stable version into the global namespace for IDE Autocomplete
from .versions.v5_9_11 import *
