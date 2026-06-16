# Troubleshooting AI Implementations

When providing the `xovis-sdk` to autonomous agents (like Claude or GPT-5.5), you may encounter specific architectural failure modes. Ensure your agent prompts or instructions account for these strict parameters.

### 1. HTTP 403 Forbidden (Privacy & WAF)
**Symptom:** The agent attempts to fetch analytics or historical data, but the API rejects it with an HTML-formatted error.
**Cause:** This indicates the **Xovis HUB Web Application Firewall (WAF)** or the **Edge Privacy Mode** is actively blocking the request. High-security tenants or sensors set to Privacy Mode 3/4 will aggressively reject observation.
**Solution:** Instruct the agent to check `get_privacy_state`. If the privacy mode is 3 or 4, or if `remote_access` is disabled, the agent must report: *"Access Restricted: Cloud Proxy Firewall or Strict Privacy Mode is blocking data extraction."*

### 2. HTTP 429 Rate Limit Exhaustion (Cloud Hub)
**Symptom:** Operations against the Hub start returning strict rate limit errors.
**Cause:** The agent is dynamically instantiating `HubClient` objects inside a loop, requesting a new Auth0 token on every iteration.
**Solution:** Force the agent to use the asynchronous context manager (`async with HubClient(...) as hub:`) and pass the initialized client or Toolkit down through the execution chain. The SDK now implements **Adaptive Pacing** (1.0s delay for Cloud) to mitigate this.

### 3. PermissionError: "Tool is CRITICAL"
**Symptom:** The agent fails to execute a tool like `factory_reset` or `clear_sensor_db`.
**Cause:** The `XovisSafetyGuardrail` is intercepting the command because it is marked as `CRITICAL` in the Enterprise Safety Policy and lacks confirmation.
**Solution:** The agent MUST pass `{"confirmation": True}` in the tool arguments. If the tool is still blocked, it may be set to `SafetyLevel.BLOCKED` (e.g., `flash_format`), which is hardcoded and cannot be bypassed.

### 4. Hardware Capability Blocks (Lensless Spider)
**Symptom:** The agent attempts to configure physical zones on a Spider NUC, but the API rejects it.
**Cause:** Spider NUCs lack physical lenses and only support `multisensors` contexts.
**Solution:** The agent must always evaluate `get_system_info` first. If `is_spider` is True, it must strictly use the `multisensor` context for analytics and geometries.

### 5. AI Safety TUI Configuration
**Symptom:** The agent is hashing or blocking data (like MAC addresses) that the user needs to see in the final report.
**Cause:** The `AIPrivacySession` is performing pseudonymization based on the default or user-configured privacy levels.
**Solution:** Use the built-in **AI Safety TUI** to adjust field-level privacy (HASH/BLOCK/ALLOW) or tool safety mappings. Changes are persisted in `.xovis_ai_privacy.json` and applied at runtime.
