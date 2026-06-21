# Device API Reference (Scalar)

This specification defines the foundational **Data Plane** and **Control Plane** structures that the `xovis-sdk` automatically validates via **Pydantic V2**. 

While the SDK abstracts these endpoints natively through the `DeviceClient`, this reference provides complete transparency into the raw edge payloads processed under the hood.

---

<div id="setup-instructions" class="setup-instructions-container" style="display: none;" markdown="1">

!!! failure "Interactive Explorer Disabled"
    The interactive explorer is currently disabled because the proprietary **Device API schema** (`api.yaml`) was not found in your local environment.

    The SDK generates strict `RootModels` and `typing.Literal` definitions directly from this proprietary specification to guarantee zero-drift between the hardware and your Python runtime.

#### How to Enable Locally

1. **Warmup:** Run `xovis warmup --host <IP>` to download the `api.yaml` schema from your sensor.
2. **Verify:** Ensure the schema is saved in `docs/assets/openapi/api.yaml`.
3. **Clean & Serve:** Run `rm -r site` (if it exists) and `mkdocs serve` to view the reference.

</div>

<div id="explorer-container" style="display: none;">

<div class="scalar-api-reference">
  <script
    id="api-reference"
    data-url="../../assets/openapi/api.yaml"
    data-configuration='{"theme": "deepSpace", "showSidebar": true, "layout": "modern"}'></script>
</div>
<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>

</div>

<script>
(async () => {
  const schemaUrl = "../../assets/openapi/api.yaml";
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