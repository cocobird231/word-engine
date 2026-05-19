"""
Diagram rendering for Graphviz and Mermaid code blocks.

Converts diagram source code to PNG images saved in the assets directory.

Graphviz: requires either the 'graphviz' Python package or the 'dot' CLI.
Mermaid:  requires the 'mmdc' CLI (@mermaid-js/mermaid-cli via npm).
"""
import os
import subprocess
import tempfile


def render_graphviz(code: str, assets_dir: str, index: int) -> "str | None":
    """
    Render a Graphviz dot diagram to PNG and save it to assets_dir.

    Tries the 'graphviz' Python package first, then falls back to the
    'dot' CLI via subprocess.

    Args:
        code: Graphviz dot source code.
        assets_dir: Directory to save the PNG file.
        index: Sequential index used to generate a unique filename.

    Returns:
        Absolute path to the generated PNG, or None if rendering failed.
    """
    os.makedirs(assets_dir, exist_ok=True)
    filename = f"diagram_graphviz_{index:03d}.png"
    output_path = os.path.join(assets_dir, filename)

    # Try graphviz Python package first
    try:
        import graphviz  # type: ignore
        src = graphviz.Source(code, format="png")
        src.render(outfile=output_path, cleanup=True)
        if os.path.isfile(output_path):
            return output_path
    except ImportError:
        pass
    except Exception:
        pass

    # Fall back to dot CLI
    try:
        result = subprocess.run(
            ["dot", "-Tpng", "-o", output_path],
            input=code.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0 and os.path.isfile(output_path):
            return output_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def render_mermaid(code: str, assets_dir: str, index: int) -> "str | None":
    """
    Render a Mermaid diagram to PNG using the mmdc CLI.

    Requires @mermaid-js/mermaid-cli installed globally:
        npm install -g @mermaid-js/mermaid-cli

    Args:
        code: Mermaid diagram source code.
        assets_dir: Directory to save the PNG file.
        index: Sequential index used to generate a unique filename.

    Returns:
        Absolute path to the generated PNG, or None if rendering failed.
    """
    os.makedirs(assets_dir, exist_ok=True)
    filename = f"diagram_mermaid_{index:03d}.png"
    output_path = os.path.join(assets_dir, filename)

    tmp_input = None
    tmp_puppeteer = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".mmd", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_input = f.name

        # Write puppeteer config with --no-sandbox for sandboxed environments
        import json
        puppeteer_cfg = {"args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as pf:
            json.dump(puppeteer_cfg, pf)
            tmp_puppeteer = pf.name

        result = subprocess.run(
            ["mmdc", "-i", tmp_input, "-o", output_path, "-p", tmp_puppeteer],
            capture_output=True,
            timeout=60,
        )
        if result.returncode == 0 and os.path.isfile(output_path):
            return output_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    finally:
        for tmp in [tmp_input, tmp_puppeteer]:
            if tmp:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

    return None
