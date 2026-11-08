"""Optional online fetch. Saves primary rule documents and an honest manifest."""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "public"
TIMEOUT_SECONDS = 45
HOST_DELAY_SECONDS = 1.0
USER_AGENT = os.environ.get("SOURCE_USER_AGENT", "Mozilla/5.0 (controls reporting source archive)")
SOURCES = [
    {"id": "R1", "url": "https://www.ecfr.gov/current/title-17/section-240.15c3-3a",
     "document": "17 CFR 240.15c3-3a Exhibit A", "section": "Items 1 to 16; Notes A to E", "filename": "reserve_rule.html", "marker": "Debit balances in customers"},
    {"id": "R2", "url": "https://www.ecfr.gov/current/title-17/chapter-II/part-240/section-240.15c3-1",
     "document": "17 CFR 240.15c3-1", "section": "(a)(1)(i), (a)(2)(i), (c)(1)(vii), (c)(2)(iv)(A), (c)(2)(vi)(D)(1), (J), (M)",
     "filename": "capital_rule.html", "marker": "Aggregate Indebtedness"},
    {"id": "R3", "url": "https://www.ecfr.gov/current/title-17/chapter-II/part-240/section-240.15c3-3",
     "document": "17 CFR 240.15c3-3", "section": "(e)", "filename": "customer_protection.html", "marker": "Special Reserve Bank Account"},
    {"id": "C1", "url": "https://www.ecfr.gov/current/title-17/chapter-II/part-240/section-240.12b-2",
     "document": "17 CFR 240.12b-2", "section": "Material weakness; significant deficiency definitions", "filename": "control_definitions.html", "marker": "Material weakness"},
    {"id": "A1", "url": "https://storage.fasb.org/FIF%20ASU%202016-02%20Leases%20%28Topic%20842%29%20%28Rev%206-3-20%29.pdf",
     "document": "FASB In Focus ASU 2016-02, revised June 2020", "section": "Lessee model summary", "filename": "fasb_summary.pdf", "marker": "%PDF"},
    {"id": "A2", "url": "https://storage.fasb.org/ASU%202016-02_Section%20A.pdf",
     "document": "FASB ASU 2016-02 Section A", "section": "842-10-25-8 to 25-13; 842-20-25, 30, 35",
     "filename": "fasb_leases_section_a.pdf", "marker": "%PDF"},
]


def fetch_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for source in SOURCES:
        record = {key: value for key, value in source.items() if key != "marker"}
        record.update(retrieved_at=datetime.now(timezone.utc).isoformat(), status="FAILED", sha256=None)
        try:
            request = Request(source["url"], headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                content = response.read()
                record["final_url"] = response.url
                record["http_status"] = response.status
                record["content_type"] = response.headers.get("Content-Type", "")
            if source["marker"].encode() not in content:
                raise ValueError("Expected document marker missing; possible block or landing page")
            target = OUTPUT_DIR / source["filename"]
            target.write_bytes(content)
            record.update(status="DOWNLOADED_NOT_REVIEWED", sha256=hashlib.sha256(content).hexdigest(), bytes=len(content))
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        results.append(record)
        print(f"{source['id']}: {record['status']}")
        (OUTPUT_DIR / "manifest.json").write_text(json.dumps({"synthetic": False, "sources": results}, indent=2) + "\n", encoding="utf-8")
        time.sleep(HOST_DELAY_SECONDS)
    return all(record["status"] == "DOWNLOADED_NOT_REVIEWED" for record in results)


if __name__ == "__main__":
    raise SystemExit(0 if fetch_all() else 1)
