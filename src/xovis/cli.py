"""
Xovis SDK - CLI Tools

Operates within the Developer Experience (DX) boundary of the State & Topology Plane.
Provides offline static type generation by parsing serialized HostStateBucket
JSON representations and synthesizing strict Python `typing.Literal` structures.
Features zero-dependency ANSI color output, generation analytics, and dry-run safety.
"""

import argparse
import ast
import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from xovis.api.device.cache import HostStateBucket
from xovis.api.device.client import DeviceClient
from xovis.api.device.discovery import discovery_manager

try:
    from xovis.skills.discovery import SchemaAnalyst

    _HAS_SCHEMA_ANALYST = True
except ImportError:
    SchemaAnalyst = None
    _HAS_SCHEMA_ANALYST = False
from xovis.utils.loop import setup_optimal_loop

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

setup_optimal_loop()


# --- CLI Formatter for High-End DX ---
class CLIFormatter(logging.Formatter):
    """Custom logging formatter injecting ANSI color codes for terminal UX."""

    COLORS = {
        logging.DEBUG: "\033[90m",  # Gray
        logging.INFO: "\033[96m",  # Cyan
        logging.WARNING: "\033[93m",  # Yellow
        logging.ERROR: "\033[91m",  # Red
        logging.CRITICAL: "\033[1;91m",  # Bold Red
    }
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    FORMAT = "%(message)s"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        record.msg = f"{color}◆ {record.msg}{self.RESET}"
        return logging.Formatter(self.FORMAT).format(record)


class GroupedHelpFormatter(argparse.HelpFormatter):
    """Custom formatter to group subcommands in the help output."""

    def _format_action(self, action: argparse.Action) -> str:
        parts = super()._format_action(action)
        if action.nargs == argparse.PARSER:
            # Inject grouping headers into the subparser list
            lines = parts.splitlines()
            new_lines = []

            groups = {
                "Developer Experience (DX) & AI": [
                    "generate-types",
                    "generate-rules",
                    "docs",
                    "discovery",
                ],
                "Hardware Interaction & Provisioning": ["probe", "sync-models", "datapush"],
                "Fleet & Cloud Services": ["hub", "mcp", "setup", "ui"],
            }

            processed_groups = set()

            for line in lines:
                # Check if this line is a subcommand
                cmd_match = False
                for group_name, commands in groups.items():
                    if any(line.strip().startswith(cmd) for cmd in commands):
                        if group_name not in processed_groups:
                            new_lines.append(f"\n{F.BOLD}{group_name}:{F.RESET}")
                            processed_groups.add(group_name)
                        cmd_match = True
                        break

                if not cmd_match and "Available commands" in line:
                    continue  # Skip the default header

                new_lines.append(line)

            return "\n".join(new_lines) + "\n"
        return parts


logger = logging.getLogger("xovis-cli")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(CLIFormatter())
logger.addHandler(handler)

F = CLIFormatter


def extract_names(items: list[Any]) -> tuple[list[str], int]:
    """
    Extracts unique names from cached resources and counts them.

    Args:
        items (List[Any]): A list of Pydantic resource models or dictionaries.

    Returns:
        Tuple[List[str], int]: Sorted list of unique names and the total count.
    """
    names = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name")
        else:
            name = getattr(item, "name", None)
        if name and isinstance(name, str):
            names.append(name)
    unique_names = sorted(list(set(names)))
    return unique_names, len(unique_names)


def generate_literal(type_name: str, names: list[str]) -> str:
    """
    Generates a strict typing.Literal string definition.

    Args:
        type_name (str): Target Python type alias.
        names (List[str]): Extracted names to inject.

    Returns:
        str: Raw Python code defining the Literal type.
    """
    if not names:
        return f"{type_name}: TypeAlias = str\n"

    literals = ", ".join(json.dumps(name) for name in names)
    return f"{type_name}: TypeAlias = Literal[{literals}]\n"


def print_receipt(stats: dict[str, int]) -> None:
    """Prints a formatted analytics table to the terminal."""
    total = sum(stats.values())
    print(f"\n{F.BOLD}  Generation Analytics{F.RESET}")
    print("  " + "─" * 30)
    for category, count in stats.items():
        if count > 0:
            print(f"  {category:<20} {F.GREEN}+{count}{F.RESET}")
    print("  " + "─" * 30)
    print(f"  {F.BOLD}Total Entities Typed:  {total}{F.RESET}\n")


def generate_types(source_path: str, output_path: str, dry_run: bool = False, device: str = None, via_hub: bool = False) -> None:
    """
    Parses offline cache, tracks analytics, and safely generates Literal types.

    Args:
        source_path (str): File path to HostStateBucket JSON.
        output_path (str): Target file path for the generated Python module.
        dry_run (bool): If True, parses and analyzes without writing to disk.
        device (str, optional): Target IP or MAC address to pull state from.
        via_hub (bool): If True, route connection through the Xovis Hub tunnel.
    """
    if device:
        import asyncio
        import ipaddress

        from xovis.api.device.client import DeviceClient
        from xovis.api.hub.client import HubClient
        
        def is_ip_address(val: str) -> bool:
            try:
                ipaddress.ip_address(val)
                return True
            except ValueError:
                return False

        async def fetch_state():
            """Authenticates with the device and exports its current state to a JSON bucket."""
            if is_ip_address(device):
                if via_hub:
                    raise ValueError("Hub routing requires a MAC address, not an IP.")
                logger.info(f"Connecting to {device} to fetch live state...")
                async with DeviceClient(device, "admin", "pass") as client:
                    await client.cache.sync()
                    client.cache.export_to_file(source_path)
                    logger.info(f"Live state exported to {source_path}")
            else:
                if via_hub:
                    logger.info(f"Connecting to hub to tunnel to device {device}...")
                    async with HubClient() as hub:
                        async with await hub.connect_device(device) as client:
                            await client.cache.sync()
                            client.cache.export_to_file(source_path)
                            logger.info(f"Live state of {device} exported to {source_path} via HUB")
                else:
                    # Local LAN connection via MAC discovery
                    from xovis.api.device.network_discovery import NetworkDiscoveryService
                    logger.info(f"Discovering local IP for MAC {device}...")
                    local_ip = await NetworkDiscoveryService.resolve_mac_to_ip(device)
                    
                    if not local_ip:
                        raise ValueError(f"Could not discover device with MAC {device} on the local network. Ensure it is powered on and reachable.")
                        
                    logger.info(f"Resolved MAC {device} to IP {local_ip}. Connecting to fetch live state...")
                    async with DeviceClient(local_ip, "admin", "pass") as client:
                        await client.cache.sync()
                        client.cache.export_to_file(source_path)
                        logger.info(f"Live state exported to {source_path}")

        try:
            asyncio.run(fetch_state())
        except Exception as e:
            logger.error(f"Failed to fetch live state: {e}")
            return

    source_file = Path(source_path).resolve()
    if not source_file.exists():
        logger.error(f"Source cache file not found: {source_file}")
        return

    try:
        with open(source_file, encoding="utf-8") as f:
            data = f.read()
        bucket = HostStateBucket.model_validate_json(data)
    except Exception as e:
        logger.error(f"Failed to parse offline cache: {e}")
        return

    singlesensor = bucket.contexts.get("singlesensor")
    ms_contexts = [ctx for key, ctx in bucket.contexts.items() if key != "singlesensor"]
    stats = {}

    def get_ms_items(attr: str) -> list[Any]:
        """
        Gathers a specific resource type across all multisensor contexts.

        Args:
            attr (str): The attribute name to collect (e.g., 'agents', 'zones').

        Returns:
            List[Any]: A flattened list of resources from all virtual contexts.
        """
        items = []
        for ctx in ms_contexts:
            val = getattr(ctx, attr, [])
            if val:
                items.extend(val)
        return items

    def process(category: str, items: list[Any], prefix: str, out_list: list[str]) -> None:
        """
        Extracts entity names, generates Literal types, and updates analytics.

        Args:
            category (str): The resource category name (e.g., 'Agent').
            items (List[Any]): The list of resource models to process.
            prefix (str): Prefix for the generated type name (e.g., 'Singlesensor').
            out_list (List[str]): The accumulator for generated code lines.
        """
        names, count = extract_names(items)
        out_list.append(generate_literal(f"{prefix}{category}Name", names))
        stats[f"{prefix} {category}"] = count

    out = [
        '"""',
        "AUTO-GENERATED FILE. DO NOT EDIT DIRECTLY.",
        "Generated by xovis-cli from an offline hardware cache.",
        '"""',
        "from typing import Literal",
        "try:",
        "    from typing import TypeAlias",
        "except ImportError:",
        "    from typing_extensions import TypeAlias\n",
    ]

    logger.info("Extracting topological entities...")

    if singlesensor:
        out.append("# --- Singlesensor Context Types ---")
        process("Agent", singlesensor.agents, "Singlesensor", out)
        process("Connection", singlesensor.connections, "Singlesensor", out)
        process("Zone", singlesensor.zones, "Singlesensor", out)
        process("Line", singlesensor.lines, "Singlesensor", out)
        process("Logic", singlesensor.logics, "Singlesensor", out)
        process("Modifier", singlesensor.modifiers, "Singlesensor", out)
        process("Counter", singlesensor.counters, "Singlesensor", out)
        process("Mask", singlesensor.masks, "Singlesensor", out)
        process("Layer", singlesensor.layers, "Singlesensor", out)
        out.append("\n")

    if ms_contexts:
        out.append("# --- Multisensor Context Types ---")
        process("Agent", get_ms_items("agents"), "Multisensor", out)
        process("Connection", get_ms_items("connections"), "Multisensor", out)
        process("Zone", get_ms_items("zones"), "Multisensor", out)
        process("Line", get_ms_items("lines"), "Multisensor", out)
        process("Logic", get_ms_items("logics"), "Multisensor", out)
        process("Modifier", get_ms_items("modifiers"), "Multisensor", out)
        process("Counter", get_ms_items("counters"), "Multisensor", out)
        process("Mask", get_ms_items("masks"), "Multisensor", out)
        process("Layer", get_ms_items("layers"), "Multisensor", out)

    # Global Context Names for Discovery
    context_names = sorted(list(bucket.contexts.keys()))
    out.append("\n# --- Global Context Names ---")
    process("Context", [{"name": n} for n in context_names], "Global", out)

    print_receipt(stats)

    if dry_run:
        logger.warning("Dry-run active. File writes bypassed.")
        return

    target = Path(output_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    with open(target, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    logger.info(f"Synthesized static types at {F.BOLD}{target.name}{F.RESET}")

    try:
        subprocess.run(["ruff", "format", str(target)], check=True, capture_output=True)
        logger.info("Ruff autonomous formatting complete.")
    except FileNotFoundError:
        logger.warning("Ruff is not in PATH. Skipping formatting.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ruff formatting failed: {e.stderr.decode()}")


def scan_markdown_files(root_dir: str) -> list[str]:
    """Scans the root directory recursively for Markdown files.

    Args:
        root_dir: The repository root path to scan.

    Returns:
        A list of relative paths to Markdown files.
    """
    markdown_files = []
    ignored_dirs = {".venv", "venv", "env", ".git", "node_modules", "build", "dist", "site", "__pycache__", ".junie_cache"}
    for root, dirs, files_in_dir in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files_in_dir:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_dir)
                normalized_path = rel_path.replace(os.path.sep, "/")
                markdown_files.append(normalized_path)
    return sorted(markdown_files)


def serve_docs(host: str, port: int) -> None:
    """Builds and serves local SDK Markdown documentation via an HTTP server.

    Args:
        host: Host address to bind the server to.
        port: Port to run the HTTP server on.
    """
    import http.server
    import subprocess
    import sys
    import urllib.parse
    import webbrowser

    try:
        import mkdocs
    except ImportError:
        logger.error(f'Documentation dependencies are missing. Please install with: {F.BOLD}pip install "xovis-sdk[docs]"{F.RESET}')
        return

    root_dir = os.getcwd()

    try:
        from scripts.prepare_docs import prepare_openapi_assets

        prepare_openapi_assets()
    except Exception as e:
        logger.warning(f"Failed to prepare OpenAPI assets: {e}")

    logger.info("Building documentation using MkDocs...")
    try:
        subprocess.run([sys.executable, "-m", "mkdocs", "build"], capture_output=True, text=True, check=True)
        logger.info("Documentation built successfully.")
    except Exception as e:
        logger.error(f"Failed to build documentation with MkDocs: {e}")
        if hasattr(e, "stderr") and e.stderr:
            logger.error(f"MkDocs build error: {e.stderr}")

    site_dir = os.path.join(root_dir, "site")

    class DocsHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        """HTTP handler serving MkDocs built site."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=site_dir, **kwargs)

        def translate_path(self, path: str) -> str:
            """Translates request paths to site directory.

            Args:
                path: Requested URL path.

            Returns:
                The physical resolved file path.
            """
            parsed = urllib.parse.urlparse(path)
            clean_path = parsed.path
            if clean_path in ("/", "/index.html"):
                return os.path.join(site_dir, "index.html")

            rel_path = urllib.parse.unquote(clean_path.lstrip("/"))
            full_path = os.path.join(site_dir, rel_path)
            if os.path.commonpath([site_dir, os.path.abspath(full_path)]) == site_dir:
                return full_path

            return super().translate_path(path)

        def log_message(self, format_str: str, *args: Any) -> None:
            """Suppress default stdout/stderr logging of HTTP requests."""
            pass

    server_address = (host, port)
    try:
        httpd = http.server.ThreadingHTTPServer(server_address, DocsHTTPRequestHandler)
    except Exception as e:
        logger.error(f"Failed to start server on {host}:{port}: {e}")
        return

    logger.info(f"Serving local SDK documentation at {F.BOLD}http://{host}:{port}{F.RESET}")
    url = f"http://localhost:{port}" if host in ("127.0.0.1", "0.0.0.0") else f"http://{host}:{port}"  # nosec B104
    webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Local documentation server stopped.")
    finally:
        httpd.server_close()


def check_doc_coverage(src_path: str = "src") -> float:
    """
    Scans src/ for missing Google-style docstrings in public classes and methods.

    Returns:
        float: Coverage percentage (0.0 to 100.0).
    """
    total_public = 0
    with_doc = 0

    for root, _, files in os.walk(src_path):
        for file in files:
            if not file.endswith(".py") or file.startswith("test_"):
                continue

            file_path = os.path.join(root, file)
            # print(f"Checking {file_path}")
            try:
                with open(file_path, encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Only check public items
                        if node.name.startswith("_") and not (node.name.startswith("__") and node.name.endswith("__")):
                            continue

                        total_public += 1
                        if ast.get_docstring(node):
                            with_doc += 1
            except Exception:
                continue

    coverage = (with_doc / total_public * 100) if total_public > 0 else 100.0
    print(f"\n{F.BOLD}  Documentation Compliance Check{F.RESET}")
    print("  " + "─" * 30)
    color = F.GREEN if coverage > 90 else "\033[93m" if coverage > 70 else F.COLORS[logging.ERROR]
    print(f"  Public Docstrings:   {with_doc}/{total_public}")
    print(f"  Docstring Coverage:  {color}{coverage:.1f}%{F.RESET}")
    status = f"{F.GREEN}[PASS]{F.RESET}" if coverage >= 100 else f"{F.COLORS[logging.ERROR]}[FAIL]{F.RESET}"
    print(f"  Status:              {status}\n")
    return coverage


def probe_device(host: str, password: str = "pass") -> None:
    """Probes a device and prints a status summary."""
    import asyncio

    async def run_probe():
        """Connects to the device, probes hardware info, and displays a status report."""
        logger.info(f"Probing hardware at {F.BOLD}{host}{F.RESET}...")
        async with DeviceClient(host, "admin", password) as client:
            info = client._device_info
            fw = client.fw_version
            print(f"\n{F.BOLD}  Hardware Status: {host}{F.RESET}")
            print("  " + "─" * 30)
            print(f"  Model:        {info.get('type', 'Unknown')}")
            print(f"  Firmware:     {fw}")
            print(f"  Serial:       {info.get('serial', 'Unknown')}")
            print(f"  MAC:          {info.get('mac', 'Unknown')}")

            # Check multisensors
            ms = await client.system.get_multisensors()
            print(f"  Multisensors: {len(ms)}")

            # Capability probe
            ana = await client.has_analytics
            print(f"  Analytics:    {F.GREEN if ana else F.COLORS[logging.ERROR]}{'ENABLED' if ana else 'OFF'}{F.RESET}")
            print("  " + "─" * 30 + "\n")

    try:
        asyncio.run(run_probe())
    except Exception as e:
        logger.error(f"Probe failed: {e}")


def sync_models(device_ip: str, version_tag: str) -> None:
    """Regenerates Pydantic models from a live device while preserving docstrings."""
    from scripts.sync_models import sync_api

    logger.info(f"Starting model synchronization for {F.BOLD}{version_tag}{F.RESET}...")
    try:
        sync_api(device_ip, version_tag)
        logger.info(f"Models synchronized successfully for {version_tag}")
    except Exception as e:
        logger.error(f"Sync failed: {e}")


def start_mcp(log_file: str | None = None, daemon: bool = False) -> None:
    """Launches the Xovis MCP Server."""
    try:
        import mcp
    except ImportError:
        logger.error(f'MCP dependencies are missing. Please install with: {F.BOLD}pip install "xovis-sdk[mcp]"{F.RESET}')
        return

    cmd = [sys.executable, "-m", "xovis.mcp.server"]
    if log_file:
        cmd.extend(["--log-file", log_file])

    sys.stderr.write("Initializing Xovis MCP Server...\n")
    try:
        if daemon:
            sys.stderr.write("Starting in daemon mode...\n")
            if os.name == "nt":
                # Create detached process on Windows
                subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    cmd,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            sys.stderr.write("MCP Server detached and running in background.\n")
        else:
            subprocess.run(cmd)
    except KeyboardInterrupt:
        logger.info("MCP Server stopped.")
    except Exception as e:
        logger.error(f"MCP Server crash: {e}")


def start_setup() -> None:
    """Launches the guided setup wizard."""
    try:
        from xovis.api.core.tui import SetupWizard
    except ImportError:
        logger.error(f'TUI dependencies are missing. Please install with: {F.BOLD}pip install "xovis-sdk[tui]"{F.RESET}')
        return

    wizard = SetupWizard()
    wizard.run()


async def start_warmup(host: str, username: str = "admin", password: str = "pass", force: bool = False) -> None:
    """Launches the hardware warmup synchronization."""
    from xovis.api.device.sync import HardwareSyncer

    syncer = HardwareSyncer(host, username, password)
    success = await syncer.warmup(force=force)
    if success:
        print(f"\n{F.GREEN}[SUCCESS]{F.RESET} Hardware warmup for {host} completed.")
    else:
        print(f"\n{F.RED}[FAILED]{F.RESET} Hardware warmup for {host} failed. Check logs.")


async def start_hub_warmup(client_id: str = None, client_secret: str = None, force: bool = False) -> None:
    """Launches the Xovis HUB warmup synchronization."""
    from xovis.api.hub.sync import HubSyncer

    syncer = HubSyncer(client_id=client_id, client_secret=client_secret)
    success = await syncer.warmup(force=force)
    if success:
        print(f"\n{F.GREEN}[SUCCESS]{F.RESET} Xovis HUB warmup completed.")
    else:
        print(f"\n{F.RED}[FAILED]{F.RESET} Xovis HUB warmup failed. Check logs.")


def start_tui() -> None:
    """Launches the Xovis Open SDK Mission Control TUI."""
    try:
        from xovis.tui.app import XovisMissionControl
    except ImportError:
        logger.error(f'TUI dependencies are missing. Please install with: {F.BOLD}pip install "xovis-sdk[tui]"{F.RESET}')
        return

    app = XovisMissionControl()
    app.run()


def start_datapush_studio(
    port: int,
    protocol: str,
    host: str = None,
    agent_type: str = "LIVE_DATA",
    password: str = "pass",
) -> None:
    """Launches the Datapush Studio TUI."""
    try:
        from xovis.datapush.transmission_check import DatapushStudioApp
    except ImportError:
        logger.error(f'TUI dependencies are missing. Please install with: {F.BOLD}pip install "xovis-sdk[tui]"{F.RESET}')
        return

    app = DatapushStudioApp(device_id=host or "", port=port, protocol=protocol, agent_type=agent_type, password=password)
    app.run()


async def hub_list_devices(
    client_id: str = None,
    client_secret: str = None,
    mac: str = None,
    name: str = None,
    customer: str = None,
    group: str = None,
    status: str = None,
) -> None:
    """
    Connects to the Xovis HUB and prints a table of registered devices.
    """
    from xovis.api.hub.client import HubClient

    logger.info("Connecting to Xovis HUB Cloud...")
    try:
        async with HubClient(client_id=client_id, client_secret=client_secret) as hub:
            # We use the synchronized cache for listing
            devices = hub.cache._state.devices

            # Apply filters
            filtered = []
            for d in devices:
                d_mac = d.id.root if hasattr(d.id, "root") else d.id
                d_status = d.device_status.value if d.device_status else "Unknown"

                if mac and mac.lower() not in d_mac.lower():
                    continue
                if name and name.lower() not in (d.device_name or "").lower():
                    continue
                if customer and customer.lower() != (d.customer or "").lower():
                    continue
                if group and group.lower() != (d.device_group or "").lower():
                    continue
                if status and status.upper() != d_status.upper():
                    continue

                filtered.append(d)

            # Table configuration
            cols = [
                ("MAC Address", 20),
                ("Name", 25),
                ("Group", 20),
                ("Customer", 20),
                ("Status", 10),
            ]

            # Calculate total width (sum of column widths + spacers)
            # We have 5 columns, so 4 gaps between them. We use 2 spaces as gap.
            # Plus 2 leading spaces for the table margin.
            sum(c[1] for c in cols) + (len(cols) - 1) * 2

            header_row = "  " + "".join(f"{name:<{width}}  " for name, width in cols).rstrip()
            sep = "  " + "─" * (len(header_row.strip()) - 2)

            print(f"\n{F.BOLD}  Xovis HUB Fleet Inventory{F.RESET}")
            if any([mac, name, customer, group, status]):
                filters = []
                if mac:
                    filters.append(f"MAC~{mac}")
                if name:
                    filters.append(f"Name~{name}")
                if customer:
                    filters.append(f"Customer={customer}")
                if group:
                    filters.append(f"Group={group}")
                if status:
                    filters.append(f"Status={status}")
                print(f"  {F.BOLD}Filters:{F.RESET} {', '.join(filters)}")

            print(sep)
            print(header_row)
            print(sep)

            for d in filtered:
                d_mac = d.id.root if hasattr(d.id, "root") else d.id
                d_name = d.device_name or "Unknown"
                d_group = d.device_group or "N/A"
                d_customer = d.customer or "N/A"
                d_status = d.device_status.value if d.device_status else "Unknown"

                # Simple color coding for status
                status_color = F.GREEN if d_status.lower() == "online" else F.RESET
                if d_status.lower() == "offline":
                    status_color = F.BOLD + "\033[90m"  # Dim

                row = (
                    f"  {d_mac:<20}  "
                    f"{d_name[:24] if len(d_name) > 24 else d_name:<25}  "
                    f"{d_group[:19] if len(d_group) > 19 else d_group:<20}  "
                    f"{d_customer[:19] if len(d_customer) > 19 else d_customer:<20}  "
                    f"{status_color}{d_status:<10}{F.RESET}"
                )
                print(row)

            print(sep)
            print(f"  {F.BOLD}Total Devices:{F.RESET} {len(filtered)} (out of {len(devices)})\n")

    except Exception as e:
        logger.error(f"Failed to fetch fleet inventory: {e}")


def generate_rules(output_path: str = ".cursorrules") -> None:
    """Generates an agent rulebook injecting SDK architectural constraints."""
    rules = [
        "# xovis-sdk - Agent Rulebook",
        "",
        "## Architectural Constraints",
        "1. **Quadrifurcation**: Respect the four planes (Data, Control, State/Topology, and Agentic Layer). Never mix patterns across them.",
        "2. **Zero-Copy Data Plane**: No Pydantic in `src/xovis/datapush/`. Use `struct.pack`.",
        "3. **Max-Docstring**: Every public method MUST have a Google-style docstring.",
        "4. **Pydantic V2**: Use `.model_dump(mode='json', exclude_unset=True)` for API payloads.",
        "5. **Async Contexts**: Always use `UnifiedDeviceClient`, `DeviceClient`, and `HubClient` as async context managers.",
        "",
        "## Domain Context",
        "- `UnifiedDeviceClient`: Recommended primary hybrid router client for all device interactions (IP, MAC, or Name resolution).",
        "- `singlesensor`: Physical device context (sensor w. lenses).",
        "- `multisensors`: Virtual stitched environment context.",
        "- `HardwareNotSupportedError`: Raise when accessing `singlesensor` on a Spider NUC.",
    ]
    target = Path(output_path).resolve()
    target.write_text("\n".join(rules), encoding="utf-8")
    logger.info(f"Generated agent rulebook at {F.BOLD}{target.name}{F.RESET}")


async def run_discovery_analysis(analyze: bool = False, apply: bool = False):
    """
    Handles the internal discovery analysis loop.
    """
    if not discovery_manager.persist_path.exists():
        logger.warning("No discovery delta found. Run a sync with XOVIS_DISCOVERY_MODE=1 first.")
        return

    if analyze:
        logger.info(f"{F.BOLD}Analyzing firmware drift...{F.RESET}")
        if not _HAS_SCHEMA_ANALYST:
            logger.error(f"{F.BOLD}Discovery Analysis Failed:{F.RESET} The SchemaAnalyst skill is internal-only and not available in this release.")
            return
        analyst = SchemaAnalyst()
        bridge_path = Path(__file__).parent / "models" / "device.py"
        proposal = await analyst.analyze_delta(discovery_manager.persist_path, bridge_path)
        print(f"\n{F.GREEN}--- Discovery Proposal ---{F.RESET}")
        print(proposal)
        print(f"{F.GREEN}-------------------------{F.RESET}\n")

        if apply:
            logger.info("Applying updates to bridge models...")
            analyst.apply_updates(proposal, bridge_path)
    else:
        # Just show the current delta
        with open(discovery_manager.persist_path) as f:
            delta = json.load(f)
            print(json.dumps(delta, indent=4))


def main() -> None:
    """
    Command-line interface entry point.
    """
    package_dir = Path(__file__).parent.resolve()
    default_output = str(package_dir / "models" / "xovis_types.py")

    local_resources_dir = Path("_local_resources")
    states_dir = local_resources_dir / "states"
    resolved_default_source = None
    if (states_dir / "hub_fleet_state.json").exists():
        resolved_default_source = str(states_dir / "hub_fleet_state.json")
    elif (local_resources_dir / "hub_fleet_state.json").exists():
        resolved_default_source = str(local_resources_dir / "hub_fleet_state.json")
    elif (states_dir / "device_state.json").exists():
        resolved_default_source = str(states_dir / "device_state.json")
    elif (local_resources_dir / "device_state.json").exists():
        resolved_default_source = str(local_resources_dir / "device_state.json")
    else:
        state_files = sorted(list(states_dir.glob("state_*.json"))) if states_dir.exists() else []
        if not state_files and local_resources_dir.exists():
            state_files = sorted(list(local_resources_dir.glob("state_*.json")))
        if state_files:
            resolved_default_source = str(state_files[0])
        elif Path("device_state.json").exists():
            resolved_default_source = str(Path("device_state.json").resolve())
        else:
            resolved_default_source = str(package_dir / "device_state.json")

    parser = argparse.ArgumentParser(
        description=f"{F.BOLD}Xovis SDK CLI - Enterprise Developer Tools{F.RESET}",
        epilog="Empowering the State & Topology Plane with static typing and compliance checks.",
        formatter_class=GroupedHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- DX & AI Group ---

    # Generate Types Command
    type_parser = subparsers.add_parser(
        "generate-types",
        aliases=["gen-types"],
        help="[DX] Synthesize strict Python Literal types from hardware state.",
    )
    type_parser.add_argument(
        "--source",
        type=str,
        default=resolved_default_source,
        help="Path to the exported HostStateBucket JSON file.",
    )
    type_parser.add_argument(
        "--device",
        type=str,
        help="Optional: Pull state from this device (IP or MAC) before generating.",
    )
    type_parser.add_argument(
        "--via-hub",
        action="store_true",
        help="Optional: Route connection through the Xovis Hub tunnel.",
    )
    type_parser.add_argument(
        "--output",
        type=str,
        default=default_output,
        help="Path to the output Python file.",
    )
    type_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the cache and print analytics without writing files.",
    )

    # Generate Rules Command
    subparsers.add_parser(
        "generate-rules",
        aliases=["gen-rules"],
        help="[AI] Generate .cursorrules/rulebook with SDK architectural constraints.",
    )

    # Docs Command Group
    docs_parser = subparsers.add_parser(
        "docs",
        help="[DX] SDK documentation management (Requires: [docs]).",
    )
    docs_subparsers = docs_parser.add_subparsers(dest="docs_command", help="Docs subcommands")

    # 1. check-docstrings subcommand
    docs_subparsers.add_parser(
        "check-docstrings",
        help="Verify public docstring coverage and standard compliance ('The Receipt').",
    )

    # 2. serve subcommand
    serve_parser = docs_subparsers.add_parser(
        "serve",
        help="Scan, build, and serve local SDK Markdown documentation (Requires: [docs]).",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the HTTP server on (default: 8000).",
    )
    serve_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind the server to (default: 127.0.0.1).",
    )

    # Discovery Command
    discovery_parser = subparsers.add_parser("discovery", help="[DX] Analyze firmware drift and identify unknown API fields (internal).")
    discovery_parser.add_argument("--analyze", action="store_true", help="Perform agentic semantic analysis.")
    discovery_parser.add_argument("--apply", action="store_true", help="Apply proposed updates (Internal Only).")

    # --- Hardware Group ---

    # Probe Device Command
    probe_parser = subparsers.add_parser("probe", help="[HW] Quick hardware status check and capability discovery.")
    probe_parser.add_argument("host", type=str, help="Device IP address.")
    probe_parser.add_argument("--pass", dest="password", type=str, default="pass", help="Password.")

    # Sync Models Command
    sync_parser = subparsers.add_parser("sync-models", help="[HW] Synchronize Pydantic models with specific firmware version tags.")
    sync_parser.add_argument("host", type=str, help="Device IP address.")
    sync_parser.add_argument("tag", type=str, help="Version tag (e.g., v5_9_2).")

    # Warmup Command
    warmup_parser = subparsers.add_parser(
        "warmup",
        help="[HW] Perform hardware sync: download OpenAPI schemas and samples from a real device.",
    )
    warmup_parser.add_argument("host", type=str, help="Device IP address.")
    warmup_parser.add_argument("--user", type=str, default="admin", help="Username (default: admin).")
    warmup_parser.add_argument("--pass", dest="password", type=str, default="pass", help="Password (default: pass).")
    warmup_parser.add_argument("--force", action="store_true", help="Force overwrite existing local resources.")

    # HUB Warmup Command
    hub_warmup_parser = subparsers.add_parser(
        "warmup-hub",
        help="[HUB] Perform HUB cloud sync: download HUB OpenAPI schemas and fleet state.",
    )
    hub_warmup_parser.add_argument("--client-id", type=str, help="HUB Client ID.")
    hub_warmup_parser.add_argument("--client-secret", type=str, help="HUB Client Secret.")
    hub_warmup_parser.add_argument("--force", action="store_true", help="Force overwrite existing local resources.")

    # Datapush Studio Command
    datapush_parser = subparsers.add_parser(
        "datapush",
        aliases=["studio"],
        help="[DP] Launch TUI for real-time Data Plane telemetry visualization (Requires: [tui]).",
    )
    datapush_parser.add_argument("--port", type=int, default=9000, help="Listen port (default: 9000).")
    datapush_parser.add_argument(
        "--protocol",
        choices=["TCP", "UDP", "HTTP"],
        default="TCP",
        help="Transport protocol to use.",
    )
    datapush_parser.add_argument(
        "--agent-type",
        choices=["LIVE_DATA", "LOGICS", "STATUS"],
        default="LIVE_DATA",
        help="The type of DataPush agent to provision (default: LIVE_DATA).",
    )
    datapush_parser.add_argument("--pass", dest="password", type=str, default="pass", help="Password (default: pass).")
    datapush_parser.add_argument("--host", type=str, help="Optional: Sensor IP for auto-provisioning.")

    # --- Services Group ---

    # Hub Command
    hub_parser = subparsers.add_parser("hub", help="[CLOUD] Orchestrate Xovis HUB Cloud fleet operations.")
    hub_subparsers = hub_parser.add_subparsers(dest="hub_command", help="Hub actions")

    hub_list_parser = hub_subparsers.add_parser("list-devices", help="List all devices in the cloud fleet.")
    hub_list_parser.add_argument("--client-id", type=str, help="Xovis HUB Client ID.")
    hub_list_parser.add_argument("--client-secret", type=str, help="Xovis HUB Client Secret.")
    hub_list_parser.add_argument("--mac", type=str, help="Filter by MAC address (substring).")
    hub_list_parser.add_argument("--name", type=str, help="Filter by device name (substring).")
    hub_list_parser.add_argument("--customer", type=str, help="Filter by customer name (exact).")
    hub_list_parser.add_argument("--group", type=str, help="Filter by device group (exact).")
    hub_list_parser.add_argument("--status", choices=["ONLINE", "OFFLINE"], help="Filter by connection status.")

    # MCP Command
    mcp_parser = subparsers.add_parser("mcp", help="[AI] Launch the Xovis MCP Server for Claude/Cursor integration (Requires: [mcp]).")
    mcp_parser.add_argument("--log-file", type=str, help="Optional path to a log file for the MCP Server.")
    mcp_parser.add_argument("--daemon", action="store_true", help="Start the MCP Server in the background as a daemon.")

    # Setup Command
    subparsers.add_parser("setup", help="[DX] Launch the guided SDK setup wizard (Requires: [tui]).")

    # UI Command
    subparsers.add_parser("ui", help="[DX] Launch Xovis Mission Control (Stateful Fleet TUI) (Requires: [tui]).")

    args = parser.parse_args()

    if args.command in ["generate-types", "gen-types"]:
        # Support legacy direct call without subcommand
        source = getattr(args, "source", resolved_default_source)
        output = getattr(args, "output", default_output)
        dry_run = getattr(args, "dry_run", False)
        device = getattr(args, "device", None)
        via_hub = getattr(args, "via_hub", False)
        generate_types(source, output, dry_run=dry_run, device=device, via_hub=via_hub)
    elif args.command is None:
        parser.print_help()
    elif args.command in ["generate-rules", "gen-rules"]:
        generate_rules()
    elif args.command == "docs":
        if getattr(args, "docs_command", None) == "check-docstrings":
            check_doc_coverage()
        elif getattr(args, "docs_command", None) == "serve":
            serve_docs(args.host, args.port)
        else:
            docs_parser.print_help()
    elif args.command == "probe":
        probe_device(args.host, args.password)
    elif args.command == "sync-models":
        sync_models(args.host, args.tag)
    elif args.command == "warmup":
        asyncio.run(start_warmup(args.host, args.user, args.password, args.force))
    elif args.command == "warmup-hub":
        asyncio.run(start_hub_warmup(args.client_id, args.client_secret, args.force))
    elif args.command == "mcp":
        start_mcp(getattr(args, "log_file", None), getattr(args, "daemon", False))
    elif args.command == "setup":
        start_setup()
    elif args.command == "ui":
        start_tui()
    elif args.command == "discovery":
        asyncio.run(run_discovery_analysis(args.analyze, args.apply))
    elif args.command == "hub":
        if args.hub_command == "list-devices":
            asyncio.run(
                hub_list_devices(
                    client_id=args.client_id,
                    client_secret=args.client_secret,
                    mac=args.mac,
                    name=args.name,
                    customer=args.customer,
                    group=args.group,
                    status=args.status,
                )
            )
        else:
            hub_parser.print_help()
    elif args.command in ["datapush", "studio"]:
        start_datapush_studio(
            args.port,
            args.protocol,
            getattr(args, "host", None),
            getattr(args, "agent_type", "LIVE_DATA"),
            getattr(args, "password", "pass"),
        )


if __name__ == "__main__":
    main()
