"""Typed CSV loading with explicit field names."""
from dataclasses import fields
from typing import get_type_hints

from .common import flag, number, read_csv

# Configuration
CONVERTERS = {str: str, float: lambda value: number(value, "CSV numeric"), int: int,
              bool: lambda value: flag(value, "CSV flag")}


def load_records(path, record_type):
    hints = get_type_hints(record_type)
    field_names = {field.name for field in fields(record_type)}
    result = []
    for row in read_csv(path):
        if set(row) != field_names:
            raise ValueError(f"Unexpected schema in {path.name}: {sorted(row)}")
        converted = {}
        for name, value in row.items():
            annotation = hints[name]
            if annotation == int | None:
                converted[name] = None if value == "" else int(value)
            else:
                converted[name] = CONVERTERS[annotation](value)
        result.append(record_type(**converted))
    return result
