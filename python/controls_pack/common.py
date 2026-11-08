"""Validation and portable file handling."""
import csv
import hashlib
import json
import math
from pathlib import Path

# Configuration
ENCODING = "utf-8"


def number(value, name, minimum=None):
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a number")
    result = float(value)
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        raise ValueError(f"{name}: invalid numeric value")
    return result


def flag(value, name):
    if value in (True, "true", "True", "1", 1):
        return True
    if value in (False, "false", "False", "0", 0):
        return False
    raise ValueError(f"{name}: expected boolean")


def unique(rows, fields):
    seen = set()
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key in seen or any(value is None or value == "" for value in key):
            raise ValueError(f"Missing or duplicate key: {key}")
        seen.add(key)


def read_csv(path):
    with Path(path).open(encoding=ENCODING, newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields=None):
    rows = list(rows)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0]) if rows else [])
    with Path(path).open("w", encoding=ENCODING, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding=ENCODING)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
