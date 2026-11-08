import importlib.util
import unittest

from controls_pack.config import ROOT

# Configuration
VERIFIER_PATH = ROOT / "scripts" / "verify_workbook.py"


class WorkbookTests(unittest.TestCase):
    def test_saved_workbook_formulas_reconcile_and_metadata_is_correct(self):
        spec = importlib.util.spec_from_file_location("workbook_verifier", VERIFIER_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.inspect_saved()
        self.assertGreater(result["cached_comparisons"], 0)
        self.assertLessEqual(result["max_absolute_difference"], module.TOLERANCE)
        self.assertEqual(result["saved_errors"], [])
