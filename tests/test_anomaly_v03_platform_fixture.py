"""Unadopted 26H2 platform fixture contract and explicitly enabled native runs."""
import copy
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_engineering_contract as old_contract
from banto_ai import anomaly_v03_fixture_publication as publication
from banto_ai import anomaly_v03_platform_fixture as platform_fixture
from banto_ai import anomaly_v03_platform_fixture_runtime as runtime
from tests import test_anomaly_v03_fixture_publication as supplied


class PlatformRuntimeContractTests(unittest.TestCase):
    def test_exact_candidate_accepts_only_its_own_tuple(self):
        self.assertEqual(runtime.validate_runtime(dict(runtime.EXPECTED)), runtime.EXPECTED)
        changes = {
            'os': 'Windows 11 Enterprise', 'release': '25H2',
            'os_major': 11, 'os_minor': 1, 'os_build': 26200, 'os_ubr': 9458,
            'architecture': 'ARM64', 'filesystem': 'local-ReFS',
            'implementation': 'PyPy', 'python_version': '3.14.1',
            'pointer_bits': 32, 'gil_disabled': True,
            'compiler': 'MSC v.1945', 'source_tag': 'different',
            'python_exe_raw_sha256': '0' * 64,
            'python_dll_raw_sha256': '0' * 64,
        }
        for field, replacement in changes.items():
            with self.subTest(field=field):
                value = dict(runtime.EXPECTED);value[field] = replacement
                with self.assertRaisesRegex(ValueError, 'unsupported platform fixture runtime'):
                    runtime.validate_runtime(value)
        for value in ({**runtime.EXPECTED, 'extra': 1},
                      {k: v for k, v in runtime.EXPECTED.items() if k != 'release'},
                      {**runtime.EXPECTED, 'pointer_bits': True}):
            with self.assertRaisesRegex(ValueError, 'unsupported platform fixture runtime'):
                runtime.validate_runtime(value)

    def test_old_engineering_validator_still_rejects_26h2(self):
        with self.assertRaisesRegex(ValueError, 'unsupported engineering runtime'):
            old_contract.validate_runtime(dict(runtime.EXPECTED))

    def test_platform_scope_restores_old_runtime_and_source_bindings(self):
        before = (publication.EXTRA_SOURCES, publication.SOURCE_FILES,
                  publication.BOOTSTRAP, publication.supervisor.resources.probe_runtime,
                  publication.supervisor.policy)
        with platform_fixture._platform_scope():
            self.assertEqual(publication.EXTRA_SOURCES, platform_fixture.EXTRA_SOURCES)
            self.assertEqual(publication.SOURCE_FILES, platform_fixture.SOURCE_FILES)
            self.assertEqual(publication.BOOTSTRAP, platform_fixture.BOOTSTRAP)
            self.assertIs(publication.supervisor.resources.probe_runtime, runtime.probe_runtime)
            self.assertIs(publication.supervisor.policy.validate_runtime, runtime.validate_runtime)
        self.assertEqual((publication.EXTRA_SOURCES, publication.SOURCE_FILES,
                          publication.BOOTSTRAP, publication.supervisor.resources.probe_runtime,
                          publication.supervisor.policy), before)
        with self.assertRaisesRegex(RuntimeError, 'stop'):
            with platform_fixture._platform_scope():
                raise RuntimeError('stop')
        self.assertEqual((publication.EXTRA_SOURCES, publication.SOURCE_FILES,
                          publication.BOOTSTRAP, publication.supervisor.resources.probe_runtime,
                          publication.supervisor.policy), before)

    def test_platform_root_and_identifier_are_separate(self):
        self.assertEqual(platform_fixture.POLICY_ID, 'anomaly-v03-single-writer-platform-v2')
        self.assertEqual(platform_fixture.OUTPUT_PARENT,
                         publication.ROOT / 'artifacts' / 'anomaly-v03-engineering-platform-v2')
        self.assertNotEqual(platform_fixture.POLICY_ID, old_contract.POLICY_ID)
        self.assertNotEqual(platform_fixture.FORMAT, publication.FORMAT)
        self.assertIn('src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
                      platform_fixture.SOURCE_FILES)

    def test_runtime_change_after_publication_keeps_platform_status_failed(self):
        files, analysis, audit = supplied.example()
        rows = {name: {'path': str(platform_fixture.ROOT / 'artifacts' / ('input-' + name.replace('/', '-'))),
                       'pin': publication.observed._pin(raw), 'links': 1}
                for name, raw in files.items()}
        request = {'format': publication.FORMAT, 'mode': 'fixture', 'inputs': rows,
                   'analysis_reference': analysis, 'audit_reference': audit}
        changed = dict(runtime.EXPECTED);changed['os_ubr'] += 1
        with tempfile.TemporaryDirectory(prefix='banto-platform-change-') as directory:
            target = Path(directory) / 'attempt'
            mock_result = {'status': 'verified', 'result_pin': publication.observed._pin(b'{}'),
                           'publication_status': 'completed', 'reader_status': 'completed'}
            with patch.object(platform_fixture, '_target', return_value=target), \
                 patch.object(runtime, 'probe_runtime', side_effect=[dict(runtime.EXPECTED), changed]), \
                 patch.object(publication, 'publish_with_evidence', return_value=mock_result):
                result = platform_fixture.publish_fixture(request,
                    expected_revision='a' * 40, receipt_name='attempt')
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['reason'], 'platform_fixture_rejected')
            self.assertIn('platform fixture runtime changed', result['detail'])
            self.assertEqual(result['reader_status'], 'completed')
            self.assertFalse(result['formal_permission'])
            self.assertEqual(json.loads((target / 'platform-result.json').read_bytes())['status'], 'failed')


@unittest.skipUnless(os.name == 'nt' and sys.version_info[:2] == (3, 14) and
                     os.environ.get('BANTO_PLATFORM_FIXTURE_NATIVE') == '1',
                     'explicit 26H2 native fixture run')
class NativePlatformFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime.probe_runtime(publication.ROOT)
        cls.files, cls.analysis, cls.audit = supplied.example()
        cls.revision = subprocess.check_output(
            ['git', '-C', str(publication.ROOT), 'rev-parse', 'HEAD'], text=True).strip()

    def setUp(self):
        token = secrets.token_hex(8)
        parent = platform_fixture.OUTPUT_PARENT
        parent.mkdir(exist_ok=True)
        self.inputs = parent / ('inputs-' + token)
        self.inputs.mkdir()
        self.name = 'native-' + token
        rows = {}
        for name, raw in self.files.items():
            path = self.inputs / name.replace('/', '-')
            path.write_bytes(raw)
            rows[name] = {'path': str(path), 'pin': publication.observed._pin(raw), 'links': 1}
        self.request = {'format': publication.FORMAT, 'mode': 'fixture', 'inputs': rows,
                        'analysis_reference': copy.deepcopy(self.analysis),
                        'audit_reference': copy.deepcopy(self.audit)}

    def run_flow(self, name=None):
        return platform_fixture.publish_fixture(self.request, expected_revision=self.revision,
                                                receipt_name=name or self.name)

    def test_actual_writer_reaped_then_separate_reader_and_no_overwrite(self):
        order = []
        original = publication._run_role
        def observed_role(role, *args):
            if role == 'reader':
                self.assertEqual(order, ['writer_reaped'])
            result = original(role, *args)
            self.assertTrue(result['worker_exit_confirmed'])
            order.append(role + '_reaped')
            return result
        with patch.object(publication, '_run_role', side_effect=observed_role):
            result = self.run_flow()
        self.assertEqual(result['status'], 'verified', result)
        self.assertEqual(order, ['writer_reaped', 'reader_reaped'])
        root = Path(result['check_directory'])
        inner = json.loads((root / 'result.json').read_bytes())
        self.assertEqual(inner['status'], 'verified', inner)
        writer_evidence = json.loads((root / 'writer/evidence.json').read_bytes())
        reader_evidence = json.loads((root / 'reader/evidence.json').read_bytes())
        self.assertNotEqual(writer_evidence['invocation_id'], reader_evidence['invocation_id'])
        self.assertNotEqual(writer_evidence['process']['start_token'],
                            reader_evidence['process']['start_token'])
        self.assertTrue((root / 'published/.complete').is_file())
        for role in ('writer', 'reader'):
            row = inner[role]
            for field, name in (('dependency_pin', 'dependencies.json'),
                                ('stdout_pin', 'worker/report.json'),
                                ('supervision_pin', 'supervision.json')):
                self.assertEqual(row[field], publication.observed._pin((root / role / name).read_bytes()))
        for name in publication.PAYLOADS:
            self.assertEqual((root / 'published/payload' / name).read_bytes(),
                             self.files['wrapper/' + name] + b'\n')
        before = (root / 'published/payload/analysis.json').read_bytes()
        with self.assertRaises((ValueError, OSError)):
            self.run_flow()
        self.assertEqual((root / 'published/payload/analysis.json').read_bytes(), before)
        self.assertFalse(result['formal_permission'])
        self.assertFalse(result['registered_data_read'])

    def test_saved_writer_observation_tamper_rejected_with_failure_receipt(self):
        for name in ('supervision.json', 'worker/report.json', 'dependencies.json'):
            with self.subTest(name=name):
                receipt_name = self.name + '-' + name.replace('/', '-').replace('.', '-')
                target = platform_fixture.OUTPUT_PARENT / receipt_name
                if name == 'worker/report.json':
                    original = publication.dependencies.verify_pair
                    def changed(*args, **kwargs):
                        value = original(*args, **kwargs)
                        (target / 'writer/worker/report.json').write_bytes(b'{}\n')
                        return value
                    context = patch.object(publication.dependencies, 'verify_pair', side_effect=changed)
                else:
                    original = publication.observed._save
                    def changed(path, value):
                        original(path, value)
                        if Path(path) == target / 'writer' / name:
                            Path(path).write_bytes(b'{}\n')
                    context = patch.object(publication.observed, '_save', side_effect=changed)
                with context:
                    result = self.run_flow(receipt_name)
                self.assertEqual(result['status'], 'failed', result)
                self.assertIn('retained writer ' + name + ' changed', result['detail'])
                self.assertEqual(result['publication_status'], 'unconfirmed')
                self.assertTrue((target / 'published/.complete').is_file())
                self.assertFalse((target / 'reader').exists())
                self.assertEqual(json.loads((target / 'platform-result.json').read_bytes())['status'], 'failed')

    def test_published_payload_tamper_blocks_reader(self):
        target = platform_fixture.OUTPUT_PARENT / self.name
        original = publication._run_role
        def role(name, *args):
            if name == 'reader':
                (target / 'published/payload/analysis.json').write_bytes(b'{}\n')
            return original(name, *args)
        with patch.object(publication, '_run_role', side_effect=role):
            result = self.run_flow()
        self.assertEqual(result['status'], 'failed', result)
        self.assertEqual(result['publication_status'], 'completed')
        self.assertNotEqual(result['reader_status'], 'completed')
        self.assertTrue((target / 'writer/result.json').is_file())
        self.assertEqual(json.loads((target / 'platform-result.json').read_bytes())['status'], 'failed')
