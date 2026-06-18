# Public Repository Structure

```plaintext
xovis-sdk/
+- .github
|   +- workflows
|   |   +- ci.yml
|   |   +- docs.yml
|   |   *- publish.yml
|   +- CODEOWNERS
|   *- PULL_REQUEST_TEMPLATE.md
+- bundle_dir
|   *- manifest.json
+- docs
|   +- ai
|   |   +- img
|   |   |   +- ai_privacy.png
|   |   |   +- ai_tool_safety.png
|   |   |   +- fleet_explorer.png
|   |   |   +- fleet_list.png
|   |   |   *- push_studio.png
|   |   +- agentic_layer.md
|   |   +- mcp.md
|   |   *- safety_guardrails.md
|   +- api
|   |   +- python
|   |   |   +- core.md
|   |   |   +- datapush.md
|   |   |   +- device.md
|   |   |   +- hub.md
|   |   |   *- skills.md
|   |   +- hub_device_ref.md
|   |   +- hub_license_ref.md
|   |   +- index.md
|   |   *- reference.md
|   +- architecture
|   |   +- agentic_layer.md
|   |   +- control_plane.md
|   |   +- data_plane.md
|   |   *- state_topology.md
|   +- archive
|   |   *- architecture_v1_consolidated.md
|   +- assets
|   |   *- images
|   |       *- logo.jpg
|   +- contributing
|   |   +- agent_instructions.md
|   |   *- engineering_guidelines.md
|   +- recipes
|   |   *- langgraph_congestion_control.md
|   +- stylesheets
|   |   *- extra.css
|   +- architecture.md
|   +- cli.md
|   +- index.md
|   +- llms-small.txt
|   +- llms.txt
|   +- project_structure.md
|   *- troubleshooting_ai.md
+- examples
|   +- 01_edge_basics.py
|   +- 02_telemetry_pipeline.py
|   +- 03_topology_and_state.py
|   +- 04_fleet_orchestration.py
|   *- README.md
+- scripts
|   +- docs
|   |   +- llms-full.txt
|   |   +- llms-small.txt
|   |   *- llms.txt
|   +- generate_ai_context.py
|   +- prepare_docs.py
|   +- sync_models.py
|   +- sync_project_structure.py
|   *- test_docs.py
+- src
|   +- xovis
|   |   +- api
|   |   |   +- core
|   |   |   |   +- __init__.py
|   |   |   |   +- auth.py
|   |   |   |   +- exceptions.py
|   |   |   |   +- http.py
|   |   |   |   *- tui.py
|   |   |   +- device
|   |   |   |   +- resources
|   |   |   |   |   +- __init__.py
|   |   |   |   |   +- analytics.py
|   |   |   |   |   +- datapush.py
|   |   |   |   |   +- history.py
|   |   |   |   |   +- images.py
|   |   |   |   |   +- itxpt.py
|   |   |   |   |   +- network.py
|   |   |   |   |   +- privacy.py
|   |   |   |   |   +- scene.py
|   |   |   |   |   +- system.py
|   |   |   |   |   +- time_config.py
|   |   |   |   |   +- update.py
|   |   |   |   |   *- users.py
|   |   |   |   +- __init__.py
|   |   |   |   +- cache.py
|   |   |   |   +- client.py
|   |   |   |   +- discovery.py
|   |   |   |   +- models.py
|   |   |   |   +- sync.py
|   |   |   |   *- topology.py
|   |   |   +- hub
|   |   |   |   +- resources
|   |   |   |   |   +- __init__.py
|   |   |   |   |   +- base.py
|   |   |   |   |   +- hub_device.py
|   |   |   |   |   *- hub_license.py
|   |   |   |   +- __init__.py
|   |   |   |   +- cache.py
|   |   |   |   +- client.py
|   |   |   |   *- sync.py
|   |   |   *- __init__.py
|   |   +- datapush
|   |   |   +- __init__.py
|   |   |   +- http_server.py
|   |   |   +- mqtt_client.py
|   |   |   +- sinks.py
|   |   |   +- tcp_client.py
|   |   |   +- tcp_server.py
|   |   |   +- transmission_check.py
|   |   |   +- udp_server.py
|   |   |   *- utils.py
|   |   +- mcp
|   |   |   +- README.md
|   |   |   *- server.py
|   |   +- models
|   |   |   +- device_auto
|   |   |   |   +- versions
|   |   |   |   +- DeviceManagementService.py
|   |   |   |   +- DoorStateService.py
|   |   |   |   +- PassengerCountingService.py
|   |   |   |   *- __init__.py
|   |   |   +- __init__.py
|   |   |   +- device.py
|   |   |   *- hub_device.py
|   |   +- skills
|   |   |   +- README.md
|   |   |   +- __init__.py
|   |   |   +- crewai_adapter.py
|   |   |   +- langchain_adapter.py
|   |   |   *- toolkit.py
|   |   +- tui
|   |   |   +- screens
|   |   |   |   +- ai_privacy.py
|   |   |   |   +- bucket_modal.py
|   |   |   |   +- confirm_modal.py
|   |   |   |   +- device_dashboard.py
|   |   |   |   +- fleet_explorer.py
|   |   |   |   *- scanner_modal.py
|   |   |   +- widgets
|   |   |   |   *- datapush_studio.py
|   |   |   *- app.py
|   |   +- utils
|   |   |   +- __init__.py
|   |   |   +- loop.py
|   |   |   +- privacy.py
|   |   |   *- time.py
|   |   +- __init__.py
|   |   +- cli.py
|   |   +- config.py
|   |   *- device_state.json.example
|   *- __init__.py
+- tests
|   +- api
|   |   +- device
|   |   |   +- __init__.py
|   |   |   +- test_analytics.py
|   |   |   +- test_cache_persistence.py
|   |   |   +- test_cp_datapush_crud.py
|   |   |   +- test_cp_datapush_limits.py
|   |   |   +- test_cp_datapush_stateless.py
|   |   |   +- test_cp_datapush_triggers.py
|   |   |   +- test_cp_licenses.py
|   |   |   +- test_history.py
|   |   |   +- test_itxpt.py
|   |   |   +- test_network.py
|   |   |   +- test_privacy.py
|   |   |   +- test_scene.py
|   |   |   +- test_spider_granularity.py
|   |   |   +- test_system.py
|   |   |   +- test_time.py
|   |   |   +- test_unified_router.py
|   |   |   +- test_update.py
|   |   |   +- test_users.py
|   |   |   *- test_xovistime_integration.py
|   |   +- hub
|   |   |   +- test_hub_devices.py
|   |   |   +- test_hub_licenses.py
|   |   |   *- test_hub_resources_e2e.py
|   |   +- skills
|   |   |   +- test_toolkit_dynamic.py
|   |   |   *- test_toolkit_privacy.py
|   |   +- utils
|   |   |   +- test_privacy_session.py
|   |   |   *- test_time_parser.py
|   |   +- __init__.py
|   |   +- test_cache_complete.py
|   |   +- test_cache_paths.py
|   |   +- test_cli_paths.py
|   |   *- test_routing.py
|   +- datapush
|   |   +- __init__.py
|   |   +- conftest.py
|   |   +- dp_validation_sink.py
|   |   +- test_dp_data_alignment.py
|   |   +- test_dp_matrix_universal.py
|   |   +- test_dp_mqtt_client.py
|   |   +- test_dp_server_compliance.py
|   |   +- test_dp_sink_protocol.py
|   |   *- test_dp_tcp_raw_parsing.py
|   +- mcp
|   |   *- test_mcp_server_privacy.py
|   +- README.md
|   +- __init__.py
|   +- conftest.py
|   +- test_tui_fleet.py
|   +- test_tui_paths.py
|   *- verify_examples.py
+- .env.example
+- .gitignore
+- CONTRIBUTING.md
+- LICENSE
+- README.md
+- manifest.json
+- mkdocs.yml
+- pyproject.toml
+- requirements.txt
+- server.mcpb
+- smithery.yaml
*- uv.lock
```
