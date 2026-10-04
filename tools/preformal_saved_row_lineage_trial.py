"""Record a partial invented registered-row lineage from a pinned saved result.

This reuses the earlier owned reader's saved result. It does not reread its
observation payloads, run a producer, or authorize a formal evaluation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import _anomaly_v03_io as io  # noqa: E402
from banto_ai import _anomaly_v03_runtime as paths  # noqa: E402
from banto_ai import anomaly_v03 as v  # noqa: E402
from banto_ai import anomaly_v03_observation_audit as pinned  # noqa: E402
from banto_ai import anomaly_v03_registered_saved_row_lineage as lineage  # noqa: E402


def _pin(value: str) -> dict:
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None:
        raise ValueError('expected pin must be bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def run(source_text: str, output_text: str, *, chunk_index: int,
        receipt_pin: dict, report_pin: dict, outer_result_pin: dict,
        budgeted_result_pin: dict, resource_budget_pin: dict) -> dict:
    source = paths.regular_path(_path(source_text), directory=True)
    output = paths.regular_path(_path(output_text), missing=True)
    v.require(source.parent == ROOT / 'artifacts' and
              source.name.startswith('anomaly-v03-preformal-registered-attempt-'),
              'invented registered-attempt source root required')
    v.require(output.parent.parent == ROOT / 'artifacts' and
              output.parent.name.startswith('anomaly-v03-preformal-saved-row-lineage-') and
              output.name == 'result.json' and
              not output.exists(), 'new dedicated lineage output required')
    v.require(type(chunk_index) is int and 0 <= chunk_index < 480,
              'registered chunk index')
    receipt_raw = pinned.read_pinned(source / 'saved' / 'receipt.json',
                                     receipt_pin, 512 * 1024)
    report_raw = pinned.read_pinned(source / 'saved' / 'report.json',
                                    report_pin, 512 * 1024)
    outer_raw = pinned.read_pinned(source / 'owned-generator' / 'result.json',
                                   outer_result_pin, 256 * 1024)
    budgeted_raw = pinned.read_pinned(source / 'budgeted-result.json',
                                      budgeted_result_pin, 64 * 1024)
    resource_raw = pinned.read_pinned(source / 'resource-budget.json',
                                      resource_budget_pin, 64 * 1024)
    budgeted = v.strict_json(budgeted_raw)
    resource = v.strict_json(resource_raw)
    v.require(budgeted_raw == v.canonical_json(budgeted) and
              resource_raw == v.canonical_json(resource),
              'canonical retained two-role budget bytes')
    v.require(budgeted.get('status') == 'verified' and
              budgeted.get('inner_result_pin') == outer_result_pin and
              budgeted.get('resource_budget_pin') == resource_budget_pin and
              budgeted.get('root') == str(source) and
              budgeted.get('shared_budget_passed') is True and
              budgeted.get('both_owned_exits_reported') is True and
              budgeted.get('actual_registered_observations_read') is False and
              budgeted.get('campaign_evaluations_credited') == 0 and
              budgeted.get('full_end_to_end_budget_measured') is False,
              'retained two-role budget/result link')
    v.require(resource.get('passed') is True and
              resource.get('both_owned_exits_reported') is True and
              resource.get('sampler_exit_confirmed') is True and
              resource.get('actual_registered_observations_read') is False and
              resource.get('campaign_evaluations_credited') == 0 and
              resource.get('root') == str(source),
              'retained two-role resource receipt')
    value = lineage.bind_saved_reader_rows(
        receipt_raw, report_raw, outer_raw, chunk_index=chunk_index,
        expected_receipt_pin=receipt_pin, expected_report_pin=report_pin,
        expected_outer_result_pin=outer_result_pin)
    value['retained_two_role_budget'] = {
        'budgeted_result_pin': budgeted_result_pin,
        'resource_budget_pin': resource_budget_pin,
        'shared_budget_passed_in_prior_run': True,
        'prior_scope': resource['scope'],
        'current_lineage_trial_in_prior_budget': False,
    }
    raw = v.canonical_json(value)
    v.require(len(raw) <= 512 * 1024, 'bounded lineage result')
    output.parent.mkdir()
    io._exclusive(output, raw)
    return {'output': str(output), 'bytes': len(raw),
            'status': value['status'], 'chunk_index': chunk_index,
            'verified_rows': len(value['rows']),
            'formal_permission': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--chunk-index', type=int, required=True)
    parser.add_argument('--receipt-pin', required=True)
    parser.add_argument('--report-pin', required=True)
    parser.add_argument('--outer-result-pin', required=True)
    parser.add_argument('--budgeted-result-pin', required=True)
    parser.add_argument('--resource-budget-pin', required=True)
    args = parser.parse_args()
    result = run(args.source_root, args.output, chunk_index=args.chunk_index,
                 receipt_pin=_pin(args.receipt_pin), report_pin=_pin(args.report_pin),
                 outer_result_pin=_pin(args.outer_result_pin),
                 budgeted_result_pin=_pin(args.budgeted_result_pin),
                 resource_budget_pin=_pin(args.resource_budget_pin))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
