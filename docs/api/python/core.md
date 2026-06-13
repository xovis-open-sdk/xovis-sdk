# Core SDK Reference

The Core SDK provides the foundational type system, Pydantic models, and cross-plane utilities that power the Xovis Open SDK. It serves as the \\Base Layer\\ ensuring strict validation and consistent behavior across the entire quadrifurcated architecture.

## Architectural Pillars

1.  **Strict Type Enforcement**: Leveraging Pydantic V2, the core models ensure that every piece of data entering the SDK—whether from an edge sensor or a Cloud HUB—is validated against rigorous schemas.
2.  **Universal Models**: Unified representations for \Device\ and \HubDevice\ allow for seamless transition between single-sensor management and fleet-scale orchestration.
3.  **High-Performance Utilities**: Specialized primitives for asynchronous loops, privacy hashing, and ISO-8601 time handling, optimized for the SDK's high-throughput requirements.

## Models

::: xovis.models.device
::: xovis.models.hub_device

## Dynamic Type Safety (`xovis_types`)

While the core models provide structure, the SDK supports **Dynamic Type Generation** to provide literal-level safety for your specific environment.

### Why use dynamic types?
Because every Xovis installation is unique (with different Agent names, Zone IDs, and Line configurations), static SDK code cannot know your specific topology. By generating a local `xovis_types.py` module, you gain:
- **IDE Autocomplete**: See your actual sensor names in your editor.
- **Static Validation**: Tools like `mypy` or `pyright` can catch invalid references before you run the code.
- **Strict Literals**: Enforce that only existing zones or agents are used in your logic.

### How to generate
Use the Xovis CLI to probe a live sensor and build your local type definitions:

```bash
xovis-cli generate-types --host <SENSOR_IP>
```

This will create `src/xovis/models/xovis_types.py`. Note that this file is environment-specific and is typically excluded from version control to prevent conflicts across different installations.

## Utilities

::: xovis.utils.time
::: xovis.utils.privacy
::: xovis.utils.loop
