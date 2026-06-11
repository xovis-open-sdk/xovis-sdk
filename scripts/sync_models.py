"""
scripts/sync_models.py
Zero-dependency AST parser to safely regenerate Pydantic v2 schemas from edge devices.
"""

import ast
import subprocess
import sys
from pathlib import Path

import httpx


def extract_docstrings(file_path: Path) -> dict:
    """
    Parses a file and returns a mapping of class/function names to their docstrings.

    Args:
        file_path (Path): Path to the Python file.

    Returns:
        dict: Mapping of name to docstring.
    """
    if not file_path.exists():
        return {}

    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Warning: Could not parse {file_path} for docstrings: {e}")
        return {}

    return {
        node.name: ast.get_docstring(node) for node in ast.walk(tree) if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node)
    }


def apply_docstrings(file_path: Path, docstrings: dict):
    """
    Injects docstrings back into the generated file using AST.

    Args:
        file_path (Path): Path to the Python file to modify.
        docstrings (dict): Mapping of name to docstring.
    """
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error: Could not parse {file_path} to apply docstrings: {e}")
        return

    class DocstringInjector(ast.NodeTransformer):
        def visit_ClassDef(self, node):
            if node.name in docstrings and not ast.get_docstring(node):
                doc_expr = ast.Expr(value=ast.Constant(value=docstrings[node.name]))
                node.body.insert(0, doc_expr)
            return self.generic_visit(node)

        def visit_FunctionDef(self, node):
            if node.name in docstrings and not ast.get_docstring(node):
                doc_expr = ast.Expr(value=ast.Constant(value=docstrings[node.name]))
                node.body.insert(0, doc_expr)
            return self.generic_visit(node)

    modified_tree = DocstringInjector().visit(tree)
    ast.fix_missing_locations(modified_tree)

    # Requires Python 3.9+ for ast.unparse()
    file_path.write_text(ast.unparse(modified_tree), encoding="utf-8")


def patch_yaml(yaml_path: Path):
    """
    Patches api.yaml to fix known issues with datamodel-codegen.
    Specifically, it quotes boolean keys in discriminator mappings.
    """
    if not yaml_path.exists():
        return

    content = yaml_path.read_text(encoding="utf-8")
    # Quote true: and false: in mapping
    content = content.replace("                true: '#/components/schemas/operand'", "                \"true\": '#/components/schemas/operand'")
    content = content.replace("                false: '#/components/schemas/operand'", "                \"false\": '#/components/schemas/operand'")
    yaml_path.write_text(content, encoding="utf-8")


def sync_api(device_ip: str, version_tag: str):
    """
    Fetches api.yaml from device, generates models, and preserves docstrings.

    Args:
        device_ip (str): IP address of the Xovis device.
        version_tag (str): Version tag for the models (e.g., v5_9_11).
    """
    output_dir = Path("src/xovis/models/device_auto/versions") / version_tag
    output_dir.mkdir(parents=True, exist_ok=True)
    target_file = output_dir / "__init__.py"

    # Backup existing docstrings if file exists
    old_docs = extract_docstrings(target_file)

    print(f"Fetching API from {device_ip}...")
    try:
        resp = httpx.get(f"http://{device_ip}/swagger/api.yaml", timeout=30.0)
        resp.raise_for_status()
        yaml_content = resp.text
    except Exception as e:
        print(f"Error fetching api.yaml: {e}")
        sys.exit(1)

    resource_dir = Path("_local_ressources")
    resource_dir.mkdir(exist_ok=True)
    yaml_path = resource_dir / f"api_{version_tag}.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    patch_yaml(yaml_path)

    print(f"Generating models for {version_tag}...")
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                str(yaml_path),
                "--output",
                str(output_dir),
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--use-standard-collections",
                "--use-union-operator",
                "--target-python-version",
                "3.11",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running datamodel-codegen: {e}")
        sys.exit(1)

    apply_docstrings(target_file, old_docs)
    print(f"Successfully updated Pydantic models for version {version_tag}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/sync_models.py <IP> <VERSION_TAG>")
        sys.exit(1)
    sync_api(sys.argv[1], sys.argv[2])
