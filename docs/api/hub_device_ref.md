# ☁️ Hub Device API Reference (Scalar)

This schema defines the exact **telemetry** and **orchestration** payloads managed by the SDK's `HubClient`. 

The SDK parses these Cloud HUB responses into strict Python types (e.g., `HubDevice`), enabling you to confidently execute `bulk_execute` operations without manually parsing this raw REST interface.

---

<div id="setup-instructions" class="setup-instructions-container" style="display: none;" markdown="1">

!!! failure "Interactive Explorer Disabled"
    The interactive explorer is currently disabled because the proprietary **Hub Device schema** was not found in your local environment.

    The `XovisAIToolkit` Universal Tool Adapter leverages these underlying definitions to dynamically expose fleet-scale operations to autonomous LLM agents.

#### How to Enable Locally

1. **Warmup:** Run `xovis warmup-hub` to download the `HUB-device-management.json` schema from the Hub.
2. **Verify:** Ensure the schema is saved in `docs/assets/openapi/HUB-device-management.json`.
3. **Clean & Serve:** Run `rm -r site` (if it exists) and `mkdocs serve` to view the reference.

</div>

<div id="explorer-container" style="display: none;">

<div class="scalar-api-reference">
  <script
    id="api-reference"
    data-url="../../assets/openapi/HUB-device-management.json"
    data-configuration='{"theme": "deepSpace", "showSidebar": true, "layout": "modern"}'></script>
</div>
<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>

</div>

<script>
(async () => {
  const schemaUrl = "../../assets/openapi/HUB-device-management.json";
  try {
    const response = await fetch(schemaUrl, { method: 'HEAD', cache: 'no-store' });
    if (response.ok) {
      document.getElementById('explorer-container').style.display = 'block';
    } else {
      document.getElementById('setup-instructions').style.display = 'block';
    }
  } catch (err) {
    document.getElementById('setup-instructions').style.display = 'block';
  }
})();
</script>