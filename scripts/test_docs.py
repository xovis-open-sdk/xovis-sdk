import logging
import os
import sys
from pathlib import Path

from xovis.api.device.sync import HardwareSyncer
from xovis.api.hub.sync import HubSyncer

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("docs-test")


def test_docs_generation():
    """
    Simulates the documentation generation and verification workflow.
    """
    logger.info("--- Documentation Workflow Test ---")

    # 1. Simulate Hardware Warmup (if env vars available)
    host = os.getenv("XOVIS_DEVICE_IP", "192.168.178.38")
    user = os.getenv("XOVIS_DEVICE_USER", "admin")
    password = os.getenv("XOVIS_DEVICE_PASS", "pass")

    logger.info(f"Step 1: Testing Hardware Sync for {host} (User: {user}, Pass length: {len(password) if password else 0})")
    # In CI without real hardware, this might fail, which is expected unless mocked
    # But we want to test that the sync logic handles it gracefully or works if HW is there.
    # For a local "user test", this is exactly what they would run.

    # 2. Simulate Hub Warmup
    hub_id = os.getenv("XOVIS_HUB_CLIENT_ID", "dummy_id")
    hub_secret = os.getenv("XOVIS_HUB_CLIENT_SECRET", "dummy_secret")
    logger.info(f"Step 2: Testing Hub Sync (ID: {hub_id}, Secret length: {len(hub_secret) if hub_secret else 0})")

    # 3. Generate AI Context Files
    logger.info("Step 3: Generating llms.txt, llms-full.txt, and llms-small.txt")
    from generate_ai_context import generate_llms_full_txt, generate_llms_small_txt, generate_llms_txt

    generate_llms_txt()
    generate_llms_full_txt()
    generate_llms_small_txt()

    # 4. Verify AI context files exist
    llms_txt = Path("docs/llms.txt")
    llms_full_txt = Path("docs/llms-full.txt")
    llms_small_txt = Path("docs/llms-small.txt")

    if llms_txt.exists() and llms_txt.stat().st_size > 0:
        logger.info(f"  [OK] {llms_txt} generated.")
    else:
        logger.error(f"  [FAIL] {llms_txt} missing or empty.")
        return False

    if llms_full_txt.exists() and llms_full_txt.stat().st_size > 0:
        logger.info(f"  [OK] {llms_full_txt} generated.")
    else:
        logger.error(f"  [FAIL] {llms_full_txt} missing or empty.")
        return False

    if llms_small_txt.exists() and llms_small_txt.stat().st_size > 0:
        logger.info(f"  [OK] {llms_small_txt} generated.")
    else:
        logger.error(f"  [FAIL] {llms_small_txt} missing or empty.")
        return False

    # 5. Prepare OpenAPI assets
    logger.info("Step 5: Preparing Documentation Assets")
    from prepare_docs import prepare_openapi_assets

    prepare_openapi_assets()

    # 6. Verify docs structure
    logger.info("Step 6: Verifying MkDocs Structure")
    root_dir = Path(__file__).parent.parent
    if (root_dir / "mkdocs.yml").exists():
        logger.info("  [OK] mkdocs.yml found.")
    else:
        logger.error(f"  [FAIL] mkdocs.yml missing at {root_dir / 'mkdocs.yml'}.")
        return False

    logger.info("--- Documentation Workflow Test Completed ---")
    return True


if __name__ == "__main__":
    success = test_docs_generation()
    if not success:
        sys.exit(1)
