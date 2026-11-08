import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

// Configuration
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const WORKBOOK_PATH = path.join(ROOT, "excel/controls_reporting_pack.xlsx");
const REPORT_PATH = path.join(ROOT, "examples/output/excel_verification.json");
const MODULE_ANCHOR = path.join(ROOT, ".work/package.json");
const FIRST_ROW = 7;
const TOLERANCE = 0.01;
const RATE_TOLERANCE = 1e-12;
const PREVIEW_PATH = path.join(ROOT, ".work/previews/SYSTEM_review.png");
const AUDIT_COLUMNS = {metric: "C", actual: "D", expected: "E", difference: "F", status: "G"};

const resolver = createRequire(MODULE_ANCHOR);
const { FileBlob, SpreadsheetFile } = await import(pathToFileURL(resolver.resolve("@oai/artifact-tool")).href);
const report = JSON.parse(await fs.readFile(REPORT_PATH, "utf8"));
let workbook;
try { workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(WORKBOOK_PATH)); }
catch (error) { console.error(String(error.message).slice(0, 1000)); process.exit(1); }
workbook.recalculate();
const audit = workbook.worksheets.getItem("Audit");
const lastRow = FIRST_ROW + report.comparisons - 1;
let comparisons = 0;
for (let row = FIRST_ROW; row <= lastRow; row++) {
  const {metric, actual, expected, difference, status} = Object.fromEntries(Object.entries(AUDIT_COLUMNS).map(([key, column]) => [key, audit.getRange(`${column}${row}`).values[0][0]]));
  const tolerance = metric === "rate" ? RATE_TOLERANCE : TOLERANCE;
  if (typeof actual !== "number" || Math.abs(actual - expected) > tolerance || Math.abs(difference) > tolerance || status !== "PASS") {
    throw new Error(`Reopened formula mismatch for ${metric}`);
  }
  comparisons++;
}
const preview = await workbook.render({sheetName: "SYSTEM-01", range: "A1:N20", scale: 1.5, format: "png"});
await fs.mkdir(path.dirname(PREVIEW_PATH), {recursive: true});
await fs.writeFile(PREVIEW_PATH, new Uint8Array(await preview.arrayBuffer()));
report.reopened_recalculation = {comparisons, mismatches: 0, engine: "@oai/artifact-tool"};
await fs.writeFile(REPORT_PATH, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report.reopened_recalculation));
