"""Regenerate the seeded synthetic snapshot from the project root."""
import sys
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "python"
sys.path.insert(0, str(PACKAGE_DIR))

from controls_pack.synthetic import generate_snapshot


if __name__ == "__main__":
    generate_snapshot()
    print("Seeded synthetic snapshot generated.")
