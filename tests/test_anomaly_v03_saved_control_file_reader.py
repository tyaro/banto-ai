"""Pinned disk inventory, mutation, byte bounds and continuous runner stops."""
import copy
from contextlib import ExitStack
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_saved_control_file_reader as reader
from banto_ai import anomaly_v03_preformal_saved_row_document_budget as saved
from tests import test_anomaly_v03_saved_row_document_publication as pub_tests
from tests import test_anomaly_v03_preformal_saved_row_document_budget as saved_tests


class Checkpoints:
    def __init__(self, stop=False):
        self.phases = []
        self.stop = stop

    def checkpoint(self, phase):
        self.phases.append(phase)
        if self.stop:
            raise saved.chain.draw_bridge.resources.ResourceStop('pipeline_wall_limit')


class ControlFileReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='control-files-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.workspace = Path(cls.temporary.name).resolve()
        cls.root = cls.workspace/'artifacts'/ (reader.PREFIX+'test')
        cls.root.mkdir(parents=True)
        cls.raw = b'{"fixture":true}'
        cls.entries = []
        for number in range(480):
            chunk = cls.root/'controls'/f'{number:03d}'
            chunk.mkdir(parents=True)
            row = {}
            for name in reader.coverage.RAW_LIMITS:
                (chunk/(name+'.json')).write_bytes(cls.raw)
                row[name] = {'path':f'controls/{number:03d}/{name}.json',
                             'pin':saved.chain.draw_bridge._pin(cls.raw)}
            cls.entries.append(row)
        cls.index = {'format':reader.INDEX_FORMAT, 'entries':cls.entries,
            'fixture_controls':True, 'formal_permission':False,
            'registered_observations_read':False,
            'construction_used_cached_identity_fixture':True, 'source_revision':'a'*40}
        cls.index_raw = reader.v.canonical_json(cls.index)

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(reader, 'ROOT', self.workspace))
        (self.root/'pinset.json').write_bytes(self.index_raw)
        self.pin = saved.chain.draw_bridge._pin(self.index_raw)
        self.budget = Checkpoints()

    def load(self):
        return reader.load_controls(self.root, expected_pinset_pin=self.pin, budget=self.budget)

    def changed_index(self, change):
        value = copy.deepcopy(self.index)
        change(value)
        raw = reader.v.canonical_json(value)
        (self.root/'pinset.json').write_bytes(raw)
        self.pin = saved.chain.draw_bridge._pin(raw)

    def test_fixed_disk_inventory_and_final_reread_share_live_checkpoints(self):
        loaded = self.load()
        self.assertEqual(len(loaded['entries']), 480)
        self.assertEqual(loaded['entries'][479]['rows_raw'], self.raw)
        summary = loaded['summary']
        self.assertEqual(summary['control_files'], 4800)
        self.assertEqual(summary['control_bytes'], 4800*len(self.raw))
        self.assertEqual(summary['total_input_bytes_including_index'],4800*len(self.raw)+len(self.index_raw))
        self.assertFalse(summary['real_saved_chunk_reader_used'])
        checked = reader.recheck_controls(loaded, budget=self.budget)
        self.assertTrue(checked['disk_pin_recheck_completed'])
        self.assertIn('control-read',self.budget.phases)
        self.assertIn('control-reread',self.budget.phases)

    def test_valid_index_pin_cannot_redirect_control_path(self):
        self.changed_index(lambda value:value['entries'][0]['rows'].update(path='../outside.json'))
        with patch.object(reader, '_read_chunks', side_effect=AssertionError('payload read')):
            with self.assertRaisesRegex(ValueError,'fixed control descriptor path'):
                self.load()

    def test_total_declared_bytes_stop_before_payload_read(self):
        def enlarged(value):
            for entry in value['entries']:
                entry['stdout']['pin']['bytes']=1024**2
        self.changed_index(enlarged)
        with patch.object(reader, '_read_chunks', side_effect=AssertionError('payload read')):
            with self.assertRaisesRegex(ValueError,'total input byte bound'):
                self.load()

    def test_missing_and_duplicate_position_inventory_rejects(self):
        for change in (lambda value:value['entries'].pop(),
                       lambda value:value['entries'].__setitem__(1,value['entries'][0])):
            with self.subTest(change=change):
                self.changed_index(change)
                with self.assertRaises(ValueError):
                    self.load()

    def test_closed_index_claims_reject_even_with_matching_raw_pin(self):
        for claim in ('formal_permission','registered_observations_read'):
            self.changed_index(lambda value:value.update({claim:True}))
            with self.assertRaisesRegex(ValueError,'only invented'):
                self.load()

    def test_disk_mutation_after_load_is_rejected_without_using_cached_raw(self):
        loaded = self.load()
        path = self.root/'controls/479/rows.json'
        self.addCleanup(path.write_bytes,self.raw)
        path.write_bytes(self.raw+b' ')
        with self.assertRaises(ValueError):
            reader.recheck_controls(loaded,budget=self.budget)

    def test_index_mutation_after_load_uses_original_external_pin(self):
        loaded = self.load()
        (self.root/'pinset.json').write_bytes(self.index_raw+b' ')
        with self.assertRaises(ValueError):
            reader.recheck_controls(loaded,budget=self.budget)

    def test_extra_control_file_rejects(self):
        extra = self.root/'controls/000/extra.json'
        extra.write_bytes(self.raw)
        self.addCleanup(extra.unlink)
        with self.assertRaisesRegex(ValueError,'inventory differs'):
            self.load()

    def test_multiply_linked_payload_rejects(self):
        extra = self.root/'linked-control.json'
        os.link(self.root/'controls/000/rows.json',extra)
        self.addCleanup(extra.unlink)
        with self.assertRaises(ValueError):
            self.load()

    def test_latched_stop_prevents_index_read(self):
        self.budget.stop=True
        with patch.object(reader.pinned,'read_pinned',side_effect=AssertionError('read')):
            with self.assertRaises(saved.chain.draw_bridge.resources.ResourceStop):
                self.load()


class FakeControlFileBudget(pub_tests.FakePublicationBudget):
    pass


class DiskControlPipelineTests(unittest.TestCase):
    setUpClass = classmethod(saved_tests.SavedRowDocumentBudgetTests.setUpClass.__func__)
    publish = pub_tests.PublicationOrchestrationTests.publish

    def setUp(self):
        pub_tests.PublicationOrchestrationTests.setUp(self)
        self.stack=ExitStack()
        self.addCleanup(self.stack.close)
        FakeControlFileBudget.instances=[]
        FakeControlFileBudget.stop_phase=None
        self.stack.enter_context(patch.object(reader,'ControlFileBudget',FakeControlFileBudget))
        self.source=reader.ROOT/'artifacts'/(reader.PREFIX+'test')
        self.index_pin=saved.chain.draw_bridge._pin(b'index')
        self.loaded={'entries':self.entries,'summary':{'fixture':True},'index':{},'index_raw':b'index'}
        self.load=self.stack.enter_context(patch.object(reader,'load_controls',return_value=self.loaded))
        self.recheck=self.stack.enter_context(patch.object(reader,'recheck_controls',return_value={
            'disk_pin_recheck_completed':True,'formal_permission':False}))

    def run_trial(self, **options):
        arguments=dict(control_root=self.source,expected_control_pinset_pin=self.index_pin,
            expected_mode='fixture',expected_input_pins=self.pins,expected_revision=saved_tests.REVISION,
            receipt_name='trial-one',receipt_parent=self.parent)
        arguments.update(options)
        return saved.run_saved_control_files(**arguments)

    def test_disk_load_and_final_reread_are_inside_the_same_four_role_budget(self):
        result=self.run_trial()
        self.assertEqual(result['status'],'measured')
        self.assertEqual(result['format'],reader.PIPELINE_FORMAT)
        self.assertEqual(len(FakeControlFileBudget.instances),1)
        budget=FakeControlFileBudget.instances[0]
        self.assertIs(self.load.call_args.kwargs['budget'],budget)
        self.assertIs(self.recheck.call_args.kwargs['budget'],budget)
        self.assertTrue(budget.closed)
        self.assertTrue(result['same_budget_control_disk_to_fresh_reader_measured'])
        self.assertTrue(result['saved_control_loading_inside_budget'])
        self.assertFalse(result['external_saved_control_bytes_in_directory_budget'])
        self.assertFalse(result['full_end_to_end_budget_measured'])
        self.assertFalse(result['real_saved_chunk_reader_used'])

    def test_read_rejection_keeps_failure_before_arithmetic(self):
        self.load.side_effect=ValueError('control raw pin changed')
        result=self.run_trial()
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['stage'],'control-read')
        self.arithmetic.assert_not_called()
        self.publication.assert_not_called()
        self.assertTrue(FakeControlFileBudget.instances[0].closed)

    def test_final_disk_recheck_failure_keeps_completed_publication_but_failed_trial(self):
        self.recheck.side_effect=ValueError('control changed on disk')
        result=self.run_trial()
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['stage'],'control-reread')
        self.assertTrue(result['local_publication_performed'])
        self.assertFalse(result['same_budget_control_disk_to_fresh_reader_measured'])
        self.assertFalse(result['control_disk_pin_recheck_completed'])
        self.assertFalse(result['formal_permission'])

    def test_mixed_supplied_bytes_and_disk_source_reject_before_root(self):
        with self.assertRaises(ValueError):
            saved.run_saved_rows(self.entries,expected_mode='fixture',expected_input_pins=self.pins,
                expected_revision=saved_tests.REVISION,receipt_name='trial-one',receipt_parent=self.parent,
                publish_document=True,control_root=self.source,expected_control_pinset_pin=self.index_pin)
        self.assertFalse(self.parent.exists())


if __name__ == '__main__':
    unittest.main()
