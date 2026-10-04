"""The c001/c011 adapter requires exact externally pinned control records."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_saved_row_coverage as coverage
from tools import preformal_saved_row_coverage_pair as pair


PINSET_ROOT = 'anomaly-v03-preformal-saved-row-coverage-pins-test'
OUTPUT_ROOT = 'anomaly-v03-preformal-saved-row-coverage-test'


def fixture(repo: Path) -> None:
    (repo / 'artifacts').mkdir()
    for index in pair.INDICES:
        paths = pair.source_paths(index)
        for name, relative in paths.items():
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if name == 'result':
                suffix = f'c0{index}1'
                value = {
                    'chunk_index': index,
                    'source_root': str(repo / 'artifacts' /
                                       ('anomaly-v03-preformal-registered-attempt-' + suffix)),
                    'output_root': str(repo / 'artifacts' /
                                       ('anomaly-v03-preformal-saved-row-reread-' + suffix)),
                    'manifest_path': str(repo / paths['manifest']),
                    'row_projection_path': str(repo / paths['rows']),
                }
                raw = v.canonical_json(value)
            else:
                raw = b'{}'
            path.write_bytes(raw)


def limited_result() -> dict:
    result = coverage.collect_saved_row_coverage([])
    result.update(status='partial_coverage_unanchored', bound_chunks=2,
                  bound_evaluations=12, chunk_indices=[0, 1],
                  missing_chunk_indices=list(range(2, 480)))
    return result


class PairAdapterTests(unittest.TestCase):
    def test_exact_attempt_one_path_derivation(self):
        first = pair.source_paths(0)
        second = pair.source_paths(1)
        self.assertEqual(first['receipt'],
                         'artifacts/anomaly-v03-preformal-registered-attempt-c001/saved/receipt.json')
        self.assertEqual(second['manifest'],
                         'artifacts/anomaly-v03-preformal-generated-pinsets-c011/pins.json')
        self.assertEqual(second['result'],
                         'artifacts/anomaly-v03-preformal-saved-row-reread-c011/result.json')
        self.assertEqual(set(first), set(coverage.RAW_LIMITS))
        for invalid in (-1, 2, True, '0'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                pair.source_paths(invalid)

    def test_prepare_and_run_keep_limited_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            fixture(repo)
            prepared = pair.prepare(PINSET_ROOT, repo=repo)
            pinset = json.loads(Path(prepared['pinset']).read_bytes())
            self.assertEqual([item['chunk_index'] for item in pinset['entries']],
                             [0, 1])
            self.assertEqual([item['attempt'] for item in pinset['entries']],
                             [1, 1])
            with patch.object(pair.coverage, 'collect_saved_row_coverage',
                              return_value=limited_result()) as collector:
                outcome = pair.run(PINSET_ROOT, prepared['pinset_pin'],
                                   OUTPUT_ROOT, repo=repo)
            self.assertEqual(collector.call_count, 1)
            self.assertEqual(len(collector.call_args.args[0]), 2)
            self.assertEqual(outcome['bound_chunks'], 2)
            self.assertFalse(outcome['formal_permission'])
            result = json.loads(Path(outcome['output']).read_bytes())
            self.assertEqual(result['external_pinset_pin'], prepared['pinset_pin'])
            self.assertEqual(result['campaign_evaluations_credited'], 0)
            self.assertFalse(result['campaign_coherence_authenticated'])
            self.assertIsNone(result['producer_campaign_anchor'])

    def test_external_pin_and_exact_file_inventory_required(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            fixture(repo)
            prepared = pair.prepare(PINSET_ROOT, repo=repo)
            pinset_path = Path(prepared['pinset'])
            with self.assertRaises(ValueError):
                pair.run(PINSET_ROOT, pair._pin(b'wrong'), OUTPUT_ROOT,
                         repo=repo)
            pinset = json.loads(pinset_path.read_bytes())
            pinset['entries'][0]['files']['rows']['path'] = \
                pair.source_paths(1)['rows']
            raw = v.canonical_json(pinset)
            pinset_path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'exact retained pair path'):
                pair.run(PINSET_ROOT, pair._pin(raw), OUTPUT_ROOT, repo=repo)

    def test_result_must_name_derived_attempt_and_reread_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            fixture(repo)
            result_path = repo / pair.source_paths(1)['result']
            value = json.loads(result_path.read_bytes())
            value['source_root'] += '-other'
            result_path.write_bytes(v.canonical_json(value))
            prepared = pair.prepare(PINSET_ROOT, repo=repo)
            with self.assertRaisesRegex(ValueError, 'exact retained pair reread'):
                pair.run(PINSET_ROOT, prepared['pinset_pin'], OUTPUT_ROOT,
                         repo=repo)

    def test_source_change_after_external_pin_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            fixture(repo)
            prepared = pair.prepare(PINSET_ROOT, repo=repo)
            (repo / pair.source_paths(0)['rows']).write_bytes(b'{"changed":true}')
            with self.assertRaises(ValueError):
                pair.run(PINSET_ROOT, prepared['pinset_pin'], OUTPUT_ROOT,
                         repo=repo)

    def test_result_root_and_pinset_root_must_be_new(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            fixture(repo)
            prepared = pair.prepare(PINSET_ROOT, repo=repo)
            with self.assertRaisesRegex(ValueError, 'new external pinset root'):
                pair.prepare(PINSET_ROOT, repo=repo)
            (repo / 'artifacts' / OUTPUT_ROOT).mkdir()
            with self.assertRaisesRegex(ValueError, 'new dedicated pair coverage'):
                pair.run(PINSET_ROOT, prepared['pinset_pin'], OUTPUT_ROOT,
                         repo=repo)


if __name__ == '__main__':
    unittest.main()
