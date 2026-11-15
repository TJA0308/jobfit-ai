import unittest

from scripts.evaluate_evidence import evaluate_evidence


class EvaluationDiagnosticsTests(unittest.TestCase):
    def test_confusion_and_abstention_expose_a_mislabeled_case(self):
        dataset = {"cases": [
            {"id": "absent", "group": "negative", "requirement": "Python SQL",
             "resume": "Experience\nPainted theater sets.", "expected_evidence": None,
             "expected_status": "not_found"},
            {"id": "mention", "group": "skills", "requirement": "Python SQL",
             "resume": "Skills\nPython SQL", "expected_evidence": "Python SQL",
             "expected_status": "supported"},
        ]}
        result = evaluate_evidence(dataset)
        self.assertEqual(result["status_confusion_expected_by_predicted"]["supported"], {"partial": 1})
        self.assertEqual(result["by_group"]["skills"]["status_agreement"], 0)
        self.assertEqual(result["abstention_precision"], 1)
        self.assertEqual(result["abstention_recall"], 1)
        self.assertEqual(result["status_agreement"], .5)

    def test_absent_denominators_are_null(self):
        result = evaluate_evidence({"cases": [
            {"id": "mention", "group": "skills", "requirement": "Python SQL",
             "resume": "Skills\nPython SQL", "expected_evidence": "Python SQL",
             "expected_status": "partial"},
        ]})
        self.assertIsNone(result["abstention_precision"])
        self.assertIsNone(result["abstention_recall"])
