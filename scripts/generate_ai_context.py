import os
from pathlib import Path


def generate_llms_txt():
    """Generates the llms.txt standard for AI ingestion.

    This function generates the standard `llms.txt` file inside the `docs/`
    directory. It details the core philosophy, key API boundaries, safety
    protocols, and common coding patterns of the xovis-sdk to ensure optimal
    context injection for autonomous AI agents.
    """
    # Base path for docs
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    # Core SDK Philosophy and Architecture
    content = [
        "# xovis-sdk - Autonomous Agent Instructions",
        "",
        "> Enterprise-grade Universal Translator for Xovis Hardware.",
        "",
        "## Domain Expertise & Guidelines",
        "For deep architectural context and agent-specific operational rules, refer to:",
        "- [Engineering Guidelines](contributing/engineering_guidelines.md)",
        "- [Agent Instructions](contributing/agent_instructions.md)",
        "",
        "## Core Philosophy",
        "The SDK is strictly quadrifurcated into four planes:",
        "1. **Data Plane (`src/xovis/datapush/`)**: High-frequency (up to 12.5Hz) zero-copy telemetry. Uses optimized serialization and native asyncio.",
        "2. **The Control Plane (`src/xovis/api/`)**: Low-frequency REST configuration. Uses httpx, Pydantic V2, and proactive capability probing.",
        "3. **The Topology & State Plane (`src/xovis/api/device/`)**: Stateful fleet manager. Graph-aware, offline-first persistence, and topology resolution.",
        "4. **The Agentic Layer (`src/xovis/skills/`)**: Universal Tool Adapter exposing SDK methods to LLMs (OpenAI, Anthropic, LangGraph, MCP).",
        "",
        "## Key API Boundaries",
        "- `UnifiedDeviceClient`: Recommended hybrid router client. Automatically performs a fast direct local LAN check before falling back to the secure Cloud HUB proxy tunnel. Supports MAC, IP, and Named resolution with automatic fallback and AmbiguousDeviceNameError handling.",
        "- `DeviceClient`: Local sensor orchestration via direct IP.",
        "- `HubClient`: Fleet-scale cloud orchestration via Xovis HUB.",
        "- `XovisAIToolkit`: Universal Tool Adapter for LLMs. Supports pre-registered adapters (LangChain, CrewAI) dynamically via `toolkit.get_tools(name)` or custom adapters via `toolkit.register_adapter(name, func)`.",
        "- `TopologyManager`: Edge Topology Synthesis (synthesizes `MSGraph` directed graphs).",
        "",
        "## Code Patterns & Common Mistakes",
        "- **Mistake:** Using `orjson` in the Data Plane. **Correction:** Use `json.JSONDecoder().raw_decode()` to handle Xovis's concatenated JSON streams without newlines.",
        "- **Mistake:** Blindly executing physical operations. **Correction:** Check capabilities first (e.g., `if await device.has_wifi:`). Spider NUCs lack physical lenses and will crash if `singlesensor.scene` is accessed.",
        "- **Mistake:** Hub Rate Limits. **Correction:** The Cloud Hub uses Auth0. Share `HubClient` sessions across executions using the async context manager to prevent HTTP 429 token exhaustion.",
        "- **Mistake:** Static file lookup. **Correction:** Always prioritize lookup order starting with `_local_ressources/hub_fleet_state.json` (HUB) and `_local_ressources/device_state.json` (Device) to prevent polling CWD or package defaults.",
        "",
        "## Safety & Congestion Control",
        'High-impact operations (reboots, factory resets, network changes) are protected by `XovisSafetyGuardrail`. To execute a CRITICAL tool, the agent MUST explicitly pass `"confirmation": True` in the tool arguments. Max critical quotas apply per session.',
    ]

    llms_path = docs_dir / "llms.txt"
    # Note: Using explicit write instead of list join to ensure consistency with existing file if needed,
    # but here we want to regenerate it correctly.
    with open(llms_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content) + "\n")
    print(f"Generated {llms_path}")


def generate_llms_full_txt():
    """Generates a comprehensive index for deep context injection.

    This function walks the `src/xovis` directory to build a clean representation
    of the codebase layout, filtering out private internal configurations and
    models, and outputs `llms-full.txt` to the `docs/` directory.
    """
    docs_dir = Path("docs")

    content = [
        "# xovis-sdk - Full Agentic Context",
        "",
        "## SDK Structure",
    ]

    # Simple directory tree for context
    src_dir = Path("src/xovis")
    if src_dir.exists():
        content.append("```")

        # Helper to walk and filter
        def walk_and_filter(current_path, level=0):
            name = current_path.name if level > 0 else "xovis"
            indent = " " * 4 * level
            content.append(f"{indent}{name}/")

            # SPECIAL HANDLING: Hide contents of 'versions' folder in models
            if name == "versions" and "src/xovis/models/device_auto/versions" in current_path.as_posix():
                return

            # SPECIAL HANDLING: Hide specific proprietary auto-generated models
            private_files = {"hub_auto.py", "hub_license_auto.py", "xovis_types.py"}
            if name in private_files and "src/xovis/models" in current_path.as_posix():
                return

            try:
                # Get all entries, sorted: dirs first, then files
                entries = sorted(list(os.scandir(current_path)), key=lambda e: (not e.is_dir(), e.name))

                # Separate dirs and files
                dirs = [e for e in entries if e.is_dir() and e.name != "__pycache__" and not e.name.startswith(".")]
                files = [e for e in entries if not e.is_dir() and e.name.endswith(".py") and not e.name.startswith("__")]

                sub_indent = " " * 4 * (level + 1)

                # Recursively add dirs
                for d in dirs:
                    walk_and_filter(Path(d.path), level + 1)

                # Add files
                for f in files:
                    # Filter out private files in models directory
                    if f.name in private_files and "src/xovis/models" in current_path.as_posix():
                        continue
                    content.append(f"{sub_indent}{f.name}")
            except PermissionError:
                pass

        walk_and_filter(src_dir)
        content.append("```")

    content.append("\n## Key Models & Protocols")
    content.append("- See `src/xovis/models/` for Pydantic V2 schemas.")
    content.append("- See `src/xovis/datapush/sinks.py` for the `XovisSink` protocol.")

    llms_full_path = docs_dir / "llms-full.txt"
    llms_full_path.write_text("\n".join(content), encoding="utf-8")
    print(f"Generated {llms_full_path}")


def generate_llms_small_txt():
    """Generates a smaller, high-level summary for token-efficient agents.

    This function produces a compact summary outlining the core purpose of the SDK,
    the four-plane architecture, and the primary entry classes to help AI agents
    quickly grasp the SDK landscape in token-constrained environments.
    """
    docs_dir = Path("docs")
    content = [
        "# xovis-sdk - High-Level Summary",
        "",
        "## Purpose",
        "Universal Translator for Xovis hardware (Sensors, Spiders, HUB).",
        "",
        "## Planes",
        "1. Data Plane: Datapush telemetry.",
        "2. Control Plane: REST API management.",
        "3. Topology Plane: Fleet orchestration.",
        "4. Agentic Layer: MCP/Tool support.",
        "",
        "## Key Classes",
        "- `UnifiedDeviceClient`: Hybrid local/remote client router.",
        "- `DeviceClient`: IP-based local control.",
        "- `HubClient`: Cloud-based fleet control.",
        "- `XovisAIToolkit`: AI/LLM tool mapping with dynamic adapter support.",
    ]
    llms_small_path = docs_dir / "llms-small.txt"
    llms_small_path.write_text("\n".join(content), encoding="utf-8")
    print(f"Generated {llms_small_path}")


if __name__ == "__main__":
    generate_llms_txt()
    generate_llms_full_txt()
    generate_llms_small_txt()
