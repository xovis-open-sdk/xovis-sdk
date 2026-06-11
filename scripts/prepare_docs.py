import os
import shutil
from pathlib import Path


def prepare_openapi_assets():
    """
    Copies proprietary OpenAPI schemas from _local_ressources/ to docs/assets/openapi/.
    This ensures Scalar can render them locally without committing proprietary data to Git.
    """
    base_dir = Path(__file__).parent.parent
    source_dir = base_dir / "_local_ressources"
    target_dir = base_dir / "docs" / "assets" / "openapi"

    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    print("--- Preparing Documentation Assets ---")

    # 1. Copy the main 'latest' schemas
    main_schemas = ["api.yaml", "HUB-device-management.json", "HUB-license.json"]
    for schema in main_schemas:
        src = source_dir / schema
        dst = target_dir / schema
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  [OK] Copied {schema}")
        else:
            print(f"  [SKIPPED] {schema} not found in _local_ressources/")

    # 2. Copy any versioned schemas found in _local_ressources
    # Versioned schemas follow patterns: api_*.yaml, HUB-*_*.json
    for src in source_dir.glob("api_*.yaml"):
        shutil.copy2(src, target_dir / src.name)
        print(f"  [OK] Copied versioned schema: {src.name}")

    for src in source_dir.glob("HUB-*_*.json"):
        shutil.copy2(src, target_dir / src.name)
        print(f"  [OK] Copied versioned schema: {src.name}")

    print("---------------------------------------\n")


if __name__ == "__main__":
    prepare_openapi_assets()
