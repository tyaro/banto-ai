"""New two-arm parent-policy experiment, independent of the closed batch."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.fixtures.anomaly_v03_directory_rename_probe import main


if __name__ == "__main__":
    raise SystemExit(main(compare_parent_policy=True))
