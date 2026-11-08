"""Set workbook author metadata and inspect saved OOXML without extra libraries."""
import argparse
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

# Configuration
ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = ROOT / "excel" / "controls_reporting_pack.xlsx"
REPORT_PATH = ROOT / "examples" / "output" / "excel_verification.json"
INPUT_PATH = ROOT / "examples" / "output" / "workbook_inputs.json"
WORK_DIR = ROOT / ".work"
AUTHOR = "Yazad Madan"
TOLERANCE = 0.01
RATE_TOLERANCE = 1e-12
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELATIONSHIPS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOCUMENT_RELATIONSHIPS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CONTENT_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
CORE = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC = "http://purl.org/dc/elements/1.1/"
CORE_TYPE = "application/vnd.openxmlformats-package.core-properties+xml"
CORE_RELATIONSHIP = "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"
EXPECTED_SHEETS = {"Reserve", "OFFICE-01", "EQUIP-01", "SYSTEM-01", "Reserve Ledger", "Lease Inputs", "Audit", "ReadMe"}
NS = {"m": MAIN, "r": DOCUMENT_RELATIONSHIPS, "p": RELATIONSHIPS}
AUDIT_FIRST_ROW = 7
AUDIT_ACTUAL_COLUMN = "D"
AUDIT_EXPECTED_COLUMN = "E"
AUDIT_STATUS_COLUMN = "G"
SCHEDULE_COLUMN = "A"
KEY_COLUMN = "B"
METRIC_COLUMN = "C"
DATE_FIELD = "date"
LEASE_ID_FIELD = "lease_id"
PERIOD_FIELD = "period"
RESERVE_EXPECTED_FIELD = "reserve_expected"
LEASE_EXPECTED_FIELD = "lease_expected"


def xml_bytes(root):
    namespace = root.tag.split("}")[0].lstrip("{")
    ET.register_namespace("", namespace)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def finalize(path=WORKBOOK_PATH):
    WORK_DIR.mkdir(exist_ok=True)
    with ZipFile(path) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    core = ET.Element(f"{{{CORE}}}coreProperties")
    ET.SubElement(core, f"{{{DC}}}creator").text = AUTHOR
    ET.SubElement(core, f"{{{CORE}}}lastModifiedBy").text = AUTHOR
    contents["docProps/core.xml"] = xml_bytes(core)
    types = ET.fromstring(contents["[Content_Types].xml"])
    if not any(item.get("PartName") == "/docProps/core.xml" for item in types):
        ET.SubElement(types, f"{{{CONTENT_TYPES}}}Override", PartName="/docProps/core.xml", ContentType=CORE_TYPE)
    contents["[Content_Types].xml"] = xml_bytes(types)
    relationships = ET.fromstring(contents["_rels/.rels"])
    if not any(item.get("Type") == CORE_RELATIONSHIP for item in relationships):
        ET.SubElement(relationships, f"{{{RELATIONSHIPS}}}Relationship", Id="rIdCoreProperties", Type=CORE_RELATIONSHIP, Target="docProps/core.xml")
    contents["_rels/.rels"] = xml_bytes(relationships)
    book = ET.fromstring(contents["xl/workbook.xml"])
    calculation = book.find(f"{{{MAIN}}}calcPr")
    if calculation is None:
        calculation = ET.SubElement(book, f"{{{MAIN}}}calcPr")
    calculation.set("calcMode", "auto")
    calculation.set("fullCalcOnLoad", "1")
    contents["xl/workbook.xml"] = xml_bytes(book)
    temporary = WORK_DIR / "workbook_metadata.xlsx"
    with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
        for name, content in contents.items():
            archive.writestr(name, content)
    temporary.replace(path)


def inspect_saved(path=WORKBOOK_PATH):
    inputs = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    expected_values = {}
    for item in inputs[RESERVE_EXPECTED_FIELD]:
        for metric, expected in item.items():
            if metric != DATE_FIELD:
                expected_values[("Reserve", item[DATE_FIELD], metric)] = expected
    for item in inputs[LEASE_EXPECTED_FIELD]:
        for metric, expected in item.items():
            if isinstance(expected, (int, float)) and metric != PERIOD_FIELD:
                expected_values[(item[LEASE_ID_FIELD], str(item[PERIOD_FIELD]), metric)] = expected
    with ZipFile(path) as archive:
        book = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.get("Id"): item.get("Target") for item in relationships}
        sheets = {}
        for item in book.findall("m:sheets/m:sheet", NS):
            target = targets[item.get(f"{{{DOCUMENT_RELATIONSHIPS}}}id")]
            sheets[item.get("name")] = target.lstrip("/") if target.startswith("/") else f"xl/{target}"
        if set(sheets) != EXPECTED_SHEETS:
            raise ValueError("Unexpected worksheet set")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(node.itertext()) for node in shared]
        errors = []
        for name, target in sheets.items():
            worksheet = ET.fromstring(archive.read(target))
            if worksheet.findall(".//m:tabColor", NS):
                raise ValueError("Unexpected tab color")
            for cell in worksheet.findall(".//m:c", NS):
                if cell.get("t") == "e":
                    errors.append(f"{name}!{cell.get('r')}")
        if errors:
            raise ValueError(f"Saved formula errors: {errors[:5]}")
        audit = ET.fromstring(archive.read(sheets["Audit"]))
        comparisons = 0
        compared_keys = set()
        max_difference = 0.0
        for row in audit.findall("m:sheetData/m:row", NS):
            row_number = int(row.get("r"))
            if row_number < AUDIT_FIRST_ROW:
                continue
            cells = {cell.get("r"): cell for cell in row}
            actual_cell = cells.get(f"{AUDIT_ACTUAL_COLUMN}{row_number}")
            expected_cell = cells.get(f"{AUDIT_EXPECTED_COLUMN}{row_number}")
            if actual_cell is None or expected_cell is None or expected_cell.find("m:v", NS) is None:
                continue
            if actual_cell.find("m:f", NS) is None:
                raise ValueError("Audit live result is not a formula")
            actual = float(actual_cell.findtext("m:v", namespaces=NS))
            expected = float(expected_cell.findtext("m:v", namespaces=NS))
            key_values = []
            for column in (SCHEDULE_COLUMN, KEY_COLUMN, METRIC_COLUMN):
                cell = cells[f"{column}{row_number}"]
                text = cell.findtext("m:v", namespaces=NS)
                key_values.append(strings[int(text)] if cell.get("t") == "s" else text)
            key = tuple(key_values)
            tolerance = RATE_TOLERANCE if key[-1] == "rate" else TOLERANCE
            if key not in expected_values or abs(expected - expected_values[key]) > tolerance:
                raise ValueError(f"Workbook snapshot does not match current Python outputs: {key}")
            if key in compared_keys:
                raise ValueError(f"Duplicate workbook comparison: {key}")
            compared_keys.add(key)
            difference = abs(actual - expected)
            max_difference = max(max_difference, difference)
            if difference > tolerance:
                raise ValueError(f"Saved reconciliation failed at row {row_number}")
            comparisons += 1
        styles = ET.fromstring(archive.read("xl/styles.xml"))
        if styles.findall("m:fonts/m:font/m:color", NS):
            raise ValueError("Unexpected font color")
        if any(item.get("fillId", "0") != "0" for item in styles.findall("m:cellXfs/m:xf", NS)):
            raise ValueError("Unexpected cell fill")
        core = ET.fromstring(archive.read("docProps/core.xml"))
        if core.findtext(f"{{{DC}}}creator") != AUTHOR:
            raise ValueError("Workbook author does not match required author")
        if book.find("m:calcPr", NS).get("calcMode") != "auto":
            raise ValueError("Workbook calculation is not automatic")
        if any("externalLinks" in name or "vbaProject" in name for name in archive.namelist()):
            raise ValueError("Unexpected external link or macro")
    if comparisons == 0:
        raise ValueError("No saved reconciliation values found")
    if compared_keys != set(expected_values):
        raise ValueError("Workbook does not cover all expected Python values")
    return {"cached_comparisons": comparisons, "max_absolute_difference": max_difference,
            "saved_errors": errors, "author": AUTHOR, "automatic_calculation": True,
            "formatting": "No tab colors, applied cell fills or font colors"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true", help="Set author and automatic calculation before inspection")
    arguments = parser.parse_args()
    if arguments.finalize:
        finalize()
    result = inspect_saved()
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    report["saved_file_checks"] = result
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
