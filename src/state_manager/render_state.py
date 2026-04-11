"""
Word Engine - Render State Manager (Phase 2)

Manages versioned render history for a project.
Each render invocation gets an auto-incremented version number,
and all artifacts (params snapshot, docx, logs) are preserved per version.

State is persisted in `render_state.json` at the project root.
"""
import json
import os
import shutil
from datetime import datetime


STATE_FILENAME = "render_state.json"


class RenderStateError(Exception):
    """Raised for state management failures."""
    pass


class RenderState:
    """
    Manages versioned render state for a word-engine project.

    Attributes:
        project_dir: Root directory of the project being rendered.
        state_path: Absolute path to render_state.json.
        state: Dict representing the current state.
    """

    def __init__(self, project_dir):
        self.project_dir = os.path.abspath(project_dir)
        self.state_path = os.path.join(self.project_dir, STATE_FILENAME)
        self.state = self._load_or_init()

    def _load_or_init(self):
        """Load existing state or initialize a new one."""
        if os.path.exists(self.state_path):
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "current_version": 0,
            "history": [],
        }

    def _save(self):
        """Persist current state to disk."""
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    @property
    def current_version(self):
        return self.state["current_version"]

    def next_version(self):
        """Increment version number and return the new value."""
        self.state["current_version"] += 1
        return self.state["current_version"]

    def snapshot_params(self, params_path, version):
        """
        Copy the current params.yaml to a versioned snapshot in documents/params/.

        Args:
            params_path: Source path to the params.yaml being used for this render.
            version: The version number for this render.

        Returns:
            Absolute path to the snapshot file.
        """
        params_archive_dir = os.path.join(self.project_dir, "documents", "params")
        os.makedirs(params_archive_dir, exist_ok=True)

        snapshot_name = f"params_v{version}.yaml"
        snapshot_path = os.path.join(params_archive_dir, snapshot_name)

        if os.path.exists(snapshot_path):
            raise RenderStateError(
                f"Params snapshot already exists for version {version}: {snapshot_path}. "
                "Use --force to overwrite, or this version was already rendered."
            )

        shutil.copy2(params_path, snapshot_path)
        return snapshot_path

    def snapshot_params_force(self, params_path, version):
        """
        Copy params.yaml to versioned snapshot, overwriting if already exists.
        """
        params_archive_dir = os.path.join(self.project_dir, "documents", "params")
        os.makedirs(params_archive_dir, exist_ok=True)

        snapshot_name = f"params_v{version}.yaml"
        snapshot_path = os.path.join(params_archive_dir, snapshot_name)
        shutil.copy2(params_path, snapshot_path)
        return snapshot_path

    def register_render(self, version, params_snapshot_path, output_docx, render_log=None, label=None):
        """
        Record a completed render in the history.

        Args:
            version: The version number of this render.
            params_snapshot_path: Path to the params snapshot used.
            output_docx: Path to the rendered docx.
            render_log: (Optional) Path to the render log.
            label: (Optional) Human-readable label for this render version.
        """
        entry = {
            "version": version,
            "label": label or f"v{version}",
            "params_snapshot": str(params_snapshot_path),
            "output_docx": str(output_docx),
            "render_log": str(render_log) if render_log else None,
            "timestamp": datetime.now().isoformat(),
        }
        self.state["history"].append(entry)
        self._save()
        return entry

    def versioned_docx_path(self, version, output_dir=None):
        """
        Derive the versioned docx output path for a given version.

        Args:
            version: The render version number.
            output_dir: Directory to place the versioned docx. Defaults to documents/.

        Returns:
            Absolute path for the versioned docx file.
        """
        if output_dir is None:
            output_dir = os.path.join(self.project_dir, "documents")
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, f"report_v{version}.docx")

    def get_latest_entry(self):
        """Return the most recent render history entry, or None."""
        if not self.state["history"]:
            return None
        return self.state["history"][-1]

    def get_entry_by_version(self, version):
        """Return the history entry for a specific version, or None."""
        for entry in self.state["history"]:
            if entry["version"] == version:
                return entry
        return None

    def summary(self):
        """Return a human-readable summary of the render state."""
        lines = [
            f"Render State: {self.state_path}",
            f"Current version: v{self.current_version}",
            f"Total renders: {len(self.state['history'])}",
        ]
        if self.state["history"]:
            latest = self.state["history"][-1]
            lines.append(f"Latest: v{latest['version']} ({latest['timestamp']}) → {latest['output_docx']}")
        return "\n".join(lines)
