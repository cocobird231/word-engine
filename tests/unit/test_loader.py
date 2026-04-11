"""Unit tests for the loader module."""
import os
import pytest
import tempfile
from src.loader.loader import load_markdown, load_params, load_project, scan_assets, LoadError


class TestLoadMarkdown:
    def test_load_existing_file(self, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\nWorld", encoding="utf-8")
        result = load_markdown(str(md_file))
        assert result == "# Hello\nWorld"

    def test_load_nonexistent_file(self):
        with pytest.raises(LoadError, match="Markdown file not found"):
            load_markdown("/nonexistent/path.md")

    def test_load_utf8_content(self, tmp_path):
        md_file = tmp_path / "zh.md"
        md_file.write_text("# 標題\n中文內容", encoding="utf-8")
        result = load_markdown(str(md_file))
        assert "標題" in result


class TestLoadParams:
    def test_load_valid_yaml(self, tmp_path):
        yaml_file = tmp_path / "params.yaml"
        yaml_file.write_text("meta:\n  version: '1.0'\n", encoding="utf-8")
        result = load_params(str(yaml_file))
        assert result["meta"]["version"] == "1.0"

    def test_load_nonexistent_yaml(self):
        with pytest.raises(LoadError, match="Params file not found"):
            load_params("/nonexistent/params.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text(":\n  bad:\n    - [unclosed", encoding="utf-8")
        with pytest.raises(LoadError, match="Failed to parse YAML"):
            load_params(str(yaml_file))

    def test_load_non_dict_yaml(self, tmp_path):
        yaml_file = tmp_path / "list.yaml"
        yaml_file.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(LoadError, match="root must be a mapping"):
            load_params(str(yaml_file))


class TestScanAssets:
    def test_scan_existing_dir(self, tmp_path):
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "img1.png").write_text("fake")
        (assets / "img2.jpg").write_text("fake")
        result = scan_assets(str(assets))
        assert len(result) == 2

    def test_scan_nonexistent_dir(self):
        result = scan_assets("/nonexistent/assets")
        assert result == []


class TestLoadProject:
    def test_load_project_success(self, tmp_path):
        md_file = tmp_path / "refine.md"
        md_file.write_text("# Test", encoding="utf-8")
        params_file = tmp_path / "params.yaml"
        params_file.write_text(
            "meta:\n  version: '1.0'\npaths:\n  assets_dir: './assets'\n",
            encoding="utf-8",
        )
        result = load_project(str(md_file), str(params_file))
        assert result["markdown"] == "# Test"
        assert result["params"]["meta"]["version"] == "1.0"
        assert "md_path" in result["metadata"]
