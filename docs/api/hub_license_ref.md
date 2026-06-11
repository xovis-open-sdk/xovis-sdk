# 💳 Hub License API Reference (Scalar)

This schema dictates the **billing** and **subscription** payloads handled by the `xovis-sdk` when operating against the Xovis HUB Cloud. 

The SDK's Control Plane natively maps these endpoints into the `LicenseStatus` and `PayPerUseBillStatus` Pydantic V2 models, ensuring enterprise compliance and usage tracking.

---

<div id="setup-instructions" class="setup-instructions-container" style="display: none;" markdown="1">

!!! failure "Interactive Explorer Disabled"
    The interactive explorer is currently disabled because the proprietary **Hub License schema** was not found in your local environment.

    The SDK's `HubLicenseManager` uses these schemas to validate license allocation and service entitlement across global fleet deployments.

#### How to Enable Locally

1. **Warmup:** Run `xovis warmup-hub` to download the `HUB-license.json` schema from the Hub.
2. **Verify:** Ensure the schema is saved in `docs/assets/openapi/HUB-license.json`.
3. **Clean & Serve:** Run `rm -r site` (if it exists) and `mkdocs serve` to view the reference.

</div>

<div id="explorer-container" style="display: none;">

<div class="scalar-api-reference">
  <script
    id="api-reference"
    data-url="../../assets/openapi/HUB-license.json"
    data-configuration='{"theme": "deepSpace", "showSidebar": true, "layout": "modern"}'></script>
</div>
<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>

</div>

<script>
(async () => {
  const schemaUrl = "../../assets/openapi/HUB-license.json";
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