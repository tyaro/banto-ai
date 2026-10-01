"""Invented bytes/process observations only; no collector or registered data."""
import copy
import hashlib
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_consumer_evidence as evidence


def pin(raw):return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def case(role='reader', mode='fixture'):
    sources = {'src/banto_ai/entry.py': b'# invented entry\n', 'src/banto_ai/helper.py': b'# invented helper\n'}
    source = {'revision': 'a'*40, 'sources': [{'path': n, 'raw_sha256': pin(raw)['sha256'],
              'byte_count': len(raw)} for n, raw in sorted(sources.items())]}
    binaries = {'python/executable': b'invented exe', 'python/shared-library': b'invented dll',
                'stdlib/json': b'invented stdlib', 'native/kernel': b'invented native', 'tool/git': b'invented git'}
    paths = {'python/executable': ('C:/Python314/python.exe', 'python'),
             'python/shared-library': ('C:/Python314/python314.dll', 'python'),
             'stdlib/json': ('C:/Python314/Lib/json/__init__.py', 'stdlib'),
             'native/kernel': ('C:/Windows/System32/kernel32.dll', 'native'),
             'tool/git': ('C:/Tools/Git/git.exe', 'tool')}
    runtime = {'platform': {'system': 'Windows', 'release': '25H2', 'build': 26200,
                           'ubr': 9457, 'architecture': 'AMD64', 'cpu_identity': 'invented CPU'},
        'python': {'implementation': 'CPython', 'version': '3.14.0', 'pointer_bits': 64, 'gil_disabled': False},
        'startup': {'flags': dict(evidence.FLAGS), 'sys_path': ['C:/invented/src', 'C:/Python314/Lib'],
                    'site_imported': False, 'hooks': []},
        'files': {n: {'physical_path': paths[n][0], 'category': paths[n][1], 'pin': pin(raw)} for n, raw in binaries.items()}}
    inputs = {'saved/input.json': b'{"invented":true}\n'}
    outputs = {'result/report.json': b'{"result":"invented"}\n'}
    expected = {'invocation_id': 'b'*64, 'source': source, 'runtime': runtime,
        'process': {'pid': 220, 'parent_pid': 110, 'start_token': 'c'*64,
                    'argv': ['C:/Python314/python.exe', '-I', '-S', '-B', '-m', 'banto_ai.entry'], 'cwd': 'C:/invented'},
        'inputs': {n: pin(raw) for n, raw in inputs.items()}, 'outputs': {n: pin(raw) for n, raw in outputs.items()}}
    value = {'format': evidence.FORMAT, 'mode': mode, 'role': role,
        **{n: copy.deepcopy(expected[n]) for n in ('invocation_id', 'process', 'inputs', 'outputs')},
        **{kind+'_'+phase: copy.deepcopy(expected[kind]) for kind in ('source', 'runtime') for phase in ('before', 'after')},
        'completion': {'status': 'completed', 'exit_code': 0, 'worker_exit_confirmed': True, 'observation_errors': []}}
    return {'expected': expected, 'evidence': value, 'expected_mode': mode, 'expected_role': role,
            'source_snapshots': {source['revision']: sources}, 'runtime_snapshots': binaries,
            'input_snapshots': inputs, 'output_snapshots': outputs}


def invoke(sample, **overrides):
    raw = evidence.v.canonical_json(sample['evidence'])
    kwargs = {n: value for n, value in sample.items() if n != 'evidence'}
    return evidence.validate_execution_evidence(raw, **({'expected_pin': pin(raw), **kwargs} | overrides))


def set_at(value, path, replacement):
    for name in path[:-1]:value = value[name]
    value[path[-1]] = replacement


class ConsumerEvidenceTests(unittest.TestCase):
    def test_four_roles_bind_all_supplied_bytes_without_promoting(self):
        for role in evidence.ROLES:
            for mode in evidence.MODES:
                with self.subTest(role=role, mode=mode):
                    sample = case(role, mode);before = copy.deepcopy(sample);result = invoke(sample)
                    self.assertEqual(result['status'], 'supplied_consumer_evidence_bound')
                    self.assertEqual(result['source_descriptor'], sample['expected']['source'])
                    self.assertEqual(result['output_pins'], sample['expected']['outputs'])
                    self.assertEqual(result['source_files'], 2);self.assertEqual(result['runtime_files'], 5)
                    for name, value in evidence.CLOSED.items():self.assertEqual(result[name], value)
                    self.assertEqual(sample, before)
                    result['source_descriptor']['sources'].clear();result['output_pins'].clear()
                    self.assertEqual(sample, before)

    def test_wrong_role_scope_invocation_or_revision_even_with_resealed_evidence(self):
        changes = [(('role',), 'audit'), (('mode',), 'engineering-dev-smoke'),
            (('format',), 's4-a.2'), (('invocation_id',), 'd'*64),
            (('source_before', 'revision'), 'd'*40), (('source_after', 'revision'), 'd'*40),
            (('source_after', 'sources'), [])]
        for path, replacement in changes:
            with self.subTest(path=path):
                sample = case();set_at(sample['evidence'], path, replacement)
                with self.assertRaises(ValueError):invoke(sample)

    def test_raw_evidence_requires_retained_hash_not_self_consistency(self):
        sample = case();old = pin(evidence.v.canonical_json(sample['evidence']))
        sample['evidence']['role'] = 'audit'
        with self.assertRaisesRegex(ValueError, 'external evidence pin'):invoke(sample, expected_pin=old)
        for wrong in (None, {'bytes': True, 'sha256': 'a'*64}, {'bytes': 1, 'sha256': 'X'*64}):
            with self.subTest(pin=wrong),self.assertRaises(ValueError):invoke(case(), expected_pin=wrong)

    def test_process_pid_reuse_command_cwd_and_parent_are_bound(self):
        for key, value in [('pid', 221), ('parent_pid', 111), ('start_token', 'e'*64),
                           ('cwd', 'C:/elsewhere'), ('argv', ['C:/other.exe', '-I', '-S', '-B', '-m', 'entry'])]:
            with self.subTest(key=key):
                sample = case();sample['evidence']['process'][key] = value
                with self.assertRaisesRegex(ValueError, 'process binding'):invoke(sample)

    def test_completion_failures_unreaped_worker_and_observation_errors_rejected(self):
        for key, value in [('status', 'pass'), ('exit_code', 2), ('exit_code', False),
                           ('worker_exit_confirmed', False), ('worker_exit_confirmed', 1),
                           ('observation_errors', ['missing final snapshot'])]:
            with self.subTest(key=key, value=value):
                sample = case();sample['evidence']['completion'][key] = value
                with self.assertRaisesRegex(ValueError, 'completion'):invoke(sample)

    def test_runtime_before_and_after_must_match_caller_profile(self):
        changes = [(('platform', 'ubr'), 9458), (('platform', 'cpu_identity'), 'different CPU'),
                   (('python', 'version'), '3.14.7'), (('startup', 'flags', 'no_site'), 0),
                   (('startup', 'sys_path'), ['C:/foreign']), (('files',), {})]
        for phase in ('before', 'after'):
            for path, value in changes:
                with self.subTest(phase=phase, path=path):
                    sample = case();set_at(sample['evidence']['runtime_'+phase], path, value)
                    with self.assertRaisesRegex(ValueError, 'runtime '+phase):invoke(sample)

    def test_windows_update_between_invocations_is_recordable(self):
        sample = case()
        sample['expected']['runtime']['platform']['ubr'] = 9500
        for phase in ('before', 'after'):
            sample['evidence']['runtime_'+phase] = copy.deepcopy(sample['expected']['runtime'])
        self.assertEqual(invoke(sample)['status'], 'supplied_consumer_evidence_bound')

    def test_source_snapshot_revision_inventory_and_bytes_are_external(self):
        for kind in ('revision', 'missing', 'extra', 'mutated', 'text', 'line-endings'):
            with self.subTest(kind=kind):
                sample = case();snapshots = sample['source_snapshots'];files = snapshots['a'*40]
                if kind == 'revision':snapshots['d'*40] = snapshots.pop('a'*40)
                elif kind == 'missing':files.pop('src/banto_ai/helper.py')
                elif kind == 'extra':files['src/banto_ai/extra.py'] = b''
                elif kind == 'mutated':files['src/banto_ai/entry.py'] = b'# changed entry!\n'
                elif kind == 'text':files['src/banto_ai/entry.py'] = files['src/banto_ai/entry.py'].decode()
                else:files['src/banto_ai/entry.py'] = files['src/banto_ai/entry.py'].replace(b'\n', b'\r\n')
                with self.assertRaises(ValueError):invoke(sample)

    def test_runtime_input_and_output_snapshots_cannot_be_substituted(self):
        for group in ('runtime_snapshots', 'input_snapshots', 'output_snapshots'):
            for kind in ('missing', 'extra', 'same-length-change'):
                with self.subTest(group=group, kind=kind):
                    sample = case();files = sample[group];name = next(iter(files))
                    if kind == 'missing':files.pop(name)
                    elif kind == 'extra':files['extra'] = b''
                    else:files[name] = bytes([files[name][0] ^ 1])+files[name][1:]
                    with self.assertRaises(ValueError):invoke(sample)

    def test_resealed_output_or_input_inventory_does_not_redefine_expectation(self):
        for group in ('inputs', 'outputs'):
            sample = case();name = next(iter(sample['evidence'][group]))
            sample['evidence'][group][name] = pin(b'resealed replacement')
            with self.subTest(group=group),self.assertRaisesRegex(ValueError, group+' binding'):invoke(sample)

    def test_self_reported_pass_full_closure_and_extra_fields_are_rejected(self):
        for name in ('formal_permission', 'result_trusted', 'source_closure_complete', 'acceptance_status'):
            sample = case();sample['evidence'][name] = True
            with self.subTest(name=name),self.assertRaisesRegex(ValueError, 'evidence fields'):invoke(sample)
        sample = case();sample['evidence'] = {'acceptance_status': 'pass'}
        with self.assertRaisesRegex(ValueError, 'evidence fields'):invoke(sample)

    def test_invalid_external_expectations_fail_even_if_evidence_repeats_them(self):
        changes = [(('source', 'sources'), []), (('source', 'revision'), 'short'),
            (('process', 'pid'), True), (('process', 'pid'), 110), (('process', 'start_token'), ''),
            (('process', 'argv'), ['C:/Python314/python.exe', '-I', '-B', '-m', 'entry', 'arg']),
            (('runtime', 'startup', 'flags', 'no_site'), 0),
            (('runtime', 'startup', 'flags', 'isolated'), True),
            (('runtime', 'startup', 'site_imported'), True), (('runtime', 'startup', 'hooks'), ['sitecustomize']),
            (('runtime', 'startup', 'sys_path'), ['C:/Python314/Lib/SITE-PACKAGES']),
            (('runtime', 'startup', 'sys_path'), ['C:/Python314/Lib', 'c:\\python314\\lib']),
            (('runtime', 'python', 'version'), '3.12.10'), (('runtime', 'files'), {}),
            (('inputs',), {}), (('outputs',), {})]
        for path, replacement in changes:
            with self.subTest(path=path, value=replacement):
                sample = case();set_at(sample['expected'], path, replacement)
                for kind in ('source', 'runtime'):
                    for phase in ('before', 'after'):sample['evidence'][kind+'_'+phase] = copy.deepcopy(sample['expected'][kind])
                for kind in ('process', 'inputs', 'outputs'):sample['evidence'][kind] = copy.deepcopy(sample['expected'][kind])
                with self.assertRaises(ValueError):invoke(sample)

    def test_unsafe_paths_and_case_alias_inventories_rejected_without_io(self):
        for path in ('relative', '\\\\server\\share', 'C:/x/../y', 'C:/x//y', 'C:/x/a:stream', 'C:/CON'):
            sample = case();sample['expected']['process']['cwd'] = path
            with self.subTest(path=path),self.assertRaises(ValueError):invoke(sample)
        for group in ('inputs', 'outputs'):
            sample = case();name = next(iter(sample['expected'][group]))
            sample['expected'][group][name.upper()] = copy.deepcopy(sample['expected'][group][name])
            with self.subTest(group=group),self.assertRaisesRegex(ValueError, 'case-alias'):invoke(sample)
        sample = case();rows = sample['expected']['source']['sources'];rows.append(copy.deepcopy(rows[-1]))
        with self.assertRaisesRegex(ValueError, 'uniqueness'):invoke(sample)

    def test_strict_json_duplicates_nonfinite_bad_utf8_and_metadata_bound(self):
        sample = case();kwargs = {k: value for k, value in sample.items() if k != 'evidence'}
        for raw in (b'{"role":"reader","role":"audit"}', b'{"x":NaN}', b'\xff'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                evidence.validate_execution_evidence(raw, expected_pin=pin(raw), **kwargs)
        with patch.object(evidence.v, 'strict_json', side_effect=AssertionError('parse')):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                invoke(sample, expected_pin={'bytes': evidence.MAX_EVIDENCE_BYTES+1, 'sha256': 'd'*64})

    def test_formal_and_unknown_role_rejected_before_parsing_or_snapshots(self):
        for args in ({'expected_mode': 'formal'}, {'expected_role': 'producer'}, {'expected_role': []}):
            with self.subTest(args=args),patch.object(evidence.v, 'strict_json', side_effect=AssertionError('parse')):
                with self.assertRaises(ValueError):invoke(case(), **args)

    def test_success_never_reads_paths_or_launches_processes(self):
        sample = case()
        with (patch('builtins.open', side_effect=AssertionError('open')),
              patch.object(Path, 'read_bytes', side_effect=AssertionError('read')),
              patch.object(subprocess, 'run', side_effect=AssertionError('launch'))):
            result = invoke(sample)
        self.assertFalse(result['execution_authenticated'])


if __name__ == '__main__':unittest.main()
