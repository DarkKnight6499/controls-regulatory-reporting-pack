"""Run the shipped offline snapshot."""
from dataclasses import asdict
import json

from .report import run


if __name__ == "__main__":
    print(json.dumps(asdict(run()), indent=2))
