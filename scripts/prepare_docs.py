import os
import shutil
from pathlib import Path


def prepare_openapi_assets():
    """
    Copies proprietary OpenAPI schemas from _local_resources/ to docs/assets/openapi/.
    This ensures Scalar can render them locally without committing proprietary data to Git.
    """
    base_dir = Path(__file__).parent.parent
    source_dir = base_dir / "_local_resources"
    target_dir = base_dir / "docs" / "assets" / "openapi"

    target_dir.mkdir(parents=True, exist_ok=True)

    print("--- Preparing Documentation Assets ---")

    schemas_to_copy = [
        (source_dir / "schemas" / "api.yaml", target_dir / "api.yaml"),
        (source_dir / "schemas" / "hub" / "HUB-device-management.json", target_dir / "HUB-device-management.json"),
        (source_dir / "schemas" / "hub" / "HUB-license.json", target_dir / "HUB-license.json"),
    ]

    for src, dst in schemas_to_copy:
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  [OK] Copied {src.name} to {dst.name}")
        else:
            print(f"  [SKIPPED] {src.name} not found")

    schemas_path = source_dir / "schemas"
    if schemas_path.exists():
        for item in schemas_path.iterdir():
            if item.is_dir() and item.name != "hub":
                version_api = item / "api.yaml"
                if version_api.exists():
                    dst_name = f"api_{item.name}.yaml"
                    shutil.copy2(version_api, target_dir / dst_name)
                    print(f"  [OK] Copied versioned schema: {dst_name}")

        hub_dir = schemas_path / "hub"
        if hub_dir.exists():
            for src in hub_dir.glob("HUB-*_*.json"):
                shutil.copy2(src, target_dir / src.name)
                print(f"  [OK] Copied versioned HUB schema: {src.name}")

    print("---------------------------------------\n")


if __name__ == "__main__":
    prepare_openapi_assets()
