"""
Xovis SDK - Smithery Server Metadata Synchronizer.

Provides an automated script to synchronize local metadata from `smithery.yaml`
with the Smithery Platform API to ensure alignment of directory configurations,
icons, display names, descriptions, and other public registry metadata.
"""

import os
import sys

import httpx
import yaml


def update_smithery_server() -> None:
    """
    Synchronizes local smithery.yaml metadata with the Smithery Platform API.

    Loads the configuration from `smithery.yaml`, reads the API key from the
    environment variable `SMITHERY_API_KEY`, and executes a PATCH request to
    the Smithery API server update endpoint.

    Raises:
        ValueError: If SMITHERY_API_KEY is missing or smithery.yaml is corrupt.
        RuntimeError: If the API request fails.
    """
    api_key = os.getenv("SMITHERY_API_KEY")
    if not api_key:
        print("Error: SMITHERY_API_KEY environment variable is not set.")
        sys.exit(1)

    yaml_path = "smithery.yaml"
    if not os.path.exists(yaml_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(script_dir, "..", "smithery.yaml")

    if not os.path.exists(yaml_path):
        print(f"Error: Configuration file not found at {yaml_path}")
        sys.exit(1)

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error: Failed to parse {yaml_path}: {e}")
        sys.exit(1)

    display_name = config.get("displayName")
    description = config.get("description")
    homepage = config.get("homepage")

    if not display_name or not description:
        print("Error: displayName and description are required in smithery.yaml")
        sys.exit(1)

    qualified_name = "xovis-sdk/xovis-mcp"
    encoded_name = "xovis-sdk%2Fxovis-mcp"
    url = f"https://api.smithery.ai/servers/{encoded_name}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "displayName": display_name,
        "description": description,
        "homepage": homepage,
        "repositoryUrl": "https://github.com/xovis-open-sdk/xovis-sdk",
    }

    print(f"Sending metadata update to Smithery API for {qualified_name}...")
    try:
        response = httpx.patch(url, headers=headers, json=payload, timeout=30.0)
        if response.status_code == 200:
            print("Successfully updated Smithery server metadata!")
            print(response.json())
        else:
            print(f"Failed to update metadata. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Error executing API request: {e}")
        sys.exit(1)


if __name__ == "__main__":
    update_smithery_server()
