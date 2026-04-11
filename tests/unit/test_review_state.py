"""
Unit tests for the ReviewState manager.

Tests cover: initialization, start_new_round, mark_step, step status checks,
next_step logic, is_complete, artifact tracking, and summary output.
"""
import os
import pytest
from src.state_manager.review_state import ReviewState, ReviewStateError


@pytest.fixture
def review_dir(tmp_path):
    return str(tmp_path)


class TestInitialization:
    def test_fresh_state_has_no_version(self, review_dir):
        r = ReviewState(review_dir)
        assert r.current_version is None

    def test_fresh_state_zero_rounds(self, review_dir):
        r = ReviewState(review_dir)
        assert r.review_rounds == 0

    def test_fresh_state_all_steps_false(self, review_dir):
        r = ReviewState(review_dir)
        for step in ReviewState.STEPS:
            assert not r.is_step_done(step)

    def test_state_file_created_on_save(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        assert os.path.exists(r.state_path)

    def test_state_persists_across_instances(self, review_dir):
        r1 = ReviewState(review_dir)
        r1.start_new_round(3)
        r1.mark_step("qc_passed")
        r2 = ReviewState(review_dir)
        assert r2.current_version == 3
        assert r2.is_step_done("qc_passed")


class TestStartNewRound:
    def test_round_increments(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        r.start_new_round(2)
        assert r.review_rounds == 2

    def test_start_new_round_resets_steps(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        r.mark_step("qc_passed")
        r.start_new_round(2)
        assert not r.is_step_done("qc_passed")

    def test_start_new_round_sets_version(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(7)
        assert r.current_version == 7


class TestMarkStep:
    def test_mark_valid_step(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        r.mark_step("qc_passed")
        assert r.is_step_done("qc_passed")

    def test_mark_invalid_step_raises(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        with pytest.raises(ReviewStateError, match="Unknown step"):
            r.mark_step("nonexistent")

    def test_mark_rendered_records_docx(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(2)
        r.mark_step("rendered", artifact_path="/path/to/report_v2.docx")
        assert r.state["artifacts"]["docx"] == "/path/to/report_v2.docx"

    def test_mark_exported_records_pdf(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(2)
        r.mark_step("exported", artifact_path="/path/to/report_v2.pdf")
        assert r.state["artifacts"]["pdf"] == "/path/to/report_v2.pdf"


class TestNextStep:
    def test_next_step_initial(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        assert r.next_step() == "qc_passed"

    def test_next_step_after_qc(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        r.mark_step("qc_passed")
        assert r.next_step() == "rendered"

    def test_next_step_all_done_returns_none(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        for step in ReviewState.STEPS:
            r.mark_step(step)
        assert r.next_step() is None


class TestIsComplete:
    def test_not_complete_initially(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        assert not r.is_complete()

    def test_complete_after_all_steps(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        for step in ReviewState.STEPS:
            r.mark_step(step)
        assert r.is_complete()


class TestSummary:
    def test_summary_contains_version(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(3)
        summary = r.summary()
        assert "v3" in summary

    def test_summary_shows_next_step(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        r.mark_step("qc_passed")
        summary = r.summary()
        assert "rendered" in summary

    def test_summary_complete_message(self, review_dir):
        r = ReviewState(review_dir)
        r.start_new_round(1)
        for step in ReviewState.STEPS:
            r.mark_step(step)
        summary = r.summary()
        assert "complete" in summary.lower() or "🎉" in summary
