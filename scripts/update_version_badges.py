"""
Xovis SDK - Version Badge Synchronizer.

This script scans the project's markdown documentation (README.md and all files
within the docs/ directory) to automatically synchronize PyPI and NPM version-specific
badges and hyperlinks with the current version defined in pyproject.toml.
"""

import os
import re
from pathlib import Path


def get_current_version() -> str:
    """
    Extracts the current SDK version from pyproject.toml.

    Returns:
        str: The version string (e.g., "1.0.0a18").

    Raises:
        FileNotFoundError: If pyproject.toml is missing.
        ValueError: If the version string cannot be found.
    """
    toml_path = Path("pyproject.toml")
    if not toml_path.exists():
        raise FileNotFoundError("pyproject.toml not found in the root directory.")

    with open(toml_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")

    return match.group(1)


def get_npm_version(py_version: str) -> str:
    """
    Converts a Python/PyPI style prerelease version to NPM semver format.
    Example: "1.0.0a18" -> "1.0.0-a18".

    Args:
        py_version (str): The Python package version.

    Returns:
        str: The normalized NPM version.
    """
    match = re.match(r"^(\d+\.\d+\.\d+)(a|b|rc)(\d+)$", py_version)
    if match:
        return f"{match.group(1)}-{match.group(2)}{match.group(3)}"
    return py_version


def update_badges_in_file(file_path: Path, py_version: str, npm_version: str) -> bool:
    """
    Updates PyPI and NPM version badge links in a single markdown file.

    Args:
        file_path (Path): Path to the markdown file.
        py_version (str): The current Python/PyPI version.
        npm_version (str): The current NPM version.

    Returns:
        bool: True if any modifications were made, False otherwise.
    """
    if not file_path.exists():
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # 1. Update PyPI release/project links (e.g., https://pypi.org/project/xovis-sdk/1.0.0a18/)
    pypi_pattern = r"(https://pypi\.org/project/xovis-sdk/)[^/)]+(/?)"
    content = re.sub(pypi_pattern, rf"\g<1>{py_version}\g<2>", content)

    # 2. Update NPM release/package links with specific versions if they exist
    npm_pattern = r"(https://www\.npmjs\.com/package/xovis-sdk/v/)[^/)]+(/?)"
    content = re.sub(npm_pattern, rf"\g<1>{npm_version}\g<2>", content)

    # 3. Update any inline code or text badges containing xovis-sdk==<version> or xovis-sdk@<version>
    pip_install_pattern = r"(pip install \"?xovis-sdk(?:\[[^\]]+\])?==)[^\s\"]+(\"?)"
    content = re.sub(pip_install_pattern, rf"\g<1>{py_version}\g<2>", content)

    npm_install_pattern = r"(npm install xovis-sdk@)[^\s\"]+"
    content = re.sub(npm_install_pattern, rf"\g<1>{npm_version}", content)

    if content != original_content:
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return True

    return False


def main() -> None:
    """
    Main execution loop to discover and update all markdown files in the project.
    """
    try:
        py_version = get_current_version()
        npm_version = get_npm_version(py_version)
    except Exception as e:
        print(f"Error: {e}")
        return

    print("Synchronizing version badges across documentation...")
    print(f"  PyPI version: {py_version}")
    print(f"  NPM version:  {npm_version}")

    modified_files = []

    # Check root README.md
    readme_path = Path("README.md")
    if update_badges_in_file(readme_path, py_version, npm_version):
        modified_files.append(readme_path)

    # Check all files in docs/
    docs_dir = Path("docs")
    if docs_dir.exists() and docs_dir.is_dir():
        for md_file in docs_dir.glob("**/*.md"):
            if update_badges_in_file(md_file, py_version, npm_version):
                modified_files.append(md_file)

    if modified_files:
        print(f"\nSuccessfully updated version badges in {len(modified_files)} files:")
        for f in modified_files:
            print(f"  - {f}")
    else:
        print("\nAll version badges are already up-to-date!")


if __name__ == "__main__":
    main()
