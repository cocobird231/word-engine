"""
Diagram rendering for Graphviz and Mermaid code blocks.

Converts diagram source code to high-resolution PNG and SVG images
saved in the assets directory.

- PNG: embedded in the docx (high-DPI for print quality)
- SVG: saved alongside as a vector asset for downstream use

Graphviz: requires either the 'graphviz' Python package or the 'dot' CLI.
Mermaid:  requires the 'mmdc' CLI (@mermaid-js/mermaid-cli via npm).
"""
import json
import os
import subprocess
import tempfile

# ── Quality settings ─────────────────────────────────────────────────────
GRAPHVIZ_DPI = 300        # DPI for Graphviz PNG output
MERMAID_SCALE = 4         # Puppeteer scale factor for Mermaid (4x = ~384 DPI)
MERMAID_WIDTH = 1600      # Puppeteer viewport width for Mermaid


def render_graphviz(code: str, assets_dir: str, index: int) -> "str | None":
    """
    Render a Graphviz dot diagram to high-resolution PNG + SVG.

    Tries the 'graphviz' Python package first, then falls back to the
    'dot' CLI via subprocess.

    Args:
        code: Graphviz dot source code.
        assets_dir: Directory to save image files.
        index: Sequential index for unique filenames.

    Returns:
        Absolute path to the generated PNG, or None if rendering failed.
        SVG is saved alongside if successful.
    """
    os.makedirs(assets_dir, exist_ok=True)
    png_name = f"diagram_graphviz_{index:03d}.png"
    svg_name = f"diagram_graphviz_{index:03d}.svg"
    png_path = os.path.join(assets_dir, png_name)
    svg_path = os.path.join(assets_dir, svg_name)

    # Try graphviz Python package first
    try:
        import graphviz  # type: ignore
        src = graphviz.Source(code, format="png")
        src.render(outfile=png_path, cleanup=True)
        # Also render SVG
        src_svg = graphviz.Source(code, format="svg")
        src_svg.render(outfile=svg_path, cleanup=True)
        if os.path.isfile(png_path):
            return png_path
    except ImportError:
        pass
    except Exception:
        pass

    # Fall back to dot CLI
    try:
        # High-DPI PNG
        result = subprocess.run(
            ["dot", f"-Gdpi={GRAPHVIZ_DPI}", "-Tpng", "-o", png_path],
            input=code.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        # SVG (vector)
        subprocess.run(
            ["dot", "-Tsvg", "-o", svg_path],
            input=code.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0 and os.path.isfile(png_path):
            return png_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def render_mermaid(code: str, assets_dir: str, index: int) -> "str | None":
    """
    Render a Mermaid diagram to high-resolution PNG + SVG.

    Uses the mmdc CLI with increased scale factor for crisp output.

    Args:
        code: Mermaid diagram source code.
        assets_dir: Directory to save image files.
        index: Sequential index for unique filenames.

    Returns:
        Absolute path to the generated PNG, or None if rendering failed.
        SVG is saved alongside if successful.
    """
    os.makedirs(assets_dir, exist_ok=True)
    png_name = f"diagram_mermaid_{index:03d}.png"
    svg_name = f"diagram_mermaid_{index:03d}.svg"
    png_path = os.path.join(assets_dir, png_name)
    svg_path = os.path.join(assets_dir, svg_name)

    tmp_input = None
    tmp_puppeteer = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".mmd", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_input = f.name

        # Puppeteer config with sandbox workaround
        puppeteer_cfg = {
            "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as pf:
            json.dump(puppeteer_cfg, pf)
            tmp_puppeteer = pf.name

        # High-resolution PNG
        result = subprocess.run(
            ["mmdc", "-i", tmp_input, "-o", png_path,
             "-p", tmp_puppeteer,
             "-s", str(MERMAID_SCALE),
             "-w", str(MERMAID_WIDTH)],
            capture_output=True,
            timeout=60,
        )
        png_ok = result.returncode == 0 and os.path.isfile(png_path)

        # SVG (vector)
        subprocess.run(
            ["mmdc", "-i", tmp_input, "-o", svg_path,
             "-p", tmp_puppeteer,
             "-e", "svg"],
            capture_output=True,
            timeout=60,
        )

        return png_path if png_ok else None

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
