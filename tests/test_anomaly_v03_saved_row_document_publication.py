"""Publication stops, provenance mutations and pinned fresh readback."""
import copy
from contextlib import ExitStack, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_saved_row_document_publication as publication
from banto_ai import anomaly_v03_preformal_saved_row_document_budget as saved
from tests import test_anomaly_v03_preformal_saved_row_document_budget as saved_tests
from tests import test_anomaly_v03_preformal_contiguous_document_budget as helpers


class FakePublicationBudget(helpers.FakeBudget):
    def close(self):
        report = super().close()
        report['both_arithmetic_child_exits_reported'] = all(
            name in self.roles and self.roles[name]['exit']
            for name in ('analysis', 'audit'))
        report['all_four_child_exits_reported'] = (
            set(self.roles) == {'analysis', 'audit', 'writer', 'reader'} and
            all(row['exit'] for row in self.roles.values()))
        return report


class PublicationOrchestrationTests(unittest.TestCase):
    setUpClass = classmethod(saved_tests.SavedRowDocumentBudgetTests.setUpClass.__func__)
    run_trial = saved_tests.SavedRowDocumentBudgetTests.run_trial

    def setUp(self):
        saved_tests.SavedRowDocumentBudgetTests.setUp(self)
        stack = ExitStack()
        self.addCleanup(stack.close)
        FakePublicationBudget.instances = []
        FakePublicationBudget.stop_phase = None
        stack.enter_context(patch.object(publication, 'PublicationBudget', FakePublicationBudget))
        self.writer_failure = False
        self.reader_failure = False
        self.publication = stack.enter_context(patch.object(publication, 'publish', side_effect=self.publish))

    def publish(self, root, budget, result, *args):
        result['stage'] = 'writer'
        budget.checkpoint('writer')
        if self.writer_failure:
            raise ValueError('writer failed')
        budget.record_role('writer', 'complete', worker_pid=102, exit_confirmed=True)
        result['writer_reaped_before_reader_start'] = True
        result['stage'] = 'reader'
        budget.checkpoint('reader')
        if self.reader_failure:
            raise ValueError('reader failed')
        budget.record_role('reader', 'complete', worker_pid=103, exit_confirmed=True)
        result.update(local_publication_performed=True, publication_performed=True)

    def test_same_budget_requires_all_four_exits_and_keeps_formal_closed(self):
        result = self.run_trial(publish_document=True)
        self.assertEqual(result['status'], 'measured')
        self.assertEqual(result['format'], publication.FORMAT)
        self.assertTrue(result['same_budget_saved_rows_to_fresh_reader_measured'])
        self.assertTrue(result['all_four_child_exits_reported'])
        budget = FakePublicationBudget.instances[0]
        self.assertEqual(len(FakePublicationBudget.instances), 1)
        self.assertTrue(budget.closed)
        self.assertLess(budget.phases.index('slices'), budget.phases.index('writer'))
        self.assertLess(budget.phases.index('writer'), budget.phases.index('reader'))
        self.assertLess(budget.phases.index('reader'), budget.phases.index('postflight'))
        self.assertFalse(result['formal_permission'])
        self.assertFalse(result['full_end_to_end_budget_measured'])

    def test_writer_failure_never_starts_reader(self):
        self.writer_failure = True
        result = self.run_trial(publish_document=True)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['stage'], 'writer')
        self.assertNotIn('reader', FakePublicationBudget.instances[0].phases)
        self.assertFalse(result['same_budget_saved_rows_to_fresh_reader_measured'])

    def test_reader_failure_keeps_writer_exit_and_failed_attempt(self):
        self.reader_failure = True
        result = self.run_trial(publish_document=True)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['writer_reaped_before_reader_start'])
        self.assertFalse(result['all_four_child_exits_reported'])
        self.assertTrue((self.parent/'trial-one/result.json').exists())

    def test_stop_before_writer_preserves_latched_failure(self):
        FakePublicationBudget.stop_phase = 'writer'
        result = self.run_trial(publish_document=True)
        self.assertEqual(result['reason'], 'pipeline_wall_limit')
        self.assertNotIn('writer', FakePublicationBudget.instances[0].roles)
        self.assertTrue(FakePublicationBudget.instances[0].closed)

    def test_unreaped_publication_owner_is_retained_and_raised(self):
        owner = publication.supervisor.UnreapedWorker(object(), {})
        self.publication.side_effect = owner
        with self.assertRaises(publication.supervisor.UnreapedWorker) as raised:
            self.run_trial(publish_document=True)
        self.assertIs(raised.exception, owner)
        self.assertEqual(owner.receipt, self.parent/'trial-one')
        self.assertTrue(FakePublicationBudget.instances[0].closed)
        self.assertEqual(json.loads((owner.receipt/'result.json').read_bytes())['reason'],
                         'owned_publication_child_exit_unconfirmed')

    def test_nonboolean_publication_selection_rejects_before_root(self):
        with self.assertRaises(ValueError):
            self.run_trial(publish_document=1)
        self.assertFalse(self.parent.exists())


class PublicationPayloadTests(unittest.TestCase):
    """Small arithmetic-shaped data tests mappings, never full draw evidence."""
    @classmethod
    def setUpClass(cls):
        saved_tests.SavedRowDocumentBudgetTests.setUpClass.__func__(cls)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='saved-publication-')
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name).resolve()
        self.root = self.parent/'trial-one'
        self.root.mkdir()
        self.addCleanup(patch.stopall)
        patch.object(publication, 'OUTPUT_PARENT', self.parent).start()
        fixture = json.loads(self.prepared['files']['fixture/input.json'])
        source = json.loads(self.prepared['files']['fixture/slices.json'])
        input_pins = self.prepared['binding']['worker_input_pins']
        (self.root/'inputs').mkdir()
        for name, raw in self.prepared['files'].items():
            (self.root/'inputs'/Path(name).name).write_bytes(raw)
        projection_pin = saved.chain._write_value(self.root/'projection.json', self.prepared['binding'], 8*1024**2)
        binding = {'clusters': fixture['clusters'], 'projection_pins': input_pins,
                   'saved_row_projection_pin': projection_pin}
        result = {'saved_row_projection_pin': projection_pin,
                  'input_pin': saved.chain._write_value(self.root/'input.json',
                    saved._draw_input(binding, saved_tests.REVISION), 512*1024)}
        calc = saved.chain.document_bridge.adapter.inference.compute_fixture_tables(
            fixture['clusters'], [list(range(40))], engineering_ready=False)
        # Only the shape is enlarged; these tests make no arithmetic claim.
        calc['replicate_count'] = 50000
        result['calculation_pin'] = saved.chain._write_value(self.root/'calculation.json', calc, saved.chain.MAX_CONTROL)
        audit = {'format':'anomaly-v03-preformal-draw-budget-audit-v1',
            'status':'invented_primary_numerics_matched', 'draw_sha256':saved.chain.draw_bridge.frozen.BOOTSTRAP_HASH,
            'clusters':40, 'replicates':50000, 'candidate_tables':9, 'primary_estimates':117,
            'paired_estimates':72, 'gates':180, 'calculation_sha256':result['calculation_pin']['sha256'],
            'registered_data_read':False, 'formal_bootstrap_performed':False,
            'independent_s6_complete':False, 'formal_permission':False, 'promotion_allowed':False,
            'performance_status':'not_evaluated'}
        result['arithmetic_audit_pin'] = saved.chain._write_value(self.root/'audit.json', audit, saved.chain.MAX_CONTROL)
        budget = helpers.FakeBudget(self.root, saved.chain.LIMITS).start()
        document, schema = saved.chain._document(self.root, binding, fixture, calc, audit, budget, result)
        saved.chain._slices(self.root, binding, fixture, source, document, schema, budget, result)
        self.request = {'receipt_root':str(self.root), 'publication_root':str(self.root/'published'),
            'source_revision':saved_tests.REVISION, 'projection_input_pins':input_pins,
            'projection_pin':projection_pin, 'input_pin':result['input_pin'],
            'payload_source_pins':{name:result[key] for name,key in (
                ('calculation.json','calculation_pin'), ('audit.json','arithmetic_audit_pin'),
                ('document.json','document_pin'), ('slices.json','slices_pin'),
                ('slice-count-audit.json','slice_count_audit_pin'))}}

    def mutate(self, name, edit):
        value = json.loads((self.root/name).read_bytes())
        edit(value)
        self.request['payload_source_pins'][name] = saved.chain._write_value(
            self.root/(name+'.changed'), value, publication.PAYLOAD_LIMITS[name])
        (self.root/name).write_bytes((self.root/(name+'.changed')).read_bytes())

    def test_five_payloads_retain_source_bytes_and_fresh_readback(self):
        files = publication._retained(self.request)
        for name, raw in files.items():
            self.assertEqual(raw, (self.root/name).read_bytes()+b'\n')
        with patch.object(publication.io, '_local_parent', side_effect=lambda path:path):
            writer = publication.io.publish_local_result(self.root, 'published', files,
                verify_semantics=lambda value:publication._semantic(value, files))
            reader = publication.io.verify_local_publication(self.root/'published',
                expected_marker_sha256=writer['marker_raw_sha256'],
                verify_semantics=lambda value:publication._semantic(value, files))
        self.assertTrue(reader['local_verified'])
        self.assertEqual(reader['payloads'], 5)

    def test_valid_raw_pin_cannot_bless_formal_claim(self):
        self.mutate('document.json', lambda value:value.update(formal_permission=True))
        with self.assertRaises(ValueError):
            publication._retained(self.request)

    def test_valid_raw_pin_cannot_bless_changed_slice(self):
        self.mutate('slices.json', lambda value:value['document_draft']['slices'][0].update(denominator=1))
        with self.assertRaisesRegex(ValueError, 'full slice mapping differs'):
            publication._retained(self.request)

    def test_valid_raw_pin_cannot_bless_changed_count_audit(self):
        self.mutate('slice-count-audit.json', lambda value:value.update(main_slice_rows=1232))
        with self.assertRaisesRegex(ValueError, 'independent count audit differs'):
            publication._retained(self.request)

    def test_redirected_publication_rejects_before_input_read(self):
        self.request['publication_root'] = str(self.parent/'outside')
        with patch.object(publication, '_canonical', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError, 'ownership differs'):
                publication._retained(self.request)

    def test_worker_wrong_request_owner_rejects_before_source_read(self):
        path = self.root/'unowned.json'
        raw = publication.io.json_bytes({**self.request, 'format':publication.FORMAT+'-request', 'role':'writer'})
        path.write_bytes(raw)
        with patch.object(publication, '_source_recheck', side_effect=AssertionError('read')), redirect_stdout(StringIO()):
            code = publication.worker_main([str(path), str(len(raw)), publication._pin(raw)['sha256']])
        self.assertEqual(code, 2)


class PublicationRoleBindingTests(unittest.TestCase):
    def test_fresh_reader_identity_reuse_rejects_before_terminal_success(self):
        with tempfile.TemporaryDirectory(prefix='publication-role-') as directory:
            root = Path(directory).resolve()
            pin = publication._pin(b'fixture')
            result = dict(saved_row_projection_pin=pin, input_pin=pin,
                          calculation_pin=pin, arithmetic_audit_pin=pin,
                          document_pin=pin, slices_pin=pin, slice_count_audit_pin=pin)
            budget = helpers.FakeBudget(root, saved.chain.LIMITS).start()
            reply = {'marker_raw_sha256':'a'*64, 'process':{'pid':123,'start_token':'same'}}
            with patch.object(publication, '_retained', return_value={'fixture.json':b'{}\n'}), \
                 patch.object(publication, '_role', return_value=reply) as role, \
                 patch.object(publication.io, 'verify_local_publication') as verify:
                with self.assertRaisesRegex(ValueError, 'process identity differs'):
                    publication.publish(root, budget, result, 'b'*40, {}, {})
            self.assertEqual([call.args[0]['role'] for call in role.call_args_list], ['writer','reader'])
            self.assertTrue(result['writer_reaped_before_reader_start'])
            verify.assert_not_called()
            self.assertNotIn('local_publication_performed', result)


if __name__ == '__main__':
    unittest.main()
