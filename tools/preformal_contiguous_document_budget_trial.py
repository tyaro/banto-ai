"""Run one invented 50,000-draw arithmetic/document/slice budget attempt."""
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_contiguous_document_budget as trial  # noqa: E402


if __name__ == '__main__':
    try:
        raise SystemExit(trial.main())
    except trial.draw_bridge.draw_budget.UnreapedMeasurement as owner:
        trial.draw_bridge.draw_budget.retain_unreaped_owner(owner)
        raise
