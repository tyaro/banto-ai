"""Invented 480-slot metadata only; no observation or owned process work."""
from __future__ import annotations

import copy
from pathlib import Path, PurePosixPath
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_materializer as materializer
from banto_ai import anomaly_v03_preformal_campaign_metadata as p


def _runtime():
    value = {
        'architecture': 'AMD64', 'compiler': 'test', 'filesystem': 'local-NTFS',
        'gil_disabled': False, 'implementation': 'CPython',
        'os': 'Windows 11 Pro', 'os_build': 26300, 'os_major': 10,
        'os_minor': 0, 'os_ubr': 9457, 'pointer_bits': 64,
        'python_dll_raw_sha256': 'd' * 64,
        'python_exe_raw_sha256': 'e' * 64,
        'python_version': '3.14.0', 'release': '26H2', 'source_tag': 'test',
    }
    return {'candidate_id': 'win26h2-v1', 'tuple': value,
            'tuple_sha256': v.canonical_sha256(value), 'status': 'not_adopted'}


def _plan(root=None):
    campaign_id = 'a' * 64
    if root is None:
        root = (str(Path(__file__).resolve().parents[1] / 'artifacts' /
                    'anomaly-v03-preformal-campaign-aaaaaaaa')
                if p.PureWindowsPath is PurePosixPath else
                r'D:\develop\banto-ai\artifacts\anomaly-v03-preformal-campaign-aaaaaaaa')
    return p.fixed_plan(
        campaign_id,
        root,
        'h', {'bytes': p.FROZEN_REGISTRY_BYTES,
              'sha256': v.REGISTRY_RAW_SHA256},
        {'revision': 'b' * 40,
         'selected_files': [{'path': 'src/banto_ai/anomaly_v03.py',
                             'pin': {'bytes': 1000, 'sha256': 'c' * 64}}],
         'scope': 'selected-working-git-raw-only-not-source-closure'},
        _runtime(),
        {'scope': 'invented-480-chunk-campaign-candidate',
         'status': 'not_adopted',
         'enforcement': 'sampled-and-cooperative-not-hard-quota',
         'limits': {'wall_seconds': 100000, 'parent_private_bytes': 1024**3,
                    'directory_bytes': 100000000000,
                    'directory_entries': 100000, 'directory_depth': 12,
                    'minimum_free_disk_bytes': 1,
                    'minimum_free_ram_bytes': 1,
                    'minimum_commit_headroom_bytes': 1}})


class Journal:
    def __init__(self, root=None):
        self.plan = _plan(root)
        self.plan_raw = p.encode_plan(self.plan)
        self.plan_pin = p.pin(self.plan_raw)
        self.raws = []

    @property
    def head(self):
        return p.pin(self.raws[-1])['sha256'] if self.raws else self.plan_pin['sha256']

    def add(self, index, attempt, state, *, reason=None, mutate=None,
            fresh_reread=True):
        evidence = None
        outputs = None
        if state == 'completed':
            evidence = {name: p.pin(name.encode())
                        for name in p.REQUIRED_EVIDENCE_NAMES}
            evidence.update({name: None for name in p.FRESH_REREAD_EVIDENCE_NAMES})
            if fresh_reread:
                evidence.update({name: p.pin(name.encode())
                                 for name in p.FRESH_REREAD_EVIDENCE_NAMES})
                evidence['fresh_reread_rows'] = evidence['rows']
            outputs = {name: p.pin(name.encode()) for name in p._output_names(index)}
            outputs['saved/registry.json'] = self.plan['registry_pin']
            for label, name in (
                ('saved_receipt', 'saved/receipt.json'),
                ('saved_report', 'saved/report.json'),
                ('saved_savepoint', 'saved/savepoint.json'),
                ('saved_registry', 'saved/registry.json'),
            ):
                evidence[label] = outputs[name]
        record = p.make_record(
            self.plan_pin, self.head, len(self.raws) + 1, index, attempt,
            state, p.attempt_root(self.plan, index, attempt), p.pin(b'manifest'),
            source_revision=self.plan['source']['revision'],
            runtime_tuple_sha256=self.plan['runtime_candidate']['tuple_sha256'],
            evidence_pins=evidence, saved_output_pins=outputs, reason=reason)
        if mutate is not None:
            mutate(record)
        self.raws.append(p.encode_record(record))

    def complete(self, index, attempt=1):
        self.add(index, attempt, 'started')
        self.add(index, attempt, 'completed')

    def reduce(self, **overrides):
        args = {'expected_plan_pin': self.plan_pin,
                'expected_record_count': len(self.raws),
                'expected_head_sha256': self.head}
        args.update(overrides)
        return p.reduce_journal(self.plan_raw, self.raws, **args)


class PlanTests(unittest.TestCase):
    def test_frozen_identity_plan_and_short_sibling_attempt_paths(self):
        with patch.object(materializer, 'normal_stream',
                          side_effect=AssertionError('no observations')):
            plan = _plan()
            p.validate_plan(plan)
        self.assertEqual(len(plan['chunks']), 480)
        self.assertEqual(plan['identity_plan_sha256'],
                         '8cbda70c8749bebb2bab92f3113870093027589bc73b5e4676cb74fbca39e921')
        self.assertEqual(plan['chunk_identity_hashes_sha256'],
                         '50308531170c26fb4ecf6782afee3f76d0f4c26c5805677d724a7b769b460448')
        self.assertEqual(plan['chunks_sha256'],
                         v.canonical_sha256(plan['chunks']))
        self.assertEqual(plan['chunks'][0]['registered_seed_index'], 0)
        self.assertEqual(plan['chunks'][479]['registered_seed_index'], 39)
        self.assertTrue(p.attempt_root(plan, 0, 1).endswith('-h001'))
        self.assertTrue(p.attempt_root(plan, 1, 1).endswith('-h011'))
        self.assertTrue(p.attempt_root(plan, 479, 1).endswith('-hdb1'))
        self.assertTrue(p.attempt_root(plan, 0, 2).endswith('-h002'))
        self.assertFalse(plan['registered_seed_consumed'])
        self.assertFalse(plan['formal_permission'])
        self.assertFalse(plan['launch_authorized'])
        self.assertFalse(plan['resume_authorized'])

    def test_plan_rehash_cannot_change_frozen_identity_or_scope(self):
        original = _plan()
        for mutate in (
            lambda x: x['chunks'].reverse(),
            lambda x: x['chunks'][0].update(layout=9),
            lambda x: x.update(identity_plan_sha256='f' * 64),
            lambda x: x.update(campaign_completed=True),
            lambda x: x['source']['selected_files'].clear(),
            lambda x: x['registry_pin'].update(bytes=10678),
            lambda x: x['runtime_candidate']['tuple'].update(os_ubr=9458),
            lambda x: x['budget_candidate'].update(status='adopted'),
            lambda x: x.update(path_code='H'),
        ):
            plan = copy.deepcopy(original)
            mutate(plan)
            plan['chunks_sha256'] = v.canonical_sha256(plan['chunks'])
            with self.assertRaises(ValueError):
                p.validate_plan(plan)

    def test_selected_source_files_are_stored_in_canonical_path_order(self):
        base = _plan()
        source = copy.deepcopy(base['source'])
        source['selected_files'].insert(0, {
            'path': 'src/banto_ai/zzz.py',
            'pin': {'bytes': 20, 'sha256': 'f' * 64}})
        source['selected_files'].reverse()
        plan = p.fixed_plan(base['campaign_id'], base['root'], base['path_code'],
                            base['registry_pin'], source,
                            base['runtime_candidate'], base['budget_candidate'])
        self.assertEqual([row['path'] for row in plan['source']['selected_files']],
                         sorted(row['path'] for row in source['selected_files']))
        p.validate_plan(plan)
        plan['source']['selected_files'].reverse()
        with self.assertRaises(ValueError):
            p.validate_plan(plan)


class ReducerTests(unittest.TestCase):
    def setUp(self):
        self.j = Journal()

    def test_empty_journal_is_only_prelaunch_metadata(self):
        result = self.j.reduce()
        self.assertEqual(result['record_count'], 0)
        self.assertEqual(result['declared_completed_chunks'], 0)
        self.assertEqual(len(result['missing_chunk_indices']), 480)
        self.assertIsNone(result['producer_campaign_anchor'])
        self.assertFalse(result['campaign_coherence_authenticated'])

    def test_two_ordered_chunks_remain_partial_and_untrusted(self):
        self.j.complete(0)
        self.j.complete(1)
        result = self.j.reduce()
        self.assertEqual(result['declared_completed_chunks'], 2)
        self.assertEqual(result['declared_completed_evaluations'], 12)
        self.assertEqual(result['completed_chunk_indices'], [0, 1])
        self.assertEqual(result['missing_chunk_indices'], list(range(2, 480)))
        self.assertIsNone(result['clusters'])
        self.assertFalse(result['producer_execution_authenticated'])
        self.assertEqual(result['campaign_evaluations_credited'], 0)
        self.assertFalse(result['formal_permission'])
        self.assertFalse(result['launch_authorized'])
        self.assertFalse(result['resume_authorized'])

    def test_completed_requires_distinct_fresh_reread_evidence(self):
        self.j.add(0, 1, 'started')
        self.j.add(0, 1, 'completed', fresh_reread=True)
        self.assertEqual(self.j.reduce()['declared_completed_chunks'], 1)
        incomplete = Journal()
        incomplete.add(0, 1, 'started')
        incomplete.add(0, 1, 'completed', fresh_reread=False)
        with self.assertRaises(ValueError):
            incomplete.reduce()

    def test_saved_logical_names_match_retained_g02_manifest_inventory(self):
        # This digest was taken from the 22 logical output_pins keys in the
        # retained g02 prelaunch manifest, never from generated._outputs().
        self.assertEqual(v.canonical_sha256(sorted(p._output_names(0))),
                         '067ea960fd965f2628aa28217f70ca94fbbde4521e53b8aca2c849a5773db6f6')

    def test_failure_retained_retry_sequential_and_integrity_terminal(self):
        self.j.add(0, 1, 'started')
        self.j.add(0, 1, 'failed', reason='worker_exit')
        self.assertEqual(self.j.reduce()['latest_unfinished_state'], 'failed')
        self.assertFalse(self.j.reduce()['resume_authorized'])
        self.j.complete(0, attempt=2)
        self.j.complete(1)
        self.assertEqual(self.j.reduce()['failed_attempt_count'], 1)

        bad = Journal()
        bad.add(0, 1, 'started')
        bad.add(0, 1, 'failed', reason='integrity')
        bad.add(0, 2, 'started')
        with self.assertRaises(ValueError):
            bad.reduce()

    def test_failed_or_unfinished_latest_cannot_skip_to_next_chunk(self):
        for failure in (False, True):
            trial = Journal()
            trial.add(0, 1, 'started')
            if failure:
                trial.add(0, 1, 'failed', reason='worker_exit')
            trial.add(1, 1, 'started')
            with self.assertRaises(ValueError):
                trial.reduce()

    def test_external_raw_head_count_and_canonical_lf_are_required(self):
        self.j.complete(0)
        original = list(self.j.raws)
        for overrides in (
            {'expected_plan_pin': {'bytes': self.j.plan_pin['bytes'],
                                   'sha256': 'f' * 64}},
            {'expected_record_count': 1},
            {'expected_record_count': True},
            {'expected_head_sha256': 'f' * 64},
        ):
            with self.assertRaises(ValueError):
                self.j.reduce(**overrides)
        for raws in (original[:-1], list(reversed(original)),
                     [original[0], original[0]],
                     [original[0].rstrip(b'\n'), original[1]]):
            self.j.raws = raws
            with self.assertRaises(ValueError):
                self.j.reduce(expected_record_count=2,
                              expected_head_sha256=p.pin(original[-1])['sha256'])
        with self.assertRaises(ValueError):
            p.reduce_journal(self.j.plan_raw.rstrip(b'\n'), [],
                             expected_plan_pin=p.pin(self.j.plan_raw.rstrip(b'\n')),
                             expected_record_count=0,
                             expected_head_sha256=p.pin(self.j.plan_raw.rstrip(b'\n'))['sha256'])

    def test_anchor_root_context_and_completed_evidence_must_match(self):
        for mutate in (
            lambda x: x['anchor_pin'].update(sha256='f' * 64),
            lambda x: x.update(attempt_root=x['attempt_root'][:-1] + '2'),
            lambda x: x.update(source_revision='f' * 40),
            lambda x: x.update(runtime_tuple_sha256='f' * 64),
            lambda x: x['evidence_pins'].update(rows=None),
            lambda x: x['saved_output_pins'].pop('saved/report.json'),
        ):
            trial = Journal()
            trial.add(0, 1, 'started')
            trial.add(0, 1, 'completed', mutate=mutate)
            with self.assertRaises(ValueError):
                trial.reduce()

    def test_attempt_numbers_and_chunk_order_are_exact(self):
        for index, attempt in ((1, 1), (0, 2)):
            trial = Journal()
            trial.add(index, attempt, 'started')
            with self.assertRaises(ValueError):
                trial.reduce()
        trial = Journal()
        trial.complete(0)
        trial.add(0, 2, 'started')
        with self.assertRaises(ValueError):
            trial.reduce()


if __name__ == '__main__':
    unittest.main()
