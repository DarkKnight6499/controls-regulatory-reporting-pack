import ast
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from controls_pack.common import read_csv, sha256, write_csv, write_json
from controls_pack.config import DATA_DIR, ROOT
from controls_pack.report import run, verify_artifact, verify_manifest
from controls_pack.controls import Evidence
from controls_pack.synthetic import generate_snapshot

# Configuration
WORK_DIR = ROOT / ".work"
SUMMARY_RECONCILIATIONS = "failed_reconciliations"
EXCEPTION_CONTROL = "control_id"
JOURNAL_ID = "journal_id"
DEBIT = "debit"
CREDIT = "credit"
NETWORK_MODULES = {"requests", "urllib", "http", "socket", "httpx", "aiohttp"}
EVIDENCE_ID = "evidence_id"
ARTIFACT_HASH = "artifact_sha256"
MANIFEST_FILES = "files"
MANIFEST_PATH = "path"
MANIFEST_HASH = "sha256"
EVIDENCE_STATUS = "evidence_status"


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK_DIR.mkdir(exist_ok=True)

    def test_snapshot_is_seeded_and_manifest_verifies(self):
        verify_manifest(DATA_DIR)
        with tempfile.TemporaryDirectory(dir=WORK_DIR) as temporary:
            snapshot = Path(temporary) / "snapshot"
            generate_snapshot(snapshot)
            self.assertEqual(sha256(DATA_DIR / "manifest.json"), sha256(snapshot / "manifest.json"))

    def test_full_report_reconciles_and_contains_planted_exceptions(self):
        with tempfile.TemporaryDirectory(dir=WORK_DIR) as temporary:
            output = Path(temporary)
            summary = run(output=output)
            self.assertEqual(summary.failed_reconciliations, 0)
            self.assertEqual((summary.reserve_days, summary.lease_count, summary.lease_periods), (10, 3, 54))
            self.assertEqual((summary.population_size, summary.sample_size, summary.sample_failures), (43, 12, 5))
            exceptions = read_csv(output / "daily_exception_log.csv")
            controls = {item[EXCEPTION_CONTROL] for item in exceptions}
            self.assertTrue({"RESERVE", "CAPITAL", "VARIANCE", "COVENANT", "EVIDENCE", "VENDOR"} <= controls)
            totals = {}
            for row in read_csv(output / "lease_journals.csv"):
                totals[row[JOURNAL_ID]] = totals.get(row[JOURNAL_ID], 0) + float(row[DEBIT]) - float(row[CREDIT])
            self.assertTrue(all(abs(value) < .000001 for value in totals.values()))

    def test_manifest_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=WORK_DIR) as temporary:
            snapshot = Path(temporary)
            generate_snapshot(snapshot)
            with (snapshot / "reserve_ledger.csv").open("a", encoding="utf-8") as handle:
                handle.write("tampered\n")
            with self.assertRaisesRegex(ValueError, "integrity failure"):
                verify_manifest(snapshot)

    def test_artifact_hash_and_path_controls(self):
        evidence = Evidence("X", "2026-10-30", "C", "A", "B", "2026-10-30", "2026-10-30",
                            "2026-10-30", "../outside.json", "a" * 64)
        self.assertIn("escapes", verify_artifact(evidence, ROOT))

    def test_bad_covenant_artifact_cannot_receive_evidence_pass(self):
        with tempfile.TemporaryDirectory(dir=WORK_DIR) as temporary:
            snapshot = Path(temporary) / "snapshot"
            generate_snapshot(snapshot)
            population_path = snapshot / "control_population.csv"
            population = read_csv(population_path)
            for item in population:
                if item[EVIDENCE_ID] == "E041":
                    item[ARTIFACT_HASH] = "0" * 64
            write_csv(population_path, population)
            manifest_path = snapshot / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in manifest[MANIFEST_FILES]:
                if item[MANIFEST_PATH] == population_path.name:
                    item[MANIFEST_HASH] = sha256(population_path)
            write_json(manifest_path, manifest)
            output = Path(temporary) / "output"
            run(directory=snapshot, output=output)
            results = [item for item in read_csv(output / "covenant_compliance.csv") if item[EVIDENCE_ID] == "E041"]
            self.assertEqual(len(results), 3)
            self.assertTrue(all(item[EVIDENCE_STATUS] == "FAIL" for item in results))

    def test_library_has_no_network_imports(self):
        for path in (ROOT / "python" / "controls_pack").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [item.name for item in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""]
                self.assertFalse({name.split(".")[0] for name in names} & NETWORK_MODULES, path.name)
