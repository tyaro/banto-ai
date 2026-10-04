"""Retained invented slice publication: owned writer/readback and fail closure.

This exercises only the new 26H2-compatible preformal route. The old 25H2
fixture publication entry is intentionally outside this test's dependency graph.
"""
from __future__ import annotations

import hashlib
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_bound_slice_publication as publication


ROOT = Path(__file__).resolve().parents[1]
SLICE_ROOT = ROOT / 'artifacts/anomaly-v03-preformal-bound-slice-bridge/trial-01-saved-50000-slices'
POSTCHECK_ROOT = ROOT / 'artifacts/anomaly-v03-preformal-bound-slice-postcheck-01'
SLICE_RESULT_PIN = {'bytes': 7028,
                    'sha256': '86963319de613e43528b306ba364597076055299d488c0c38e27f9f1b0812029'}
POSTCHECK_PIN = {'bytes': 1901,
                 'sha256': '1a1135943da889da91065ecc4c20816ab35a8fc31919415db3cf8cf1d2f41fa8'}
SOURCE_NAMES = ('slices.json', 'audit.json', 'postcheck-result.json')
HAVE_RETAINED = all(path.is_file() for path in (
    SLICE_ROOT / 'result.json', SLICE_ROOT / 'slices.json', SLICE_ROOT / 'audit.json',
    POSTCHECK_ROOT / 'postcheck-result.json', POSTCHECK_ROOT / 'postcheck.py'))


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _head():
    return subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                                   stderr=subprocess.DEVNULL).decode().strip()


class PublicationWorkerGuardTests(unittest.TestCase):
    def test_pinned_request_cannot_redirect_publication_outside_owned_trial(self):
        with tempfile.TemporaryDirectory(prefix='slice-worker-guard-',
                                         dir=ROOT / 'artifacts') as path:
            temporary = Path(path)
            request_path = temporary / 'trial-guard' / 'writer' / 'request.json'
            request_path.parent.mkdir(parents=True)
            outside = temporary / 'outside-publication'
            raw = publication.io.json_bytes({
                'format': publication.REQUEST_FORMAT,
                'role': 'writer',
                'payload_pins': {name: SLICE_RESULT_PIN for name in SOURCE_NAMES},
                'publication_root': str(outside),
            })
            request_path.write_bytes(raw)
            capture = StringIO()
            with (patch.object(publication, '_retained',
                               side_effect=AssertionError('input read before ownership check')),
                  patch.object(publication, '_raw_source_pins',
                               side_effect=AssertionError('source read before ownership check')),
                  redirect_stdout(capture)):
                code = publication.worker_main(
                    [str(request_path), str(len(raw)), _pin(raw)['sha256']])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(capture.getvalue())['error_type'], 'ValueError')
            self.assertFalse(outside.exists())


@unittest.skipUnless(HAVE_RETAINED and os.name == 'nt' and sys.version_info[:2] == (3, 14),
                     'retained invented slice artifacts and Windows CPython 3.14 required')
class SavedSlicePublicationTests(unittest.TestCase):
    def _run(self, parent, name, *, slice_root=SLICE_ROOT, slice_pin=SLICE_RESULT_PIN,
             postcheck_root=POSTCHECK_ROOT, postcheck_pin=POSTCHECK_PIN):
        current_source_pins = publication._raw_source_pins()
        with (patch.object(publication, 'OUTPUT_PARENT', parent),
              patch.object(publication, '_source_pins', return_value=current_source_pins)):
            return publication.run_saved_publication(
                slice_root=slice_root, expected_slice_result_pin=slice_pin,
                postcheck_root=postcheck_root, expected_postcheck_pin=postcheck_pin,
                expected_revision=_head(), trial_name=name)

    def test_owned_writer_reader_preserve_source_and_publication_pins(self):
        with tempfile.TemporaryDirectory(prefix='slice-publication-test-',
                                         dir=ROOT / 'artifacts') as path:
            parent = Path(path) / 'out'
            value = self._run(parent, 'trial-owned-publication')
            target = parent / 'trial-owned-publication'
            saved = json.loads((target / 'result.json').read_bytes())
            self.assertEqual(value['status'], 'verified', value)
            self.assertEqual(saved['status'], 'verified')
            self.assertEqual(saved['publication_status'], 'completed')
            self.assertEqual(saved['reader_status'], 'completed')
            self.assertTrue(saved['writer_reaped_before_reader_start'])
            self.assertTrue(saved['resource_budget_passed'])
            self.assertTrue(saved['local_publication_performed'])
            self.assertEqual(saved['payload_files'], 3)
            self.assertEqual(_pin((target / 'result.json').read_bytes()), value['result_pin'])
            published_root = target / 'published'
            self.assertEqual({p.name for p in published_root.iterdir()},
                             {'payload', 'marker-pending.json', '.complete'})
            self.assertEqual(set((target / 'published/payload').iterdir()),
                             {target / 'published/payload' / name for name in SOURCE_NAMES})
            marker, pending = (published_root / name for name in
                               ('.complete', 'marker-pending.json'))
            self.assertEqual(marker.read_bytes(), pending.read_bytes())
            self.assertEqual(hashlib.sha256(marker.read_bytes()).hexdigest(),
                             saved['marker_raw_sha256'])
            self.assertEqual(marker.stat().st_ino, pending.stat().st_ino)
            self.assertEqual(marker.stat().st_nlink, 2)
            marker_value = json.loads(marker.read_bytes())
            self.assertEqual(len(marker_value['payload_inventory']), 3)
            identities = []
            for role in ('writer', 'reader'):
                role_value = saved[role]
                role_root = target / role
                monitor_raw = (role_root / 'supervision.json').read_bytes()
                launch_raw = (role_root / 'launch.json').read_bytes()
                reply_raw = (role_root / 'worker/report.json').read_bytes()
                monitor, launch = json.loads(monitor_raw), json.loads(launch_raw)
                self.assertEqual(monitor['status'], 'complete')
                self.assertEqual(monitor['exit_code'], 0)
                self.assertIs(monitor['worker_exit_confirmed'], True)
                self.assertIs(role_value['worker_exit_confirmed'], True)
                self.assertEqual(monitor['worker_pid'], role_value['process']['pid'])
                self.assertEqual(launch, {key: value for key, value in
                                          role_value['process'].items()
                                          if key != 'parent_pid'})
                self.assertEqual(role_value['supervision_pin'], _pin(monitor_raw))
                self.assertEqual(role_value['launch_pin'], _pin(launch_raw))
                self.assertEqual(role_value['worker_reply_pin'], _pin(reply_raw))
                self.assertEqual(monitor['output'], _pin(reply_raw))
                self.assertEqual(json.loads((role_root / 'result.json').read_bytes()),
                                 role_value)
                identities.append((role_value['process']['pid'],
                                   role_value['process']['start_token']))
            self.assertEqual(len(set(identities)), 2)
            for name, source_root, source_name in (
                    ('slices.json', SLICE_ROOT, 'slices.json'),
                    ('audit.json', SLICE_ROOT, 'audit.json'),
                    ('postcheck-result.json', POSTCHECK_ROOT, 'postcheck-result.json')):
                source = (source_root / source_name).read_bytes()
                published = (target / 'published/payload' / name).read_bytes()
                self.assertEqual(published, source + b'\n')
                self.assertEqual(saved['source_payload_pins'][name], _pin(source))
                self.assertEqual(saved['payload_pins'][name], _pin(published))
            for key in ('formal_permission', 'formal_document_validated',
                        'independent_s6_complete', 'full_end_to_end_budget_measured',
                        'registered_data_read', 'source_closure_complete',
                        'runtime_closure_complete'):
                self.assertIs(saved[key], False, key)
            self.assertEqual(saved['campaign_evaluations_credited'], 0)
            with self.assertRaises((FileExistsError, ValueError)):
                self._run(parent, 'trial-owned-publication')

    def test_wrong_external_pins_reject_before_new_root_or_role(self):
        with tempfile.TemporaryDirectory(prefix='slice-publication-test-',
                                         dir=ROOT / 'artifacts') as path:
            parent = Path(path) / 'out'
            for label, slice_pin, postcheck_pin in (
                    ('slice', {**SLICE_RESULT_PIN, 'sha256': '0' * 64}, POSTCHECK_PIN),
                    ('postcheck', SLICE_RESULT_PIN,
                     {**POSTCHECK_PIN, 'sha256': '0' * 64})):
                with self.subTest(label=label), patch.object(
                        publication, '_role', side_effect=AssertionError('role launched')):
                    with self.assertRaises(ValueError):
                        self._run(parent, 'trial-rejected-' + label,
                                  slice_pin=slice_pin, postcheck_pin=postcheck_pin)
                self.assertFalse(parent.exists())

    def test_changed_saved_slice_bytes_reject_before_new_root_or_role(self):
        with tempfile.TemporaryDirectory(prefix='slice-publication-test-',
                                         dir=ROOT / 'artifacts') as path:
            temporary = Path(path)
            source_parent = temporary / 'source'
            copied = source_parent / 'trial-modified'
            copied.mkdir(parents=True)
            for name in ('result.json', 'slices.json', 'audit.json'):
                shutil.copyfile(SLICE_ROOT / name, copied / name)
            (copied / 'slices.json').write_bytes(b'{}')
            parent = temporary / 'out'
            with (patch.object(publication.slice_bridge, 'OUTPUT_PARENT', source_parent),
                  patch.object(publication, '_role', side_effect=AssertionError('role launched'))):
                with self.assertRaises(ValueError):
                    self._run(parent, 'trial-rejected-changed-slices', slice_root=copied)
            self.assertFalse(parent.exists())

    def test_changed_saved_postcheck_bytes_reject_before_new_root_or_role(self):
        with tempfile.TemporaryDirectory(prefix='slice-publication-test-',
                                         dir=ROOT / 'artifacts') as path:
            temporary = Path(path)
            copied = temporary / 'postcheck'
            copied.mkdir()
            for name in ('postcheck-result.json', 'postcheck.py'):
                shutil.copyfile(POSTCHECK_ROOT / name, copied / name)
            (copied / 'postcheck-result.json').write_bytes(b'{}')
            parent = temporary / 'out'
            with (patch.object(publication, 'POSTCHECK_ROOT', copied),
                  patch.object(publication, '_role', side_effect=AssertionError('role launched'))):
                with self.assertRaises(ValueError):
                    self._run(parent, 'trial-rejected-changed-postcheck',
                              postcheck_root=copied)
            self.assertFalse(parent.exists())


if __name__ == '__main__':
    unittest.main()
