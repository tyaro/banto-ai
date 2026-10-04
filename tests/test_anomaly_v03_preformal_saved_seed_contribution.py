"""One invented seed contribution from twelve pinned saved-reader slots."""
import copy
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_consumer_input as metadata
from banto_ai import anomaly_v03_preformal_saved_row_coverage as coverage
from banto_ai import anomaly_v03_preformal_saved_seed_contribution as seed
from banto_ai import anomaly_v03_registered_saved_row_lineage as lineage
from banto_ai import anomaly_v03_registered_saved_summary as saved
from tests.test_anomaly_v03_producer_slice_fixture import raw_counts
from tests.test_anomaly_v03_preformal_saved_row_coverage import make_entry, rewrap
from tests.test_anomaly_v03_registered_saved_summary import pin


def chunk_entry(index, *, latest_attempt=1, stale_report=False,
                inconclusive_first=False):
    """Build consistent invented reader/control bytes for a frozen layout."""
    _, objects = make_entry()
    objects = copy.deepcopy(objects)
    suffix = f't{index:03d}'
    source_root = rf'D:\invented\artifacts\anomaly-v03-preformal-registered-attempt-{suffix}'
    output_root = rf'D:\invented\artifacts\anomaly-v03-preformal-saved-row-reread-{suffix}'
    identities = v.evaluation_inventory('holdout')[index * 6:index * 6 + 6]
    assert len(identities) == 6
    savepoint = objects['savepoint']
    savepoint['chunk_index'] = index
    savepoint['run_root'] = source_root + r'\run-root'
    savepoint_raw = v.canonical_json(savepoint)
    receipt, report, outer = (objects[name] for name in ('receipt', 'report', 'outer'))
    receipt['chunk_index'] = report['chunk_index'] = index
    receipt['savepoint_pin'] = report['savepoint_pin'] = pin(savepoint_raw)
    payload_pins = {}
    hashes = {}
    for identity in identities:
        dataset = identity['dataset_id']
        if dataset in hashes:
            continue
        hashes[dataset] = {}
        for kind in metadata.INPUT_HASHES:
            raw = v.canonical_json({'invented': True, 'dataset_id': dataset,
                                    'kind': kind})
            payload_pins[saved._payload_path(identity, kind)] = pin(raw)
            hashes[dataset][kind] = pin(raw)['sha256']
    for row, slot, identity in zip(report['rows'],
                                    receipt['attempts'][0]['evaluations'],
                                    identities):
        input_hashes = hashes[identity['dataset_id']]
        raw = v.canonical_json({'identity': identity,
                                'input_hashes': input_hashes, 'invented': True})
        evaluation_pin = pin(raw)
        payload_pins[saved._payload_path(identity)] = evaluation_pin
        row.update(identity=identity, input_hashes=input_hashes,
                   evaluation_pin=evaluation_pin)
        slot.update(identity=identity, input_hashes=input_hashes,
                    evaluation_sha256=evaluation_pin['sha256'])
    if inconclusive_first:
        slot = receipt['attempts'][0]['evaluations'][0]
        row = report['rows'][0]
        slot.update(status='inconclusive', profile_status='inconclusive')
        row['evaluation_outcome'] = 'inconclusive'
        row['slices'] = raw_counts({**row['primary'],
                                    'profile_status': 'inconclusive'})
    if latest_attempt == 2:
        old = copy.deepcopy(receipt['attempts'][0])
        old['state'] = 'failed'
        old['failure'] = {'stage': 'supervision', 'reason': 'worker_exit',
                          'evidence_sha256': None}
        old['evaluations'][-1].update(status='partial',
                                     profile_status='not_evaluated',
                                     evaluation_sha256=None)
        current = receipt['attempts'][0]
        current['attempt'] = 2
        receipt['attempts'] = [old, current]
    report['attempt'] = 1 if stale_report else latest_attempt
    receipt_raw = v.canonical_json(receipt)
    report['receipt_pin'] = pin(receipt_raw)
    report['payload_pins'] = payload_pins
    report_raw = v.canonical_json(report)
    reader = outer['reader_result']
    reader.update(chunk_index=index, latest_attempt=latest_attempt,
                  failed_attempts=latest_attempt - 1,
                  receipt_pin=pin(receipt_raw), report_pin=pin(report_raw),
                  payload_pins=payload_pins)
    output_pins = dict(payload_pins)
    output_pins.update({
        'saved/receipt.json': pin(receipt_raw),
        'saved/report.json': pin(report_raw),
        'saved/registry.json': receipt['registry_pin'],
        'saved/savepoint.json': pin(savepoint_raw),
    })
    outer['generated_output_pins'] = output_pins
    outer_raw = v.canonical_json(outer)
    # A stale report is rejected before the reread projection can be derived.
    if not stale_report:
        rows = lineage.bind_saved_reader_rows(
            receipt_raw, report_raw, outer_raw, chunk_index=index,
            expected_receipt_pin=pin(receipt_raw),
            expected_report_pin=pin(report_raw),
            expected_outer_result_pin=pin(outer_raw))
        objects['rows'] = rows
    manifest = objects['manifest']
    manifest.update(chunk_index=index, root=source_root,
                    output_pins=output_pins,
                    output_file_count=len(output_pins),
                    output_bytes=sum(p['bytes'] for p in output_pins.values()))
    manifest_raw = v.canonical_json(manifest)
    stdout = objects['stdout']
    stdout.update(manifest_pin=pin(manifest_raw), output_pins=output_pins,
                  reader_result=reader)
    stdout_raw = v.canonical_json(stdout) + b'\n'
    supervision = objects['supervision']
    supervision['output'] = pin(stdout_raw)
    result = objects['result']
    result.update(chunk_index=index, source_root=source_root,
                  output_root=output_root,
                  manifest_path=rf'D:\invented\artifacts\anomaly-v03-preformal-generated-pinsets-{suffix}\pins.json',
                  row_projection_path=output_root + r'\rows.json',
                  external_saved_payload_bytes=manifest['output_bytes'],
                  manifest_pin=pin(manifest_raw),
                  row_projection_pin=pin(v.canonical_json(objects['rows'])),
                  old_outer_result_pin=pin(outer_raw),
                  receipt_pin=pin(receipt_raw), report_pin=pin(report_raw),
                  reader_supervision_pin=pin(v.canonical_json(supervision)),
                  child_stdout_pin=pin(stdout_raw))
    entry = {name + '_raw': (stdout_raw if name == 'stdout'
                            else v.canonical_json(value))
             for name, value in objects.items()}
    entry['expected_pins'] = {name: pin(entry[name + '_raw'])
                              for name in objects}
    return entry


class SavedSeedContributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = [chunk_entry(index) for index in range(12)]

    def test_twelve_layouts_form_one_unanchored_contribution(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')):
            result = seed.aggregate_saved_seed(self.entries,
                                                registered_seed_index=0)
        self.assertEqual(result['status'], 'complete_seed_contribution_unanchored')
        self.assertEqual(result['bound_evaluations'], 72)
        self.assertEqual(result['layout_ids'], list(range(12)))
        self.assertEqual(result['missing_layouts'], [])
        contribution = result['cluster_contribution']
        self.assertEqual(contribution['cluster']['cluster_id'], 'invented-00')
        self.assertEqual(contribution['diagnostic']['cluster_id'], 'invented-00')
        self.assertEqual(contribution['slice_source_cluster']['cluster_id'],
                         'invented-00')
        for candidate in seed.arithmetic.CANDIDATES:
            for layer in seed.arithmetic.STRATA[:2]:
                cell = contribution['cluster']['candidates'][candidate][layer]
                self.assertEqual(cell['profile_status'], 'calibrated')
                self.assertEqual(cell['counts']['machine_recall'][1], 120)
                self.assertEqual(cell['counts']['clean_rate'][1], 40380)
                self.assertEqual(contribution['slice_source_cluster']
                                 ['candidates'][candidate][layer]['evaluations'], 12)
        for field in ('clusters', 'diagnostics', 'slice_source'):
            self.assertIsNone(result[field])
        self.assertFalse(result['formal_permission'])
        self.assertFalse(result['analysis_authorized'])
        self.assertFalse(result['actual_registered_observations_read'])
        self.assertEqual(result['campaign_evaluations_credited'], 0)

    def test_partial_seed_retains_pins_but_no_contribution(self):
        result = seed.aggregate_saved_seed(self.entries[:1],
                                           registered_seed_index=0)
        self.assertEqual(result['status'], 'partial_seed_contribution_unanchored')
        self.assertEqual(result['bound_evaluations'], 6)
        self.assertEqual(result['missing_layouts'], list(range(1, 12)))
        self.assertEqual(result['source_chunks'][0]['entry_pins']['rows'],
                         self.entries[0]['expected_pins']['rows'])
        self.assertEqual(set(result['source_chunks'][0]['entry_pins']),
                         set(coverage.RAW_LIMITS))
        self.assertIsNone(result['cluster_contribution'])
        self.assertIsNone(result['clusters'])
        self.assertFalse(result['formal_permission'])

    def test_missing_duplicate_foreign_and_out_of_order_layouts_reject(self):
        with self.assertRaisesRegex(ValueError, 'strictly increasing unique'):
            seed.aggregate_saved_seed(self.entries[:1] + self.entries[:1],
                                      registered_seed_index=0)
        with self.assertRaisesRegex(ValueError, 'strictly increasing unique'):
            seed.aggregate_saved_seed([self.entries[1], self.entries[0]],
                                      registered_seed_index=0)
        with self.assertRaisesRegex(ValueError, 'foreign chunk'):
            seed.aggregate_saved_seed(self.entries[:1],
                                      registered_seed_index=1)
        result = seed.aggregate_saved_seed(self.entries[:11],
                                           registered_seed_index=0)
        self.assertIsNone(result['cluster_contribution'])
        self.assertEqual(result['missing_layouts'], [11])

    def test_external_pin_stale_attempt_and_identity_mutation_reject(self):
        tampered = copy.deepcopy(self.entries[0])
        tampered['expected_pins']['rows'] = pin(b'wrong')
        with self.assertRaisesRegex(ValueError, 'external rows pin'):
            seed.aggregate_saved_seed([tampered], registered_seed_index=0)
        current = chunk_entry(0, latest_attempt=2)
        self.assertEqual(seed.aggregate_saved_seed(
            [current], registered_seed_index=0)['source_chunks'][0]
            ['latest_attempt'], 2)
        stale = chunk_entry(0, latest_attempt=2, stale_report=True)
        with self.assertRaisesRegex(ValueError, 'report attempt'):
            seed.aggregate_saved_seed([stale], registered_seed_index=0)
        wrong = copy.deepcopy(self.entries[0])
        rows = v.strict_json(wrong['rows_raw'])
        rows['rows'][0]['identity'] = rows['rows'][1]['identity']
        rewrap(wrong, 'rows', rows)
        result = v.strict_json(wrong['result_raw'])
        result['row_projection_pin'] = wrong['expected_pins']['rows']
        rewrap(wrong, 'result', result)
        with self.assertRaisesRegex(ValueError, 'fresh reread row projection'):
            seed.aggregate_saved_seed([wrong], registered_seed_index=0)

    def test_inconclusive_latest_outcome_remains_inconclusive(self):
        entries = [chunk_entry(0, inconclusive_first=True), *self.entries[1:]]
        result = seed.aggregate_saved_seed(entries, registered_seed_index=0)
        candidate = seed.arithmetic.CANDIDATES[0]
        layer = seed.arithmetic.STRATA[0]
        contribution = result['cluster_contribution']
        self.assertEqual(contribution['cluster']['candidates'][candidate]
                         [layer]['profile_status'], 'inconclusive')
        self.assertEqual(contribution['slice_source_cluster']['candidates']
                         [candidate][layer]['profile_inconclusive_evaluations'], 1)
        self.assertFalse(result['analysis_authorized'])

if __name__ == '__main__':
    unittest.main()
