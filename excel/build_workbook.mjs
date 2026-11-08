import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

// Configuration
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const INPUT_PATH = path.join(ROOT, "examples/output/workbook_inputs.json");
const OUTPUT_PATH = path.join(ROOT, "excel/controls_reporting_pack.xlsx");
const VERIFICATION_PATH = path.join(ROOT, "examples/output/excel_verification.json");
const PREVIEW_DIR = path.join(ROOT, ".work/previews");
const MODULE_ANCHOR = path.join(ROOT, ".work/package.json");
const TOLERANCE = 0.01;
const RATE_TOLERANCE = 1e-12;
const REDUCTION = 0.01;
const HEADER_ROW = 6;
const FIRST_ROW = 7;
const MONEY_FORMAT = '#,##0.00;(#,##0.00);0.00';
const DATE_FORMAT = "mm/dd/yy";
const SOURCE_URL = "https://www.ecfr.gov/current/title-17/section-240.15c3-3a";
const FASB_URL = "https://storage.fasb.org/ASU%202016-02_Section%20A.pdf";
const INPUT_FIELDS = ["record_id", "date", "category", "amount", "age_days", "market_value", "secured", "collectible", "affiliate", "account_type", "transfer_confirmed"];
const INPUT_HEADERS = ["Record ID", "Date", "Category", "Amount USD", "Age days", "Market USD", "Secured", "Collectible", "Affiliate", "Account type", "Transfer confirmed"];
const INPUT_COLUMNS = {record_id: "A", date: "B", category: "C", amount: "D", age_days: "E", market_value: "F", secured: "G", collectible: "H", affiliate: "I", account_type: "J", transfer_confirmed: "K", item: "L", eligible: "M", credit: "N", debit: "O", valid: "P"};
const ITEM_MAP = {free_credit: 1, customer_draft: 1, overdrawn_check: 1, borrowed_money: 2, securities_loaned: 3, failed_receive: 4, principal_sale: 5, distribution: 6, short_count: 7, suspense: 8, transfer: 9, customer_debit: 10, securities_borrowed: 11, failed_deliver: 12};
const RESERVE_COLUMNS = {credits: "B", raw_debits: "C", item10: "D", debit_reduction: "E", allowed_debits: "F", required_reserve: "G", eligible_deposit: "H", shortfall: "I", excess_deposit: "J"};
const LEASE_COLUMNS = {period: "A", payment: "B", rate: "C", opening_liability: "D", remeasurement: "E", interest: "F", closing_liability: "G", opening_rou: "H", rou_adjustment: "I", rou_amortization: "J", closing_rou: "K", lease_expense: "L"};
const PARAMETER_OFFSETS = {rate: 1, prepaid: 2, incentive: 3, costs: 4, term: 5, modPeriod: 6, revisedRate: 7, initialLiability: 8, initialRou: 9, revisedLiability: 10, remainingPeriods: 11, remainingCash: 12, originalCash: 13};

const resolver = createRequire(MODULE_ANCHOR);
const {Workbook, SpreadsheetFile} = await import(pathToFileURL(resolver.resolve("@oai/artifact-tool")).href);
const inputs = JSON.parse(await fs.readFile(INPUT_PATH, "utf8"));
const workbook = Workbook.create();
const reserve = workbook.worksheets.add("Reserve");
const leaseSheets = new Map(inputs.leases.map(contract => [contract.lease_id, workbook.worksheets.add(contract.lease_id)]));
const ledger = workbook.worksheets.add("Reserve Ledger");
const leaseInputs = workbook.worksheets.add("Lease Inputs");
const audit = workbook.worksheets.add("Audit");
const readme = workbook.worksheets.add("ReadMe");
const formulaChecks = [];
const leaseMetadata = new Map();

function value(sheet, address, input) { sheet.getRange(address).values = [[input]]; }
function formula(sheet, address, input) { sheet.getRange(address).formulas = [[input]]; }
function serialDate(iso) { return new Date(`${iso}T00:00:00.000Z`); }
function baseStyle(sheet, lastColumn, lastRow, title) {
  const range = sheet.getRange(`A1:${lastColumn}${lastRow}`);
  range.format.font = {name: "Arial", size: 10};
  range.format.rowHeight = 19;
  range.format.columnWidth = 17;
  range.format.verticalAlignment = "center";
  sheet.showGridLines = false;
  value(sheet, "A2", title);
  sheet.getRange(`A2:${lastColumn}2`).format.font = {name: "Arial", size: 14, bold: true};
  sheet.getRange("A2").format.rowHeight = 25;
}
function headers(sheet, address, labels) {
  sheet.getRange(address).values = [labels];
  sheet.getRange(address).format.font = {name: "Arial", size: 10, bold: true};
  sheet.getRange(address).format.wrapText = true;
  sheet.getRange(address).format.rowHeight = 34;
}
function check(schedule, key, metric, cell, expected) {
  formulaChecks.push({schedule, key: String(key), metric, cell, expected});
}

baseStyle(reserve, "K", FIRST_ROW + inputs.reserve_expected.length, "Customer reserve (USD)");
value(reserve, "A3", "Item 10 reduction");
value(reserve, "B3", REDUCTION);
reserve.getRange("B3").setNumberFormat("0.0%");
value(reserve, "D3", "Synthetic. Basic method. Internal daily monitoring.");
headers(reserve, "A6:K6", ["Date", "Credits", "Raw debits", "Item 10", "Debit reduction", "Allowed debits", "Required reserve", "Eligible deposit", "Shortfall", "Excess deposit", "Source rows"]);
reserve.getRange(`B7:J${FIRST_ROW + inputs.reserve_expected.length - 1}`).setNumberFormat(MONEY_FORMAT);
reserve.getRange("A1:A17").format.columnWidth = 14;
reserve.freezePanes.freezeRows(HEADER_ROW);

const lastLedgerRow = FIRST_ROW + inputs.reserve_ledger.length - 1;
baseStyle(ledger, "T", lastLedgerRow, "Synthetic reserve ledger (USD)");
value(ledger, "A3", "Synthetic seed 8421533. Restricted cash accounts. Items 13 to 15 unsupported.");
value(ledger, "A4", SOURCE_URL);
headers(ledger, "A6:P6", [...INPUT_HEADERS, "Item", "Eligible amount", "Credit", "Debit", "Valid input"]);
ledger.getRange(`A7:K${lastLedgerRow}`).values = inputs.reserve_ledger.map(row => INPUT_FIELDS.map(field => field === "date" ? serialDate(row[field]) : row[field]));
ledger.getRange(`B7:B${lastLedgerRow}`).setNumberFormat(DATE_FORMAT);
ledger.getRange(`D7:D${lastLedgerRow}`).setNumberFormat(MONEY_FORMAT);
ledger.getRange(`F7:F${lastLedgerRow}`).setNumberFormat(MONEY_FORMAT);
ledger.getRange(`M7:O${lastLedgerRow}`).setNumberFormat(MONEY_FORMAT);
ledger.getRange(`A7:A${lastLedgerRow}`).format.columnWidth = 25;
ledger.getRange(`C7:C${lastLedgerRow}`).format.columnWidth = 24;
headers(ledger, "S6:T6", ["Category", "Exhibit item"]);
const categories = Object.entries(ITEM_MAP);
ledger.getRange(`S7:T${FIRST_ROW + categories.length - 1}`).values = categories;
ledger.getRange(`S1:S${lastLedgerRow}`).format.columnWidth = 24;
for (let row = FIRST_ROW; row <= lastLedgerRow; row++) {
  formula(ledger, `L${row}`, `=VLOOKUP(C${row},$S$7:$T$${FIRST_ROW + categories.length - 1},2,FALSE)`);
  formula(ledger, `P${row}`, `=AND(LEN(A${row})>0,COUNTIF($A$7:$A$${lastLedgerRow},A${row})=1,ISNUMBER(B${row}),ISNUMBER(D${row}),D${row}>=0,ISNUMBER(E${row}),E${row}>=0,INT(E${row})=E${row},ISNUMBER(F${row}),F${row}>=0,ISLOGICAL(G${row}),ISLOGICAL(H${row}),ISLOGICAL(I${row}),ISLOGICAL(K${row}),OR(L${row}<>10,J${row}="cash"))`);
  const eligible = `IF(L${row}=3,MAX(D${row},F${row}),IF(AND(L${row}=4,E${row}>30),MAX(D${row},F${row}),IF(AND(L${row}>=6,L${row}<=8),IF(E${row}>30,F${row},0),IF(L${row}=9,IF(AND(E${row}>40,NOT(K${row})),F${row},0),IF(L${row}=10,IF(AND(G${row},H${row},NOT(I${row})),D${row},0),IF(L${row}=12,IF(E${row}<=30,D${row},0),D${row}))))))`;
  formula(ledger, `M${row}`, `=IF(P${row},${eligible},NA())`);
  formula(ledger, `N${row}`, `=IF(L${row}<=9,M${row},0)`);
  formula(ledger, `O${row}`, `=IF(L${row}>=10,M${row},0)`);
}
ledger.freezePanes.freezeRows(HEADER_ROW);
ledger.freezePanes.freezeColumns(3);
for (const [index, expected] of inputs.reserve_expected.entries()) {
  const row = FIRST_ROW + index;
  value(reserve, `A${row}`, serialDate(expected.date));
  formula(reserve, `B${row}`, `=SUMIF('Reserve Ledger'!$B$7:$B$${lastLedgerRow},A${row},'Reserve Ledger'!$N$7:$N$${lastLedgerRow})`);
  formula(reserve, `C${row}`, `=SUMIF('Reserve Ledger'!$B$7:$B$${lastLedgerRow},A${row},'Reserve Ledger'!$O$7:$O$${lastLedgerRow})`);
  formula(reserve, `D${row}`, `=SUMIFS('Reserve Ledger'!$O$7:$O$${lastLedgerRow},'Reserve Ledger'!$B$7:$B$${lastLedgerRow},A${row},'Reserve Ledger'!$L$7:$L$${lastLedgerRow},10)`);
  formula(reserve, `E${row}`, `=IF(AND(ISNUMBER($B$3),$B$3>=0,$B$3<=1),D${row}*$B$3,NA())`);
  formula(reserve, `F${row}`, `=C${row}-E${row}`);
  formula(reserve, `G${row}`, `=IF(K${row}>0,MAX(B${row}-F${row},0),NA())`);
  value(reserve, `H${row}`, expected.eligible_deposit);
  formula(reserve, `I${row}`, `=IF(AND(ISNUMBER(H${row}),H${row}>=0),MAX(G${row}-H${row},0),NA())`);
  formula(reserve, `J${row}`, `=IF(AND(ISNUMBER(H${row}),H${row}>=0),MAX(H${row}-G${row},0),NA())`);
  formula(reserve, `K${row}`, `=COUNTIF('Reserve Ledger'!$B$7:$B$${lastLedgerRow},A${row})`);
  for (const [metric, column] of Object.entries(RESERVE_COLUMNS)) check("Reserve", expected.date, metric, `Reserve!${column}${row}`, expected[metric]);
}
reserve.getRange(`A7:A${FIRST_ROW + inputs.reserve_expected.length - 1}`).setNumberFormat(DATE_FORMAT);

let block = 7;
const inputLast = inputs.leases.reduce((count, contract) => count + contract.payments.length + 20, 7);
baseStyle(leaseInputs, "F", inputLast, "Synthetic lease contracts (USD)");
value(leaseInputs, "A3", "Monthly end-of-period payments. Classifications supplied. No ownership transfer or purchase option.");
value(leaseInputs, "A4", FASB_URL);
leaseInputs.getRange(`A7:A${inputLast}`).format.columnWidth = 26;
leaseInputs.getRange(`B7:F${inputLast}`).format.columnWidth = 21;
leaseInputs.freezePanes.freezeRows(6);
for (const contract of inputs.leases) {
  const count = contract.payments.length;
  const tableHeader = block + 15;
  const dataStart = block + 16;
  const dataEnd = dataStart + count - 1;
  const parameterRow = Object.fromEntries(Object.entries(PARAMETER_OFFSETS).map(([key, offset]) => [key, block + offset]));
  const ref = key => `'Lease Inputs'!$B$${parameterRow[key]}`;
  leaseMetadata.set(contract.lease_id, {parameterRow, ref, dataStart, dataEnd, count});
  value(leaseInputs, `A${block}`, contract.lease_id);
  value(leaseInputs, `B${block}`, contract.kind);
  leaseInputs.getRange(`A${block}:F${block}`).format.font = {bold: true};
  value(leaseInputs, `D${block}`, "Inputs valid");
  const parameterValid = ["rate", "prepaid", "incentive", "costs", "revisedRate"].map(key => `ISNUMBER($B$${parameterRow[key]}),$B$${parameterRow[key]}>=0`).join(",");
  formula(leaseInputs, `E${block}`, `=AND(${parameterValid},COUNT(B${dataStart}:B${dataEnd})=${count},COUNT(C${dataStart}:C${dataEnd})=${count},MIN(B${dataStart}:B${dataEnd})>=0,MIN(C${dataStart}:C${dataEnd})>=0,ISNUMBER($B$${parameterRow.modPeriod}),INT($B$${parameterRow.modPeriod})=$B$${parameterRow.modPeriod},$B$${parameterRow.modPeriod}>=0,$B$${parameterRow.modPeriod}<=${count},$B$${parameterRow.term}=${count})`);
  const parameterValues = [
    ["Periodic rate", contract.periodic_rate], ["Prepaid", contract.prepaid], ["Incentive", contract.incentive],
    ["Direct costs", contract.initial_direct_cost], ["Periods", count],
    ["Modification period (0 none)", contract.modification?.effective_period ?? 0],
    ["Revised periodic rate", contract.modification?.periodic_rate ?? contract.periodic_rate],
    ["Initial liability", null], ["Initial ROU", null], ["Revised liability", null],
    ["Remaining periods", null], ["Remaining cash", null], ["Original cash", null],
  ];
  leaseInputs.getRange(`A${block + 1}:B${block + 13}`).values = parameterValues;
  for (const key of ["rate", "revisedRate"]) leaseInputs.getRange(`B${parameterRow[key]}`).setNumberFormat("0.00%");
  for (const key of ["prepaid", "incentive", "costs", "initialLiability", "initialRou", "revisedLiability", "remainingCash", "originalCash"]) leaseInputs.getRange(`B${parameterRow[key]}`).setNumberFormat(MONEY_FORMAT);
  headers(leaseInputs, `A${tableHeader}:F${tableHeader}`, ["Period", "Original payment", "Revised payment", "Original PV", "Revised period", "Revised PV"]);
  leaseInputs.getRange(`B${dataStart}:D${dataEnd}`).setNumberFormat(MONEY_FORMAT);
  leaseInputs.getRange(`F${dataStart}:F${dataEnd}`).setNumberFormat(MONEY_FORMAT);
  for (let period = 1; period <= count; period++) {
    const row = dataStart + period - 1;
    const revised = contract.modification && period >= contract.modification.effective_period
      ? contract.modification.remaining_payments[period - contract.modification.effective_period] : contract.payments[period - 1];
    leaseInputs.getRange(`A${row}:C${row}`).values = [[period, contract.payments[period - 1], revised]];
    formula(leaseInputs, `D${row}`, `=IF($E$${block},B${row}/(1+$B$${parameterRow.rate})^A${row},NA())`);
    formula(leaseInputs, `E${row}`, `=IF(A${row}<$B$${parameterRow.modPeriod},0,A${row}-$B$${parameterRow.modPeriod}+1)`);
    formula(leaseInputs, `F${row}`, `=IF($E$${block},IF(OR($B$${parameterRow.modPeriod}=0,A${row}<$B$${parameterRow.modPeriod}),0,C${row}/(1+$B$${parameterRow.revisedRate})^E${row}),NA())`);
  }
  formula(leaseInputs, `B${parameterRow.initialLiability}`, `=SUM(D${dataStart}:D${dataEnd})`);
  formula(leaseInputs, `B${parameterRow.initialRou}`, `=B${parameterRow.initialLiability}+B${parameterRow.prepaid}-B${parameterRow.incentive}+B${parameterRow.costs}`);
  formula(leaseInputs, `B${parameterRow.revisedLiability}`, `=SUM(F${dataStart}:F${dataEnd})`);
  formula(leaseInputs, `B${parameterRow.remainingPeriods}`, `=IF(B${parameterRow.modPeriod}=0,0,B${parameterRow.term}-B${parameterRow.modPeriod}+1)`);
  formula(leaseInputs, `B${parameterRow.remainingCash}`, `=IF(B${parameterRow.modPeriod}=0,0,SUMIF(A${dataStart}:A${dataEnd},">="&B${parameterRow.modPeriod},C${dataStart}:C${dataEnd}))`);
  formula(leaseInputs, `B${parameterRow.originalCash}`, `=SUM(B${dataStart}:B${dataEnd})`);
  leaseInputs.getRange(`B${parameterRow.rate}`).dataValidation = {rule: {type: "decimal", operator: "greaterThanOrEqual", formula1: 0}};
  leaseInputs.getRange(`B${parameterRow.modPeriod}`).dataValidation = {rule: {type: "whole", operator: "between", formula1: 0, formula2: count}};
  const sheet = leaseSheets.get(contract.lease_id);
  baseStyle(sheet, "N", FIRST_ROW + count, `${contract.lease_id} ${contract.kind} lease (USD)`);
  value(sheet, "A3", "Synthetic. Monthly periods. Modification applies before the effective period's payment.");
  value(sheet, "A4", "Finance amortization uses the remaining lease term. Operating expense stays level between modifications.");
  headers(sheet, "A6:N6", ["Period", "Cash payment", "Periodic rate", "Opening liability", "Remeasurement", "Accretion", "Closing liability", "Opening ROU", "ROU adjustment", "ROU amortization", "Closing ROU", "Lease expense", "Liability check", "ROU check"]);
  sheet.getRange(`B7:N${FIRST_ROW + count - 1}`).setNumberFormat(MONEY_FORMAT);
  sheet.getRange(`C7:C${FIRST_ROW + count - 1}`).setNumberFormat("0.00%");
  sheet.getRange(`A7:A${FIRST_ROW + count - 1}`).format.columnWidth = 9;
  sheet.freezePanes.freezeRows(HEADER_ROW);
  for (let period = 1; period <= count; period++) {
    const row = FIRST_ROW + period - 1;
    const inputRow = dataStart + period - 1;
    formula(sheet, `A${row}`, `='Lease Inputs'!A${inputRow}`);
    formula(sheet, `B${row}`, `=IF(AND(${ref("modPeriod")}>0,A${row}>=${ref("modPeriod")}),'Lease Inputs'!C${inputRow},'Lease Inputs'!B${inputRow})`);
    formula(sheet, `C${row}`, `=IF(AND(${ref("modPeriod")}>0,A${row}>=${ref("modPeriod")}),${ref("revisedRate")},${ref("rate")})`);
    formula(sheet, `D${row}`, period === 1 ? `=${ref("initialLiability")}` : `=G${row - 1}`);
    formula(sheet, `E${row}`, `=IF(A${row}=${ref("modPeriod")},${ref("revisedLiability")}-D${row},0)`);
    formula(sheet, `F${row}`, `=(D${row}+E${row})*C${row}`);
    formula(sheet, `G${row}`, `=D${row}+E${row}+F${row}-B${row}`);
    formula(sheet, `H${row}`, period === 1 ? `=${ref("initialRou")}` : `=K${row - 1}`);
    formula(sheet, `I${row}`, `=E${row}`);
    if (contract.kind === "operating") {
      const originalExpense = `(${ref("originalCash")}+${ref("prepaid")}-${ref("incentive")}+${ref("costs")})/${ref("term")}`;
      formula(sheet, `L${row}`, `=IF(A${row}=${ref("modPeriod")},(${ref("remainingCash")}+H${row}+I${row}-D${row}-E${row})/${ref("remainingPeriods")},${period === 1 ? originalExpense : `L${row - 1}`})`);
      formula(sheet, `J${row}`, `=L${row}-F${row}`);
    } else {
      formula(sheet, `J${row}`, `=IF(A${row}=${ref("modPeriod")},(H${row}+I${row})/${ref("remainingPeriods")},${period === 1 ? `${ref("initialRou")}/${ref("term")}` : `J${row - 1}`})`);
      formula(sheet, `L${row}`, `=F${row}+J${row}`);
    }
    formula(sheet, `K${row}`, `=H${row}+I${row}-J${row}`);
    formula(sheet, `M${row}`, `=D${row}+E${row}+F${row}-B${row}-G${row}`);
    formula(sheet, `N${row}`, `=H${row}+I${row}-J${row}-K${row}`);
    const expected = inputs.lease_expected.find(item => item.lease_id === contract.lease_id && item.period === period);
    for (const [metric, column] of Object.entries(LEASE_COLUMNS)) if (metric !== "period") check(contract.lease_id, period, metric, `'${contract.lease_id}'!${column}${row}`, expected[metric]);
  }
  block = dataEnd + 5;
}

baseStyle(audit, "G", FIRST_ROW + formulaChecks.length, "Excel reconciliation to Python (USD unless rate)");
value(audit, "A3", "Tolerance");
value(audit, "B3", TOLERANCE);
value(audit, "A4", "Rate tolerance");
value(audit, "B4", RATE_TOLERANCE);
audit.getRange("B4").setNumberFormat("0.00E+00");
value(audit, "C3", "Python values are fixed snapshots. Refresh Python outputs and rebuild after contract changes.");
headers(audit, "A6:G6", ["Schedule", "Date or period", "Metric", "Excel live", "Python snapshot", "Difference", "Status"]);
audit.getRange(`C1:C${FIRST_ROW + formulaChecks.length}`).format.columnWidth = 25;
audit.getRange(`D7:F${FIRST_ROW + formulaChecks.length - 1}`).setNumberFormat(MONEY_FORMAT);
for (const [index, item] of formulaChecks.entries()) {
  const row = FIRST_ROW + index;
  audit.getRange(`A${row}:C${row}`).values = [[item.schedule, item.key, item.metric]];
  formula(audit, `D${row}`, `=${item.cell}`);
  value(audit, `E${row}`, item.expected);
  formula(audit, `F${row}`, `=D${row}-E${row}`);
  formula(audit, `G${row}`, `=IF(ABS(F${row})<=IF(C${row}="rate",$B$4,$B$3),"PASS","FAIL")`);
}
audit.freezePanes.freezeRows(HEADER_ROW);
baseStyle(readme, "F", 23, "Workbook scope");
const notes = [
  ["Data", "All financial balances, lease contracts and evidence are synthetic. Seed 8421533."],
  ["Reserve", "Restricted Exhibit A items 1 to 12. Note E(3) basic-method reduction. Items 13 to 15 unsupported."],
  ["Source", SOURCE_URL],
  ["Leases", "Original ASU 2016-02 fixed-payment model. Consideration-only modifications. Classification is supplied."],
  ["Source", FASB_URL],
  ["Verification", "Primary rule scope checked 2026-11-08. See docs/source_verification.md for paragraph coverage."],
  ["Inputs", "Edit Reserve Ledger A:K, Reserve H and Lease Inputs B:C value cells. Formulas own other calculations."],
  ["Refresh", "Audit holds fixed Python snapshots. Input edits should produce differences until Python is refreshed."],
  ["Extension", "Ranges cover the shipped population. Rebuild for added dates, rows, leases or a different term."],
  ["Dates", "Reserve dates are Excel dates. Lease periods are monthly indices from commencement."],
  ["Limitations", "No filing, custody, complete net capital, classification test, impairment, termination or later-amendment validation."],
  ["Review", "No real-world validation. Native Excel behavior is separately reported in excel_verification.json."],
];
readme.getRange("A6:B17").values = notes;
readme.getRange("A6:A17").format.font = {bold: true};
readme.getRange("A1:A23").format.columnWidth = 18;
readme.getRange("B6:B17").format.columnWidth = 118;
readme.getRange("B6:B17").format.wrapText = true;
readme.getRange("A6:B17").format.rowHeight = 33;

workbook.recalculate();
const mismatch = [];
for (const item of formulaChecks) {
  const sheet = workbook.worksheets.getItem(item.schedule);
  const address = item.cell.slice(item.cell.lastIndexOf("!") + 1);
  const actual = sheet.getRange(address).values[0][0];
  if (typeof actual !== "number" || !Number.isFinite(actual) || Math.abs(actual - item.expected) > (item.metric === "rate" ? RATE_TOLERANCE : TOLERANCE)) mismatch.push({...item, actual});
}
if (mismatch.length) throw new Error(`Reconciliation failed: ${JSON.stringify(mismatch.slice(0, 4))}`);
const mutations = [];
const originalCredit = ledger.getRange("D7").values[0][0];
const originalReserve = reserve.getRange("G7").values[0][0];
value(ledger, "D7", originalCredit + 100);
workbook.recalculate();
if (Math.abs(reserve.getRange("G7").values[0][0] - originalReserve - 100) > TOLERANCE) throw new Error("Reserve input change did not propagate");
mutations.push("Reserve source credit +100 changes required reserve by +100");
value(ledger, "D7", originalCredit);
value(ledger, "D7", null);
workbook.recalculate();
if (ledger.getRange("P7").values[0][0] !== false) throw new Error("Blank amount was accepted");
mutations.push("Blank reserve amount fails validation");
value(ledger, "D7", 0);
workbook.recalculate();
if (ledger.getRange("P7").values[0][0] !== true) throw new Error("Zero amount rejected");
mutations.push("Zero reserve amount remains valid");
value(ledger, "D7", originalCredit);
const secondId = ledger.getRange("A8").values[0][0];
value(ledger, "A8", ledger.getRange("A7").values[0][0]);
workbook.recalculate();
if (ledger.getRange("P7").values[0][0] !== false || ledger.getRange("P8").values[0][0] !== false) throw new Error("Duplicate ledger IDs were accepted");
mutations.push("Duplicate reserve IDs fail validation for both rows");
value(ledger, "A8", secondId);
const office = inputs.leases.find(item => item.kind === "operating");
const meta = leaseMetadata.get(office.lease_id);
const modificationPeriod = office.modification.effective_period;
const modifiedInputRow = meta.dataStart + modificationPeriod - 1;
const revisedCell = `C${modifiedInputRow}`;
const initialRevised = leaseInputs.getRange(revisedCell).values[0][0];
const originalPv = leaseInputs.getRange(`B${meta.parameterRow.revisedLiability}`).values[0][0];
value(leaseInputs, revisedCell, initialRevised + 100);
workbook.recalculate();
const pvChange = leaseInputs.getRange(`B${meta.parameterRow.revisedLiability}`).values[0][0] - originalPv;
if (Math.abs(pvChange - 100 / (1 + office.modification.periodic_rate)) > TOLERANCE) throw new Error("Lease revised payment did not propagate");
const finalOfficeRow = FIRST_ROW + office.payments.length - 1;
if (Math.abs(leaseSheets.get(office.lease_id).getRange(`K${finalOfficeRow}`).values[0][0]) > TOLERANCE) throw new Error("Modified ROU does not amortize to zero");
mutations.push("Revised operating payment +100 changes remeasured PV by 100/(1+rate); ending ROU stays zero");
value(leaseInputs, revisedCell, initialRevised);
const originalRate = leaseInputs.getRange(`B${meta.parameterRow.rate}`).values[0][0];
value(leaseInputs, `B${meta.parameterRow.rate}`, null);
workbook.recalculate();
if (leaseInputs.getRange(`E${meta.parameterRow.rate - 1}`).values[0][0] !== false) throw new Error("Blank lease rate accepted");
mutations.push("Blank lease discount rate fails input validation");
value(leaseInputs, `B${meta.parameterRow.rate}`, 0);
workbook.recalculate();
if (leaseInputs.getRange(`E${meta.parameterRow.rate - 1}`).values[0][0] !== true) throw new Error("Zero lease rate rejected");
mutations.push("Zero lease discount rate is valid");
value(leaseInputs, `B${meta.parameterRow.rate}`, originalRate);
workbook.recalculate();
for (const item of formulaChecks) {
  const address = item.cell.slice(item.cell.lastIndexOf("!") + 1);
  const actual = workbook.worksheets.getItem(item.schedule).getRange(address).values[0][0];
  if (typeof actual !== "number" || Math.abs(actual - item.expected) > (item.metric === "rate" ? RATE_TOLERANCE : TOLERANCE)) throw new Error("Mutation restore failed");
}
const errorScan = await workbook.inspect({kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: {useRegex: true, maxResults: 10}, summary: "final formula error scan", maxChars: 1800});
console.log(errorScan.ndjson);
await fs.mkdir(PREVIEW_DIR, {recursive: true});
for (const [name, range] of [["Reserve", "A1:K17"], ...[...leaseSheets.keys()].map(name => [name, "A1:N15"]), ["Reserve Ledger", "A1:P13"], ["Lease Inputs", "A1:F30"], ["Audit", "A1:G15"], ["ReadMe", "A1:B18"]]) {
  const preview = await workbook.render({sheetName: name, range, scale: 1.5, format: "png"});
  await fs.writeFile(path.join(PREVIEW_DIR, `${name.replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}
console.log((await workbook.inspect({kind: "table", range: "Reserve!A6:K9", include: "values,formulas", tableMaxRows: 4, tableMaxCols: 11, maxChars: 2500})).ndjson);
const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(OUTPUT_PATH);
await fs.writeFile(VERIFICATION_PATH, JSON.stringify({engine: "@oai/artifact-tool", comparisons: formulaChecks.length, mismatches: 0, tolerance_usd: TOLERANCE, tolerance_rate: RATE_TOLERANCE, mutation_checks: mutations, formula_error_scan: errorScan.ndjson, native_excel: "Not tested", visuals: "Generated for review", source_snapshot: "workbook_inputs.json"}, null, 2) + "\n");
console.log(JSON.stringify({output: OUTPUT_PATH, comparisons: formulaChecks.length, mutations: mutations.length}));
