"""
Word Engine - Review State Manager (Phase 2)

Tracks the review loop state for a specific render version:
    QC → rerender → postfix → export → [review check]

State is recorded alongside existing render_state.json, using a separate
review_state.json to keep concerns cleanly separated.

Design decision:
  We chose a SEPARATE review_state.json (not extending render_state.json) because:
  1. render_state.json is append-only version history — mixing review status
     into it would make the version history messy to read.
  2. review_state.json is a MUTABLE current-status tracker — it gets updated
     each time the user advances through the loop, overwriting the same record.
  3. Keeps the two concerns cleanly separated: "what was rendered" vs "where am I now"

Schema of review_state.json:
{
  "current_version": 3,
  "review_rounds": 2,
  "steps": {
    "qc_passed": true,
    "rendered": true,
    "postfixed": false,
    "exported": false,
    "review_checked": false
  },
  "artifacts": {
    "docx": "documents/report_v3.docx",
    "pdf": null,
    "params_snapshot": "documents/params/params_v3.yaml"
  },
  "last_updated": "2026-04-12T01:40:00"
}
"""
import json
import os
from datetime import datetime


REVIEW_STATE_FILENAME = "review_state.json"


class ReviewStateError(Exception):
    """Raised when review state operations fail."""
    pass


class ReviewState:
    """
    Tracks the current review loop status for a word-engine project.

    Use this to understand where in the review cycle the document currently is:
      qc_passed → rendered → postfixed → exported → review_checked
    """

    STEPS = ["qc_passed", "rendered", "postfixed", "exported", "review_checked"]

    def __init__(self, project_dir):
        self.project_dir = os.path.abspath(project_dir)
        self.state_path = os.path.join(self.project_dir, REVIEW_STATE_FILENAME)
        self.state = self._load_or_init()

    def _load_or_init(self):
        if os.path.exists(self.state_path):
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "current_version": None,
            "review_rounds": 0,
            "steps": {step: False for step in self.STEPS},
            "artifacts": {
                "docx": None,
                "pdf": None,
                "params_snapshot": None,
            },
            "last_updated": None,
        }

    def _save(self):
        self.state["last_updated"] = datetime.now().isoformat()
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def start_new_round(self, version):
        """
        Start a new review round for a specific render version.
        Resets all step flags.

        Call this when beginning a new review cycle (after rerender).

        Args:
            version: The render version number (int).
        """
        self.state["current_version"] = version
        self.state["review_rounds"] += 1
        self.state["steps"] = {step: False for step in self.STEPS}
        self.state["artifacts"] = {"docx": None, "pdf": None, "params_snapshot": None}
        self._save()

    def mark_step(self, step, artifact_path=None):
        """
        Mark a review step as completed.

        Args:
            step: One of: qc_passed, rendered, postfixed, exported, review_checked
            artifact_path: (Optional) path to the output artifact for this step.
        """
        if step not in self.STEPS:
            raise ReviewStateError(
                f"Unknown step: '{step}'. Valid steps: {self.STEPS}"
            )
        self.state["steps"][step] = True

        if artifact_path:
            if step == "rendered":
                self.state["artifacts"]["docx"] = str(artifact_path)
            elif step == "exported":
                self.state["artifacts"]["pdf"] = str(artifact_path)

        self._save()

    def is_step_done(self, step):
        """Return True if the given step has been marked as completed."""
        return self.state["steps"].get(step, False)

    @property
    def current_version(self):
        return self.state["current_version"]

    @property
    def review_rounds(self):
        return self.state["review_rounds"]

    def next_step(self):
        """Return the name of the next incomplete step, or None if all done."""
        for step in self.STEPS:
            if not self.state["steps"].get(step, False):
                return step
        return None

    def is_complete(self):
        """Return True if all steps in the current round are marked done."""
        return all(self.state["steps"].get(s, False) for s in self.STEPS)

    def summary(self):
        """Return a human-readable review loop status summary."""
        ver = self.state["current_version"]
        rounds = self.state["review_rounds"]
        lines = [
            "=" * 50,
            f"  Review Loop Status",
            f"  Version: v{ver}   Round: #{rounds}",
            "=" * 50,
        ]
        for step in self.STEPS:
            done = self.state["steps"].get(step, False)
            icon = "✅" if done else "⏳"
            lines.append(f"  {icon} {step}")

        artifacts = self.state["artifacts"]
        if artifacts.get("docx"):
            lines.append(f"  docx: {artifacts['docx']}")
        if artifacts.get("pdf"):
            lines.append(f"  pdf:  {artifacts['pdf']}")

        next_step = self.next_step()
        if next_step:
            lines.append(f"\n  ➡ Next: {next_step}")
        else:
            lines.append("\n  🎉 Review round complete!")
        lines.append("=" * 50)
        return "\n".join(lines)
