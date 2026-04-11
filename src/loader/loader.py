"""
Word Engine - Loader Module (Phase 1)
Reads refine.md, params.yaml, and scans assets directory.
"""
import os
import yaml


class LoadError(Exception):
    """Raised when a required file cannot be loaded."""
    pass


def load_markdown(md_path):
    """Load and return markdown file content as string."""
    if not os.path.isfile(md_path):
        raise LoadError(f"Markdown file not found: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        return f.read()


def load_params(params_path):
    """Load and return params YAML as a dict."""
    if not os.path.isfile(params_path):
        raise LoadError(f"Params file not found: {params_path}")
    with open(params_path, "r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise LoadError(f"Failed to parse YAML: {e}")
    if not isinstance(data, dict):
        raise LoadError("Params YAML root must be a mapping (dict).")
    return data


def scan_assets(assets_dir):
    """Scan assets directory and return list of file paths. Returns empty list if dir missing."""
    if not os.path.isdir(assets_dir):
        return []
    files = []
    for root, _dirs, filenames in os.walk(assets_dir):
        for fname in filenames:
            files.append(os.path.join(root, fname))
    return sorted(files)


def load_project(md_path, params_path, assets_dir=None):
    """
    Load all project inputs and return a structured dict.

    Returns:
        {
            "markdown": str,          # raw markdown text
            "params": dict,           # parsed YAML params
            "assets": list[str],      # list of asset file paths
            "metadata": {
                "md_path": str,
                "params_path": str,
                "assets_dir": str | None
            }
        }
    """
    markdown = load_markdown(md_path)
    params = load_params(params_path)

    # Derive assets_dir from params if not explicitly given
    if assets_dir is None:
        paths_config = params.get("paths", {})
        assets_dir = paths_config.get("assets_dir", None)

    assets = scan_assets(assets_dir) if assets_dir else []

    return {
        "markdown": markdown,
        "params": params,
        "assets": assets,
        "metadata": {
            "md_path": os.path.abspath(md_path),
            "params_path": os.path.abspath(params_path),
            "assets_dir": os.path.abspath(assets_dir) if assets_dir else None,
        },
    }
