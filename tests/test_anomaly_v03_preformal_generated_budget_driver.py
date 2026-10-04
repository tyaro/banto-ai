"""Failure and closure checks for the invented generated two-role budget CLI."""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io as streams
from pathlib import Path
import secrets
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_generated_chain_budget as chain_budget
from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated
from banto_ai import anomaly_v03_preformal_owned_saved_attempt as copied
from banto_ai import _anomaly_v03_engineering_runtime as resources


TOOL = Path(__file__).resolve().parents[1] / 'tools/preformal_owned_generated_trial.py'
SPEC = importlib.util.spec_from_file_location('preformal_generated_budget_driver', TOOL)
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


class FakeBudget:
    def __init__(self, root, *, passed=True, stop_phase=None, byte_cap=192 * 1024**2):
        self.root = root
        self.passed = passed
        self.stop_phase = stop_phase
        self.limits = {'directory_bytes': byte_cap,
                       'minimum_free_disk_bytes': 5 * 1024**3}
        self.roles = {}
        self.phases = []
        self.closed = False

    def start(self):
        return self

    def checkpoint(self, phase):
        self.phases.append(phase)
        if phase == self.stop_phase:
            raise resources.ResourceStop('pipeline_wall_limit')

    def record_role(self, role, pid, pin, *, exit_confirmed=True):
        self.roles[role] = {
            'status': 'complete', 'worker_exit_confirmed': exit_confirmed,
            'worker_pid': pid, 'result_pin': pin,
        }

    def close(self):
        self.closed = True
        return {
            'format': chain_budget.FORMAT,
            'scope': 'invented-generated-attempt-to-separate-reader-only',
            'root': str(self.root), 'samples': 2,
            'sampler_exit_confirmed': True,
            'stop_reason': None if self.passed else 'pipeline_wall_limit',
            'passed': self.passed,
            'caller_reported_roles': dict(self.roles),
            'both_owned_exits_reported':
                set(self.roles) == {'generator', 'reader'} and all(
                    row['worker_exit_confirmed'] for row in self.roles.values()),
            'formal_permission': False,
            'actual_registered_observations_read': False,
            'campaign_evaluations_credited': 0,
        }


class GeneratedBudgetDriverTests(unittest.TestCase):
    def setUp(self):
        self.suffix = 'n' + secrets.token_hex(4)
        self.root = generated.ROOT / 'artifacts' / (
            generated.fixture.PREFIX + self.suffix)
        self.external = generated.ROOT / 'artifacts' / (
            'anomaly-v03-preformal-generated-pinsets-' + self.suffix)
        self.external.mkdir()
        self.manifest_path = self.external / 'pins.json'
        self.raw_manifest = b'{"invented":true}\n'
        self.manifest_path.write_bytes(self.raw_manifest)
        self.digest = hashlib.sha256(self.raw_manifest).hexdigest()
        (self.external / 'pins.json.sha256').write_bytes(
            (self.digest + '\n').encode('ascii'))
        self.revision = 'a' * 40
        self.manifest = {'source': {'revision': self.revision},
                         'output_file_count': 22, 'output_bytes': 131_144_119,
                         'chunk_index': 0}

    def tearDown(self):
        for path in (self.root, self.external):
            if path.exists():
                resolved = path.resolve(strict=True)
                self.assertEqual(resolved.parent, generated.ROOT / 'artifacts')
                self.assertTrue(resolved.name.startswith(
                    generated.fixture.PREFIX if path == self.root else
                    'anomaly-v03-preformal-generated-pinsets-'))
                shutil.rmtree(resolved)

    def test_manifest_pinset_suffix_must_match_generated_attempt(self):
        self.assertEqual(driver._manifest_path(
            str(self.manifest_path), self.root, missing=False),
            self.manifest_path)
        other = self.root.with_name(self.root.name + 'x')
        with self.assertRaises(ValueError):
            driver._manifest_path(str(self.manifest_path), other, missing=False)

    def fake_inner(self, root, *, expected_pins, source_snapshots,
                   expected_revision, chunk_index, recipe_id, outer_budget):
        self.assertIs(outer_budget, self.budget)
        role_stdout = {}
        for role, pid in (('generator', 4101), ('reader', 4102)):
            control = root / ('owned-' + role)
            control.mkdir()
            worker = control / 'worker'
            worker.mkdir()
            stdout = v.canonical_json({'role': role, 'pid': pid})
            (worker / 'report.json').write_bytes(stdout)
            stdout_pin = copied._pin(stdout)
            supervision = v.canonical_json({
                'status': 'complete', 'exit_code': 0,
                'worker_exit_confirmed': True, 'worker_pid': pid,
                'output': stdout_pin,
            })
            (control / 'supervision.json').write_bytes(supervision)
            self.budget.record_role(role, pid, copied._pin(supervision))
            role_stdout[role] = stdout_pin
        result = {
            'status': 'verified', 'reason': None,
            'owned_fixture_generator_pid': 4101,
            'owned_fixture_generator_exit_confirmed': True,
            'owned_fixture_generator_start_token': 'generator-start',
            'owned_fixture_reader_pid': 4102,
            'owned_fixture_reader_exit_confirmed': True,
            'owned_fixture_reader_start_token': 'reader-start',
            'generator_stdout_pin': role_stdout['generator'],
            'reader_stdout_pin': role_stdout['reader'],
            'formal_permission': False,
        }
        target = root / 'owned-generator'
        raw = v.canonical_json(result)
        (target / 'result.json').write_bytes(raw)
        return {**result, 'check_directory': str(target),
                'result_pin': copied._pin(raw)}

    def invoke(self, budget, *, inner=None):
        self.budget = budget
        fake_inputs = (self.root, self.manifest_path, self.manifest,
                       self.revision, {}, {self.revision: {}})
        with patch.object(driver, '_verified_run_inputs',
                          return_value=fake_inputs), \
             patch.object(chain_budget, 'GeneratedChainBudget',
                          return_value=budget), \
             patch.object(driver.shutil, 'disk_usage',
                          return_value=SimpleNamespace(free=20 * 1024**3)), \
             patch.object(generated, '_source',
                          return_value=self.manifest['source']), \
             patch.object(generated, 'generate_and_read',
                          side_effect=inner or self.fake_inner), \
             redirect_stdout(streams.StringIO()):
            return driver.run_budget('unused', 'unused', self.digest)

    def test_verified_requires_budget_and_two_reported_exits(self):
        budget = FakeBudget(self.root)
        self.assertEqual(self.invoke(budget), 0)
        self.assertTrue(budget.closed)
        result = v.strict_json((self.root / 'budgeted-result.json').read_bytes())
        receipt = (self.root / 'resource-budget.json').read_bytes()
        self.assertEqual(result['status'], 'verified')
        self.assertTrue(result['both_owned_exits_reported'])
        self.assertEqual(result['resource_budget_pin'], copied._pin(receipt))
        self.assertFalse(result['prelaunch_pin_preparation_included'])
        self.assertFalse(result['full_end_to_end_budget_measured'])
        self.assertFalse(result['formal_permission'])

    def test_late_budget_stop_overrides_verified_inner_result(self):
        budget = FakeBudget(self.root, passed=False)
        self.assertEqual(self.invoke(budget), 2)
        result = v.strict_json((self.root / 'budgeted-result.json').read_bytes())
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'pipeline_wall_limit')
        self.assertTrue(result['inner_verified'])
        self.assertFalse(result['shared_budget_passed'])
        self.assertTrue((self.root / 'owned-generator/result.json').exists())

    def test_preflight_stop_retains_budget_receipts_without_child(self):
        budget = FakeBudget(self.root, stop_phase='preflight')
        def unexpected(*args, **kwargs):
            self.fail('child launched after preflight stop')
        self.assertEqual(self.invoke(budget, inner=unexpected), 2)
        result = v.strict_json((self.root / 'budgeted-result.json').read_bytes())
        self.assertEqual(result['reason'], 'pipeline_wall_limit')
        self.assertTrue((self.root / 'resource-budget.json').exists())
        self.assertFalse((self.root / 'owned-generator').exists())

    def test_insufficient_outer_byte_cap_rejects_before_child(self):
        budget = FakeBudget(self.root, byte_cap=130 * 1024**2)
        def unexpected(*args, **kwargs):
            self.fail('child launched after capacity rejection')
        self.assertEqual(self.invoke(budget, inner=unexpected), 2)
        result = v.strict_json((self.root / 'budgeted-result.json').read_bytes())
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_type'], 'V03ValidationError')
        self.assertTrue(budget.closed)

    def test_missing_reader_role_cannot_verify_outer_result(self):
        budget = FakeBudget(self.root)
        def incomplete(*args, **kwargs):
            result = self.fake_inner(*args, **kwargs)
            budget.roles.pop('reader')
            return result
        self.assertEqual(self.invoke(budget, inner=incomplete), 2)
        result = v.strict_json((self.root / 'budgeted-result.json').read_bytes())
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['both_owned_exits_reported'])
        self.assertEqual(result['reason'], 'owned_exits_not_both_reported')

    def test_saved_supervision_change_cannot_verify_outer_result(self):
        budget = FakeBudget(self.root)

        def changed(*args, **kwargs):
            result = self.fake_inner(*args, **kwargs)
            (self.root / 'owned-reader/supervision.json').write_bytes(b'{}\n')
            return result

        self.assertEqual(self.invoke(budget, inner=changed), 2)
        result = v.strict_json((self.root / 'budgeted-result.json').read_bytes())
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'saved_role_evidence_changed')
        self.assertFalse(result['saved_role_evidence_bound'])
        self.assertTrue(result['shared_budget_passed'])

    def test_critical_owned_failure_is_raised_after_receipt(self):
        budget = FakeBudget(self.root)
        owner = generated.supervisor.UnreapedWorker(object(),
                                                      {'worker_started': True})
        def fail(*args, **kwargs):
            raise owner
        with self.assertRaises(generated.supervisor.UnreapedWorker) as caught:
            self.invoke(budget, inner=fail)
        self.assertIs(caught.exception, owner)
        self.assertTrue(budget.closed)
        self.assertTrue((self.root / 'resource-budget.json').exists())
        result = v.strict_json((self.root / 'budgeted-result.json').read_bytes())
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_type'], 'UnreapedWorker')


if __name__ == '__main__':
    unittest.main()
