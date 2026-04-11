"""
Unit tests for the RenderState manager.

Tests cover: initialization, version increment, params snapshot, 
render registration, history queries, and the force-overwrite flag.
"""
import os
import pytest
from src.state_manager.render_state import RenderState, RenderStateError


@pytest.fixture
def state_dir(tmp_path):
    """Return a temporary project directory with a fresh RenderState."""
    return str(tmp_path)


@pytest.fixture
def dummy_params(tmp_path):
    """Create a minimal params.yaml file for snapshot testing."""
    p = tmp_path / "params.yaml"
    p.write_text("meta:\n  version: '1.0'\n", encoding="utf-8")
    return str(p)


class TestInitialization:
    def test_fresh_state_starts_at_version_zero(self, state_dir):
        state = RenderState(state_dir)
        assert state.current_version == 0

    def test_state_file_created_after_register(self, state_dir, dummy_params):
        state = RenderState(state_dir)
        version = state.next_version()
        snapshot = state.snapshot_params(dummy_params, version)
        state.register_render(version, snapshot, "/fake/report_v1.docx")
        assert os.path.exists(state.state_path)

    def test_state_persists_across_instances(self, state_dir, dummy_params):
        state1 = RenderState(state_dir)
        v = state1.next_version()
        snap = state1.snapshot_params(dummy_params, v)
        state1.register_render(v, snap, "/fake/report_v1.docx")

        state2 = RenderState(state_dir)
        assert state2.current_version == 1
        assert len(state2.state["history"]) == 1


class TestVersionIncrement:
    def test_version_increments_correctly(self, state_dir):
        state = RenderState(state_dir)
        assert state.next_version() == 1
        assert state.next_version() == 2
        assert state.next_version() == 3

    def test_version_counter_not_saved_until_register(self, state_dir):
        state = RenderState(state_dir)
        state.next_version()
        # Reload without saving — current_version not yet persisted
        state2 = RenderState(state_dir)
        assert state2.current_version == 0


class TestParamsSnapshot:
    def test_snapshot_creates_file(self, state_dir, dummy_params):
        state = RenderState(state_dir)
        snapshot_path = state.snapshot_params(dummy_params, 1)
        assert os.path.exists(snapshot_path)

    def test_snapshot_path_format(self, state_dir, dummy_params):
        state = RenderState(state_dir)
        snapshot_path = state.snapshot_params(dummy_params, 5)
        assert "params_v5.yaml" in snapshot_path

    def test_snapshot_duplicate_raises_error(self, state_dir, dummy_params):
        state = RenderState(state_dir)
        state.snapshot_params(dummy_params, 1)
        with pytest.raises(RenderStateError, match="already exists"):
            state.snapshot_params(dummy_params, 1)

    def test_snapshot_force_overwrites(self, state_dir, dummy_params):
        state = RenderState(state_dir)
        state.snapshot_params(dummy_params, 1)
        # Should not raise
        state.snapshot_params_force(dummy_params, 1)


class TestRegisterRender:
    def test_register_adds_to_history(self, state_dir, dummy_params):
        state = RenderState(state_dir)
        v = state.next_version()
        snap = state.snapshot_params(dummy_params, v)
        entry = state.register_render(v, snap, "/fake/report_v1.docx", label="test-label")
        assert entry["version"] == 1
        assert entry["label"] == "test-label"
        assert len(state.state["history"]) == 1

    def test_get_latest_entry(self, state_dir, dummy_params):
        state = RenderState(state_dir)
        for i in range(3):
            v = state.next_version()
            snap = state.snapshot_params(dummy_params, v)
            state.register_render(v, snap, f"/fake/report_v{v}.docx")
        latest = state.get_latest_entry()
        assert latest["version"] == 3

    def test_get_entry_by_version(self, state_dir, dummy_params):
        state = RenderState(state_dir)
        for i in range(3):
            v = state.next_version()
            snap = state.snapshot_params(dummy_params, v)
            state.register_render(v, snap, f"/fake/report_v{v}.docx")
        entry = state.get_entry_by_version(2)
        assert entry is not None
        assert entry["version"] == 2

    def test_get_nonexistent_version_returns_none(self, state_dir):
        state = RenderState(state_dir)
        assert state.get_entry_by_version(99) is None

    def test_get_latest_on_empty_history_returns_none(self, state_dir):
        state = RenderState(state_dir)
        assert state.get_latest_entry() is None


class TestVersionedDocxPath:
    def test_versioned_path_format(self, state_dir):
        state = RenderState(state_dir)
        path = state.versioned_docx_path(3)
        assert "report_v3.docx" in path
