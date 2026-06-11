import fnmatch
import os
from pathlib import Path


def parse_git_exclude(root_dir):
    """Parses exclusions, safely ignoring Git negations (!)."""
    exclude_file = Path(root_dir) / ".git" / "info" / "exclude"
    gitignore_file = Path(root_dir) / ".gitignore"

    patterns = []
    for target in [exclude_file, gitignore_file]:
        if target.exists():
            with open(target, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Ignore comments and Git negations (!) as fnmatch can't handle them
                    if line and not line.startswith("#") and not line.startswith("!"):
                        patterns.append(line.lstrip("/"))

    patterns.append(".Redacted/PROJECT_TREE_PRIVATE.md")
    return patterns


def generate_tree(root_dir, is_private=False, git_exclude_patterns=None):
    core_exclude_dirs = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".venv",
        ".idea",
        "dist",
        "build",
        "xovis_sdk.egg-info",
        "venv",
        "env",
        ".hatch",
        ".tox",
        ".coverage",
    }
    core_exclude_files = {".DS_Store", "package-lock.json", ".env"}

    tree = []
    root_path = Path(root_dir).resolve()

    def is_excluded(path):
        rel_path = os.path.relpath(path, root_path).replace(os.sep, "/")
        name = os.path.basename(path)

        # Core SDK Privacy: Hide specific proprietary auto-generated models in public view
        if not is_private:
            private_files = {"hub_auto.py", "hub_license_auto.py", "xovis_types.py"}
            if name in private_files and rel_path.startswith("src/xovis/models/"):
                return True

        if name in core_exclude_dirs or name in core_exclude_files:
            return True

        if not is_private and git_exclude_patterns:
            for pattern in git_exclude_patterns:
                clean_pattern = pattern.rstrip("/")
                # Match exact name, or path, or if it's inside a blocked directory
                if fnmatch.fnmatch(name, clean_pattern) or fnmatch.fnmatch(rel_path, clean_pattern) or rel_path.startswith(clean_pattern + "/"):
                    return True
        return False

    def walk(directory, prefix=""):
        rel_directory = os.path.relpath(directory, root_path).replace(os.sep, "/")
        try:
            entries = sorted(list(os.scandir(directory)), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            return

        filtered_entries = [e for e in entries if not is_excluded(e.path)]

        # SPECIAL HANDLING: Hide contents of 'versions' folder but show the folder itself
        if os.path.basename(directory) == "versions" and "src/xovis/models/device_auto/versions" in rel_directory:
            filtered_entries = []

        for i, entry in enumerate(filtered_entries):
            is_last = i == len(filtered_entries) - 1
            connector = "*- " if is_last else "+- "
            tree.append(f"{prefix}{connector}{entry.name}")

            if entry.is_dir():
                extension = "    " if is_last else "|   "
                walk(entry.path, prefix + extension)

    tree.append("xovis-sdk/")
    walk(root_dir)
    return "\n".join(tree)


def update_project_tree(root_dir, target_file=".Redacted/PROJECT_TREE.md", is_private=False):
    git_exclude_patterns = parse_git_exclude(root_dir)
    tree_content = generate_tree(root_dir, is_private=is_private, git_exclude_patterns=git_exclude_patterns)

    title = "Private Repository Structure" if is_private else "Public Repository Structure"
    markdown_content = f"# {title}\n\n```plaintext\n{tree_content}\n```\n"

    target_path = Path(target_file)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(markdown_content, encoding="utf-8")
    print(f"Successfully generated {'PRIVATE ' if is_private else 'PUBLIC '}tree and saved to {target_file}")


if __name__ == "__main__":
    script_path = Path(__file__).resolve()
    root = script_path.parent.parent

    # Generate Public
    update_project_tree(root, target_file=root / "docs" / "project_structure.md", is_private=False)
    # Generate Private
    update_project_tree(root, target_file=root / ".Redacted" / "PROJECT_TREE_PRIVATE.md", is_private=True)
