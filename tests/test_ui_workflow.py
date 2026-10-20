"""Behavioral checks for focused reviews and session-local interaction."""
from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import json
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from jobfit_ai.reports import analysis_text
from jobfit_ai.scoring import analyze_resume_fit


def demo(ui: AppTest) -> AppTest:
    next(button for button in ui.button if button.label == "Run demo ranking").click().run(timeout=30)
    # AppTest cannot execute custom JavaScript; exercise the explicit native alternative.
    ui.toggle(key="native_evidence").set_value(True).run(timeout=30)
    return ui


class FocusedReviewTests(unittest.TestCase):
    def test_component_payload_follows_candidate_and_contains_only_selected_evidence(self):
        ui = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py").run(timeout=30)
        next(button for button in ui.button if button.label == "Run demo ranking").click().run(timeout=30)
        analyses = ui.session_state["results"][0]
        for analysis in analyses[:2]:
            ui.selectbox(key="selected_analysis_id").set_value(analysis.analysis_id).run(timeout=30)
            self.assertEqual(list(ui.exception), [])
            component = ui.get("bidi_component")[0].proto
            payload = json.loads(component.json)
            self.assertEqual(payload["analysis_id"], analysis.analysis_id)
            self.assertEqual(payload["filename"], analysis.source_filename)
            self.assertEqual(payload["matches"][0]["evidence"], analysis.evidence_matches[0].evidence)
            self.assertTrue(component.isolate_styles)
            self.assertTrue(component.js_source_path.endswith(".js"))
            self.assertTrue(component.css_source_path.endswith(".css"))

    def test_exports_reused_for_view_changes_and_invalidated_for_analysis_mutations(self):
        with patch("jobfit_ai.reports.analysis_text", wraps=analysis_text) as report:
            ui = demo(AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py").run(timeout=30))
            self.assertEqual(report.call_count, 1)
            ui.selectbox(key="evidence_filter").set_value("Needs attention").run(timeout=30)
            ui.button_group(key="review_view").set_value("Tailoring").run(timeout=30)
            self.assertEqual(report.call_count, 1)
            analysis = next(item for item in ui.session_state["results"][0]
                            if item.analysis_id == ui.session_state["selected_analysis_id"])
            analysis.suggestions.append("A verified new edit")
            ui.run(timeout=30)
            self.assertEqual(report.call_count, 2)
            self.assertIn("A verified new edit", ui.session_state["report_payload"][1])
            another = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py").run(timeout=30)
            self.assertNotIn("report_payload", another.session_state)
            next(button for button in ui.button if button.label == "Clear session results").click().run(timeout=30)
            self.assertNotIn("report_payload", ui.session_state)

    def test_switching_candidates_updates_only_the_selected_report_without_rescoring(self):
        with patch("jobfit_ai.scoring.analyze_resume_fit", wraps=analyze_resume_fit) as scorer, \
                patch("jobfit_ai.reports.analysis_text", wraps=analysis_text) as report:
            ui = demo(AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py").run(timeout=30))
            analyses = sorted(ui.session_state["results"][0], key=lambda item: item.match_score, reverse=True)
            self.assertEqual(scorer.call_count, 4)
            self.assertEqual(report.call_args.args[0].analysis_id, analyses[0].analysis_id)
            self.assertEqual(report.call_count, 1)
            first_quote = analyses[0].evidence_matches[0].evidence
            self.assertIn(first_quote, [item.value for item in ui.text])

            ui.selectbox(key="selected_analysis_id").set_value(analyses[1].analysis_id).run(timeout=30)
            self.assertEqual(list(ui.exception), [])
            self.assertEqual(scorer.call_count, 4)
            self.assertEqual(report.call_count, 2)
            self.assertEqual(report.call_args.args[0].analysis_id, analyses[1].analysis_id)
            self.assertNotIn(first_quote, [item.value for item in ui.text])
            self.assertEqual(len(ui.get("download_button")), 2)
            names = [item.value for item in ui.subheader]
            self.assertIn(analyses[1].candidate_name, names)
            self.assertNotIn(analyses[0].candidate_name, names)

    def test_filtering_and_switching_views_do_not_rerun_analysis(self):
        with patch("jobfit_ai.scoring.analyze_resume_fit", wraps=analyze_resume_fit) as scorer:
            ui = demo(AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py").run(timeout=30))
            ui.selectbox(key="evidence_filter").set_value("Needs attention").run(timeout=30)
            self.assertEqual(list(ui.exception), [])
            evidence_table = ui.dataframe[-1].value
            self.assertTrue(set(evidence_table["Result"]) <= {"No evidence found", "Review required"})
            selected = ui.session_state["selected_requirement_index"]
            current = next(item for item in ui.session_state["results"][0]
                           if item.analysis_id == ui.session_state["selected_analysis_id"])
            self.assertIn(current.evidence_matches[selected].status, {"not_found", "review"})

            ui.session_state["review_view"] = "Tailoring"
            ui.run(timeout=30)
            self.assertIn("Tailoring notes", [item.value for item in ui.subheader])
            self.assertNotIn("Requirement evidence", [item.value for item in ui.subheader])
            ui.session_state["review_view"] = "Score details"
            ui.run(timeout=30)
            self.assertIn("Score details", [item.value for item in ui.subheader])
            self.assertNotIn("Tailoring notes", [item.value for item in ui.subheader])
            self.assertEqual(scorer.call_count, 4)
            self.assertEqual(list(ui.exception), [])

    def test_empty_filter_and_new_batch_reset_stale_selections(self):
        ui = demo(AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py").run(timeout=30))
        previous_id = ui.session_state["selected_analysis_id"]
        analyses = sorted(ui.session_state["results"][0], key=lambda item: item.match_score)
        ui.selectbox(key="selected_analysis_id").set_value(analyses[0].analysis_id).run(timeout=30)
        ui.selectbox(key="evidence_filter").set_value("Experience wording").run(timeout=30)
        self.assertEqual(list(ui.exception), [])
        self.assertTrue(any("No requirements in this category" in item.value for item in ui.caption))
        demo(ui)
        self.assertEqual(list(ui.exception), [])
        self.assertNotEqual(ui.session_state["selected_analysis_id"], previous_id)
        self.assertEqual(len(ui.get("download_button")), 2)

    def test_form_validation_does_not_discard_an_existing_review(self):
        ui = demo(AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py").run(timeout=30))
        previous = ui.session_state["selected_analysis_id"]
        next(button for button in ui.button if button.label == "Analyze uploaded resumes").click().run(timeout=30)
        self.assertTrue(any("Upload at least one" in item.value for item in ui.error))
        self.assertEqual(ui.session_state["selected_analysis_id"], previous)
        self.assertEqual(len(ui.get("download_button")), 2)

    def test_partial_upload_errors_survive_review_interactions_and_clear(self):
        files = [SimpleNamespace(name="valid.txt", getvalue=lambda: b"Jane Doe\nProjects\nBuilt Python SQL services."),
                 SimpleNamespace(name="broken.pdf", getvalue=lambda: b"not pdf")]
        with patch("streamlit.file_uploader", return_value=files):
            ui = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py")
            ui.session_state["job_description"] = "Build Python SQL services."
            ui.run(timeout=30)
            next(button for button in ui.button if button.label == "Analyze uploaded resumes").click().run(timeout=30)
            self.assertTrue(any("broken.pdf" in item.value for item in ui.error))
            ui.session_state["review_view"] = "Tailoring"
            ui.run(timeout=30)
            self.assertTrue(any("broken.pdf" in item.value for item in ui.error))
            next(button for button in ui.button if button.label == "Clear session results").click().run(timeout=30)
        self.assertEqual(list(ui.exception), [])
        self.assertEqual(len(ui.error), 0)
        self.assertEqual(len(ui.get("download_button")), 0)


if __name__ == "__main__":
    unittest.main()
