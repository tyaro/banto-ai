"""One new-fixture experiment with a frozen parent and a source-relative leaf."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.fixtures.anomaly_v03_directory_rename_probe import main


if __name__ == "__main__":
    raise SystemExit(main(same_parent=True))
