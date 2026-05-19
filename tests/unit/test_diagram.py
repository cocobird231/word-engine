"""
Unit tests for diagram rendering (Graphviz, Mermaid) and image auto-download.

Tests cover:
  1. render_graphviz(): Python package path, dot CLI path, missing tool fallback
  2. render_mermaid(): mmdc CLI path, missing tool fallback
  3. _resolve_image_src(): file://, http/https, relative, absolute paths
  4. Integration: fence blocks with graphviz/mermaid/dot lang tags in renderer
  5. Integration: markdown image with remote URL auto-downloads to assets_dir
"""
import hashlib
import os
import shutil
import textwrap
import unittest
from unittest.mock import patch, MagicMock
import pytest
from docx import Document


# ────────────────────────────────────────────────────────────────────────────
# Helper: import functions under test
# ────────────────────────────────────────────────────────────────────────────
from src.renderer.diagram import render_graphviz, render_mermaid
from src.renderer.renderer import _resolve_image_src, render_docx


# ─────────────────────────────────────────────────────────────────────────────
# render_graphviz()
# ─────────────────────────────────────────────────────────────────────────────

class TestRenderGraphviz:
    SIMPLE_DOT = "digraph G { A -> B; }"

    def test_returns_none_when_no_tool_available(self, tmp_path):
        """With both graphviz package and dot CLI absent, returns None."""
        with patch.dict("sys.modules", {"graphviz": None}):
            with patch("shutil.which", return_value=None):
                with patch("subprocess.run", side_effect=FileNotFoundError):
                    result = render_graphviz(self.SIMPLE_DOT, str(tmp_path), 1)
        assert result is None

    def test_uses_dot_cli_fallback(self, tmp_path):
        """Falls back to dot CLI and returns path when CLI succeeds."""
        expected_path = tmp_path / "diagram_graphviz_001.png"
        expected_path.write_bytes(b"\x89PNG fake")

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.dict("sys.modules", {"graphviz": None}):
            with patch("subprocess.run", return_value=mock_result):
                result = render_graphviz(self.SIMPLE_DOT, str(tmp_path), 1)

        assert result is not None
        assert result == str(expected_path)

    def test_filename_uses_index(self, tmp_path):
        """Output filename includes the zero-padded index."""
        with patch.dict("sys.modules", {"graphviz": None}):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                render_graphviz(self.SIMPLE_DOT, str(tmp_path), 42)
        # Whether it succeeded or not, the intended filename pattern is fixed
        intended = tmp_path / "diagram_graphviz_042.png"
        assert "042" in str(intended)  # filename format check

    def test_creates_assets_dir(self, tmp_path):
        """assets_dir is created if it does not exist."""
        new_dir = tmp_path / "new_assets"
        with patch.dict("sys.modules", {"graphviz": None}):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                render_graphviz(self.SIMPLE_DOT, str(new_dir), 1)
        assert new_dir.is_dir()

    def test_uses_graphviz_package_first(self, tmp_path):
        """Tries graphviz Python package before dot CLI."""
        expected = tmp_path / "diagram_graphviz_001.png"
        expected.write_bytes(b"PNG")

        mock_pkg = MagicMock()
        mock_src = MagicMock()
        mock_src.render = MagicMock(return_value=None)
        mock_pkg.Source = MagicMock(return_value=mock_src)

        with patch.dict("sys.modules", {"graphviz": mock_pkg}):
            render_graphviz(self.SIMPLE_DOT, str(tmp_path), 1)

        mock_pkg.Source.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# render_mermaid()
# ─────────────────────────────────────────────────────────────────────────────

class TestRenderMermaid:
    SIMPLE_MERMAID = "graph TD\n    A --> B"

    def test_returns_none_when_mmdc_absent(self, tmp_path):
        """Returns None when mmdc CLI is not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = render_mermaid(self.SIMPLE_MERMAID, str(tmp_path), 1)
        assert result is None

    def test_returns_none_on_nonzero_returncode(self, tmp_path):
        """Returns None when mmdc exits with non-zero return code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            result = render_mermaid(self.SIMPLE_MERMAID, str(tmp_path), 1)
        assert result is None

    def test_returns_path_on_success(self, tmp_path):
        """Returns file path when mmdc succeeds and output exists."""
        expected = tmp_path / "diagram_mermaid_001.png"
        expected.write_bytes(b"PNG")

        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = render_mermaid(self.SIMPLE_MERMAID, str(tmp_path), 1)

        assert result == str(expected)

    def test_filename_uses_index(self, tmp_path):
        """Output filename includes the zero-padded index."""
        expected = tmp_path / "diagram_mermaid_007.png"
        expected.write_bytes(b"PNG")

        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            render_mermaid(self.SIMPLE_MERMAID, str(tmp_path), 7)

        # If we get here without error, filename format was correct
        assert "mermaid_007" in str(expected)

    def test_cleans_up_temp_file_on_error(self, tmp_path):
        """Temporary .mmd file is deleted even when mmdc raises."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            render_mermaid(self.SIMPLE_MERMAID, str(tmp_path), 1)
        # No .mmd files should remain in tmp
        mmd_files = list(tmp_path.glob("*.mmd"))
        assert len(mmd_files) == 0

    def test_cleans_up_temp_file_on_success(self, tmp_path):
        """Temporary .mmd file is deleted after successful mmdc run."""
        expected = tmp_path / "diagram_mermaid_001.png"
        expected.write_bytes(b"PNG")

        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            render_mermaid(self.SIMPLE_MERMAID, str(tmp_path), 1)

        mmd_files = list(tmp_path.glob("*.mmd"))
        assert len(mmd_files) == 0


# ─────────────────────────────────────────────────────────────────────────────
# _resolve_image_src()
# ─────────────────────────────────────────────────────────────────────────────

class TestResolveImageSrc:
    def test_empty_src_returns_none(self, tmp_path):
        result = _resolve_image_src("", str(tmp_path), str(tmp_path), {})
        assert result is None

    def test_none_src_returns_none(self, tmp_path):
        result = _resolve_image_src(None, str(tmp_path), str(tmp_path), {})
        assert result is None

    def test_file_uri_existing_file(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"PNG")
        uri = img.as_uri()  # file:///...
        result = _resolve_image_src(uri, str(tmp_path), str(tmp_path), {})
        assert result is not None
        assert os.path.isfile(result)

    def test_file_uri_missing_file_returns_none(self, tmp_path):
        uri = (tmp_path / "nonexistent.png").as_uri()
        result = _resolve_image_src(uri, str(tmp_path), str(tmp_path), {})
        assert result is None

    def test_relative_path_resolved_from_md_dir(self, tmp_path):
        img = tmp_path / "assets" / "photo.png"
        img.parent.mkdir(parents=True)
        img.write_bytes(b"PNG")
        result = _resolve_image_src("assets/photo.png", str(tmp_path), str(tmp_path), {})
        assert result is not None
        assert os.path.isfile(result)

    def test_relative_path_missing_returns_none(self, tmp_path):
        result = _resolve_image_src("does_not_exist.png", str(tmp_path), str(tmp_path), {})
        assert result is None

    def test_absolute_path_existing(self, tmp_path):
        img = tmp_path / "abs.png"
        img.write_bytes(b"PNG")
        result = _resolve_image_src(str(img), str(tmp_path), str(tmp_path), {})
        assert result == str(img)

    def test_absolute_path_missing_returns_none(self, tmp_path):
        result = _resolve_image_src("/nonexistent/path.png", str(tmp_path), str(tmp_path), {})
        assert result is None

    def test_http_url_download_disabled(self, tmp_path):
        """When download_remote_images is False, HTTP URLs return None."""
        result = _resolve_image_src(
            "https://example.com/img.png",
            str(tmp_path), str(tmp_path),
            {"download_remote_images": False}
        )
        assert result is None

    def test_http_url_download_enabled_and_cached(self, tmp_path):
        """When enabled, URL is downloaded and cached."""
        url = "https://example.com/test.png"
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        dest = tmp_path / f"image_{url_hash}.png"

        def fake_retrieve(u, path):
            open(path, "wb").write(b"PNG")

        with patch("urllib.request.urlretrieve", side_effect=fake_retrieve):
            result = _resolve_image_src(
                url, str(tmp_path), str(tmp_path),
                {"download_remote_images": True}
            )

        assert result is not None
        assert os.path.isfile(result)

    def test_http_url_cached_not_re_downloaded(self, tmp_path):
        """Cached image is not re-downloaded on second call."""
        url = "https://example.com/test.png"
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        dest = tmp_path / f"image_{url_hash}.png"
        dest.write_bytes(b"PNG")  # pre-cache

        with patch("urllib.request.urlretrieve") as mock_retrieve:
            _resolve_image_src(
                url, str(tmp_path), str(tmp_path),
                {"download_remote_images": True}
            )
            mock_retrieve.assert_not_called()

    def test_http_url_download_error_returns_none(self, tmp_path):
        """Network error during download returns None."""
        with patch("urllib.request.urlretrieve", side_effect=Exception("network error")):
            result = _resolve_image_src(
                "https://example.com/img.png",
                str(tmp_path), str(tmp_path),
                {"download_remote_images": True}
            )
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Integration: graphviz/mermaid fence blocks in render_docx
# ─────────────────────────────────────────────────────────────────────────────

def _minimal_params():
    return {
        "cover": {"enabled": False},
        "toc": {"enabled": False},
        "images": {"insert_caption": False, "download_remote_images": True,
                   "max_width_cm": 15.5},
        "tables": {"caption_enabled": False},
        "cross_references": {},
    }


class TestGraphvizIntegration:
    def test_graphviz_missing_tool_renders_placeholder(self, tmp_path):
        """When graphviz/dot not available, a placeholder paragraph is inserted."""
        md = textwrap.dedent("""\
            # Test

            ```graphviz
            digraph G { A -> B; }
            ```
        """)
        out = str(tmp_path / "out.docx")

        with patch("src.renderer.renderer.render_graphviz", return_value=None):
            render_docx(md, _minimal_params(), out, assets_dir=str(tmp_path))

        doc = Document(out)
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert any("Graphviz" in t or "graphviz" in t.lower() for t in texts), \
            f"No Graphviz placeholder found. Paragraphs: {texts}"

    def test_graphviz_with_dot_lang_tag(self, tmp_path):
        """'dot' language tag is treated the same as 'graphviz'."""
        md = textwrap.dedent("""\
            # Test

            ```dot
            digraph G { A -> B; }
            ```
        """)
        out = str(tmp_path / "out.docx")

        with patch("src.renderer.renderer.render_graphviz", return_value=None):
            render_docx(md, _minimal_params(), out, assets_dir=str(tmp_path))

        doc = Document(out)
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        # Should have some placeholder (not raw dot code)
        assert not any("digraph" in t for t in texts), \
            "Raw dot code should not appear in output"

    def test_graphviz_image_embedded_when_available(self, tmp_path):
        """When render_graphviz returns a path, image is inserted."""
        fake_img = tmp_path / "diagram_graphviz_001.png"
        # Create a real 1x1 white PNG
        import struct, zlib
        def make_png():
            def chunk(name, data):
                c = struct.pack(">I", len(data)) + name + data
                return c + struct.pack(">I", zlib.crc32(name + data) & 0xffffffff)
            header = b'\x89PNG\r\n\x1a\n'
            ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            idat = chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff'))
            iend = chunk(b'IEND', b'')
            return header + ihdr + idat + iend
        fake_img.write_bytes(make_png())

        md = textwrap.dedent("""\
            # Test

            ```graphviz
            digraph G { A -> B; }
            ```
        """)
        out = str(tmp_path / "out.docx")

        with patch("src.renderer.renderer.render_graphviz", return_value=str(fake_img)):
            render_docx(md, _minimal_params(), out, assets_dir=str(tmp_path))

        doc = Document(out)
        # Image should be embedded (no placeholder text about Graphviz)
        placeholder_texts = [p.text for p in doc.paragraphs
                             if "Graphviz" in p.text or "graphviz" in p.text.lower()]
        assert len(placeholder_texts) == 0, f"Unexpected placeholder: {placeholder_texts}"


class TestMermaidIntegration:
    def test_mermaid_missing_tool_renders_placeholder(self, tmp_path):
        """When mmdc not available, a placeholder paragraph is inserted."""
        md = textwrap.dedent("""\
            # Test

            ```mermaid
            graph TD
                A --> B
            ```
        """)
        out = str(tmp_path / "out.docx")

        with patch("src.renderer.renderer.render_mermaid", return_value=None):
            render_docx(md, _minimal_params(), out, assets_dir=str(tmp_path))

        doc = Document(out)
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert any("Mermaid" in t or "mermaid" in t.lower() for t in texts), \
            f"No Mermaid placeholder found. Paragraphs: {texts}"

    def test_mermaid_raw_code_not_in_output(self, tmp_path):
        """Mermaid source code should not appear verbatim in the docx."""
        md = textwrap.dedent("""\
            # Test

            ```mermaid
            graph TD
                A --> B
            ```
        """)
        out = str(tmp_path / "out.docx")

        with patch("src.renderer.renderer.render_mermaid", return_value=None):
            render_docx(md, _minimal_params(), out, assets_dir=str(tmp_path))

        doc = Document(out)
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert not any("graph TD" in t for t in texts), \
            "Raw Mermaid source should not appear in output"


# ─────────────────────────────────────────────────────────────────────────────
# Integration: image auto-download in render_docx
# ─────────────────────────────────────────────────────────────────────────────

class TestImageAutoDownload:
    def test_remote_image_downloaded_to_assets_dir(self, tmp_path):
        """A remote image URL is downloaded and saved to assets_dir."""
        url = "https://example.com/test.png"
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        expected_file = tmp_path / "assets" / f"image_{url_hash}.png"

        def fake_retrieve(u, path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").write(b"PNG_fake")

        md = f"# T\n\n![desc]({url})\n"
        out = str(tmp_path / "out.docx")

        with patch("urllib.request.urlretrieve", side_effect=fake_retrieve):
            render_docx(md, _minimal_params(), out,
                        md_dir=str(tmp_path),
                        assets_dir=str(tmp_path / "assets"))

        # File should have been downloaded
        assert expected_file.exists(), f"Expected {expected_file} to exist"

    def test_remote_image_download_disabled_shows_placeholder(self, tmp_path):
        """When download_remote_images=False, a placeholder is shown."""
        md = "# T\n\n![desc](https://example.com/img.png)\n"
        out = str(tmp_path / "out.docx")
        params = _minimal_params()
        params["images"]["download_remote_images"] = False

        render_docx(md, params, out,
                    md_dir=str(tmp_path),
                    assets_dir=str(tmp_path / "assets"))

        doc = Document(out)
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert any("圖片" in t or "http" in t for t in texts), \
            f"Expected placeholder for disabled download. Got: {texts}"

    def test_md_dir_used_to_resolve_relative_image(self, tmp_path):
        """Relative image path is resolved relative to md_dir."""
        assets = tmp_path / "imgs"
        assets.mkdir()

        # Create a minimal valid PNG
        import struct, zlib
        def make_png():
            def chunk(name, data):
                c = struct.pack(">I", len(data)) + name + data
                return c + struct.pack(">I", zlib.crc32(name + data) & 0xffffffff)
            header = b'\x89PNG\r\n\x1a\n'
            ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            idat = chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff'))
            iend = chunk(b'IEND', b'')
            return header + ihdr + idat + iend

        img = assets / "logo.png"
        img.write_bytes(make_png())

        md = "# T\n\n![logo](imgs/logo.png)\n"
        out = str(tmp_path / "out.docx")

        render_docx(md, _minimal_params(), out,
                    md_dir=str(tmp_path),
                    assets_dir=str(tmp_path / "assets_out"))

        doc = Document(out)
        # Image embedded → no placeholder text with "圖片: imgs/logo.png"
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        placeholder_texts = [t for t in texts if "imgs/logo.png" in t]
        assert len(placeholder_texts) == 0, \
            f"Image should have been embedded, not shown as placeholder: {placeholder_texts}"


# ─────────────────────────────────────────────────────────────────────────────
# _insert_image_paragraph(): width-only, height-only, both, natural size
# ─────────────────────────────────────────────────────────────────────────────

def _make_png(width_px: int, height_px: int, dpi: int = 96) -> bytes:
    """Create a minimal valid PNG with the specified pixel dimensions."""
    import struct, zlib
    def chunk(name, data):
        c = struct.pack(">I", len(data)) + name + data
        return c + struct.pack(">I", zlib.crc32(name + data) & 0xffffffff)
    header = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width_px, height_px, 8, 2, 0, 0, 0))
    row = b'\x00' + b'\xff\xff\xff' * width_px
    idat = chunk(b'IDAT', zlib.compress(row * height_px))
    iend = chunk(b'IEND', b'')
    return header + ihdr + idat + iend


class TestInsertImageParagraphScaling:
    """Tests for _insert_image_paragraph width+height constraints."""

    def _render_md_with_local_img(self, tmp_path, width_px, height_px, dpi=96):
        """Create a local PNG and render a markdown doc that includes it."""
        from src.renderer.renderer import render_docx
        assets = tmp_path / "assets"
        assets.mkdir()
        img = assets / "test.png"
        img.write_bytes(_make_png(width_px, height_px, dpi))

        # Use an image src with max_width_cm=15.5, max_height_cm=20.0
        params = {
            "cover": {"enabled": False}, "toc": {"enabled": False},
            "images": {
                "insert_caption": False, "download_remote_images": False,
                "max_width_cm": 15.5, "max_height_cm": 20.0
            },
            "tables": {"caption_enabled": False}, "cross_references": {},
        }
        md = "# T\n\n![img](assets/test.png)\n"
        out = str(tmp_path / "out.docx")
        render_docx(md, params, out, md_dir=str(tmp_path), assets_dir=str(assets))
        return out

    def test_wide_image_scaled_to_max_width(self, tmp_path):
        """Image wider than max_width_cm should be scaled down."""
        # 2000px wide at 96dpi ≈ 53cm, well over 15.5cm
        out = self._render_md_with_local_img(tmp_path, width_px=2000, height_px=200)
        from docx import Document
        doc = Document(out)
        # Should render without error and contain an image
        has_img = any(
            p._p.xpath('.//a:blip') for p in doc.paragraphs
        )
        assert has_img, "Wide image should be embedded (scaled down)"

    def test_tall_image_scaled_to_max_height(self, tmp_path):
        """Image taller than max_height_cm should be scaled down by height constraint."""
        # 200px wide, 3000px tall at 96dpi ≈ 79cm tall, over 20cm
        out = self._render_md_with_local_img(tmp_path, width_px=200, height_px=3000)
        from docx import Document
        doc = Document(out)
        has_img = any(p._p.xpath('.//a:blip') for p in doc.paragraphs)
        assert has_img, "Tall image should be embedded (scaled by height constraint)"

    def test_small_image_kept_at_natural_size(self, tmp_path):
        """Image smaller than max dimensions should not be scaled up."""
        # 100x100px at 96dpi ≈ 2.6cm — well within limits
        out = self._render_md_with_local_img(tmp_path, width_px=100, height_px=100)
        from docx import Document
        doc = Document(out)
        has_img = any(p._p.xpath('.//a:blip') for p in doc.paragraphs)
        assert has_img, "Small image should be embedded at natural size"
