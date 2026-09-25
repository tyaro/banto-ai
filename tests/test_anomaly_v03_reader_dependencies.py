"""Dependency snapshots remain bounded observations, not closure acceptance."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import _anomaly_v03_reader_dependencies as dep
from banto_ai import anomaly_v03_reader_evidence as observed
from tests import test_anomaly_v03_reader_evidence as fixtures


class DependencyChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'src').mkdir()
        self.path=self.root/'src/example.py';self.path.write_bytes(b'value = 1\n')
        self.row={**dep.file_observation(self.path),'category':'project','native':False}
        self.name='project/src/example.py'
        self.snapshot={'format':dep.FORMAT,'scope':dict(dep.SCOPE),
            'files':{self.name:self.row},'native_files':[],
            'modules':{'example':{'kind':'file','file':self.name,'cache_candidate':None}}}

    def verify(self,before=None,after=None,git=None):
        with patch.object(dep,'system32',return_value=self.root/'System32'):
            return dep.verify_pair(before or self.snapshot,after or self.snapshot,root=self.root,
                revision='a'*40,git=git or (lambda *args:b'value = 1\n'),required_sources=['src/example.py'])

    def test_disk_git_match_is_only_an_observation(self):
        result=self.verify()
        self.assertEqual(result['project_files'],1)
        for name in ('source_closure_complete','runtime_closure_complete','execution_authenticated','formal_permission'):
            self.assertIs(result[name],False)
        self.assertEqual(result['expectation_origin'],'child-inventory-crosschecked-by-parent-after-exit')

    def test_source_with_same_length_changed_content_is_rejected(self):
        self.path.write_bytes(b'value = 2\n')
        with self.assertRaisesRegex(ValueError,'disk mismatch'):self.verify()

    def test_git_raw_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'working/Git bytes differ'):
            self.verify(git=lambda *args:b'value = 1\r\n')

    def test_source_hardlink_rejected_native_hardlink_recorded(self):
        os.link(self.path,self.root/'alias.py')
        with self.assertRaisesRegex(ValueError,'hardlink'):dep.file_observation(self.path)
        self.assertEqual(dep.file_observation(self.path,native=True)['identity']['links'],2)

    def test_file_cap_rejects_before_open(self):
        with patch.object(Path,'open',side_effect=AssertionError('opened')),self.assertRaisesRegex(ValueError,'file limit'):
            dep.file_observation(self.path,maximum=2)

    def test_unapproved_path_rejected_before_hash(self):
        value=copy.deepcopy(self.snapshot);value['files'][self.name]['physical_path']=str(self.root/'outside.py')
        with patch.object(dep,'file_observation',side_effect=AssertionError('read')),self.assertRaisesRegex(ValueError,'permitted'):
            self.verify(value,value)

    def test_missing_required_source_rejected(self):
        with patch.object(dep,'system32',return_value=self.root/'System32'),self.assertRaisesRegex(ValueError,'required reader'):
            dep.verify_pair(self.snapshot,self.snapshot,root=self.root,revision='a'*40,
                git=lambda *args:b'value = 1\n',required_sources=['src/missing.py'])

    def test_new_builtin_import_is_recorded(self):
        after=copy.deepcopy(self.snapshot)
        after['modules']['new_builtin']={'kind':'built-in','file':None,'cache_candidate':None}
        self.assertEqual(self.verify(after=after)['added_modules_during_read'],['new_builtin'])

    def test_disappearing_module_is_rejected(self):
        after=copy.deepcopy(self.snapshot);after['modules']={}
        with self.assertRaisesRegex(ValueError,'changed/disappeared'):self.verify(after=after)

    def test_cache_candidate_reference_is_checked(self):
        value=copy.deepcopy(self.snapshot);value['modules']['example']['cache_candidate']=self.name
        with self.assertRaisesRegex(ValueError,'cache candidate reference'):self.verify(value,value)


@unittest.skipUnless(os.name=='nt','Windows loaded image observations')
class LiveDependencies(unittest.TestCase):
    """Run from a Git/raw-matching candidate checkout; current CRLFs stay intact."""
    def setUp(self):
        self.fixture=fixtures.ReaderEvidenceTests('test_observed_reader_binds_retained_expectations')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def call(self):
        published=self.fixture.publish()
        return self.fixture.call(self.fixture.request(published),observe_dependencies=True)

    def test_real_reader_records_imports_images_and_cache_candidates(self):
        result=self.call();self.assertEqual(result['status'],'verified',result)
        supplement=result['dependency_observation']
        self.assertGreater(supplement['project_files'],10)
        self.assertGreater(supplement['native_files'],2)
        target=Path(result['check_directory']);saved=json.loads((target/'dependencies.json').read_bytes())
        self.assertEqual(result['dependency_pin'],observed._pin((target/'dependencies.json').read_bytes()))
        rows=saved['after']['files'];categories={r['category'] for r in rows.values()}
        self.assertTrue({'project','stdlib','native','extension'} <= categories)
        self.assertNotIn('site',saved['after']['modules'])
        self.assertIn('banto_ai.manifest',saved['after']['modules'])
        self.assertFalse(supplement['runtime_closure_complete'])
        monitor=json.loads((target/'supervision.json').read_bytes())
        self.assertEqual(monitor['exit_code'],0);self.assertTrue(monitor['worker_exit_confirmed'])
        self.assertLess(monitor['output']['bytes'],observed.DEPENDENCY_LIMITS['output_bytes'])

    def test_resealed_child_hash_fails_parent_disk_comparison(self):
        original=observed.supervisor.supervise
        def corrupt(*args,**kwargs):
            report=original(*args,**kwargs);self.assertEqual(report['status'],'complete',report)
            path=Path(args[2])/'report.json';reply=json.loads(path.read_bytes())
            name=reply['dependencies_before']['native_files'][0]
            for key in ('dependencies_before','dependencies_after'):
                reply[key]['files'][name]['pin']['sha256']='a'*64
            raw=observed.io.json_bytes(reply);path.write_bytes(raw);report['output']=observed._pin(raw)
            return report
        with patch.object(observed.supervisor,'supervise',corrupt):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertIn('parent dependency disk mismatch',result['detail'])
        self.assertFalse((Path(result['check_directory'])/'binding.json').exists())


if __name__=='__main__':unittest.main()
