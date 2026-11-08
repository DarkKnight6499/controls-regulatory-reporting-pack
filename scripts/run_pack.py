"""Run offline calculations without installing the package."""
import json
import sys
from dataclasses import asdict
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "python"
sys.path.insert(0, str(PACKAGE_DIR))

from controls_pack.report import run


if __name__ == "__main__":
    print(json.dumps(asdict(run()), indent=2))
