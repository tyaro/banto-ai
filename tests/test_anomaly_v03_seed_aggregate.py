"""Invented count/report fixtures only; no observation or score computation."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_seed_aggregate as audit


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def invented_row(identity):
    def metric(n, d, kind):
        return {'numerator': n, 'denominator': d, 'value': audit.arithmetic.ratio(n, d, kind),
                'ci_status': 'not_evaluated', 'ci_lower': None, 'ci_upper': None, 'null_replicates': 0}
    c0 = identity['candidate_id'] == audit.arithmetic.CANDIDATES[0]
    machine, sensor = (1, 2) if c0 else (8, 9)
    detected, episodes = machine+sensor, (5 if c0 else 18)
    metrics = {kind: metric(n, d, kind) for kind, n, d in (
        ('machine_recall', machine, 10), ('sensor_recall', sensor, 10), ('precision', detected, episodes),
        ('clean_rate', 1, 3365), ('false_alert_burden', episodes-detected, 20))}
    metrics.update({'availability': [{'full_target': t, 'metric': metric(1740, 1800, k)}
        for t, k in zip(audit.arithmetic.TARGETS, audit.arithmetic.AVAILABILITY)],
        'scheduled_clean_seconds': 3365, 'effective_clean_seconds': 3300,
        'effective_clean_rate': audit.arithmetic.ratio(1, 3300, 'clean_rate')})
    return {'identity': identity, 'evaluation_outcome': 'success',
        'profile_and_score_audit': {**audit.QUIET, 'identity': identity, 'status': 'observation_profile_score_checks_passed',
            'profile_derivation_verified': True, 'score_derivation_verified': True, 'evaluation_outcome': 'success',
            'profiles_checked': 48, 'observation_rows': 18000, 'score_rows_checked': 14400,
            'available_score_rows': 13920, 'inconclusive_profiles': []},
        'ledger_audit': {'status': 'ledger_checks_passed', 'score_rows': 14400, 'incidents': 20,
            'independent_s6_complete': False, 'performance_status': 'not_evaluated',
            'equipment_episodes': episodes, 'metrics': metrics}}


class CountTests(unittest.TestCase):
    def setUp(self):
        self.rows = [invented_row(i) for role in ('dev', 'smoke') for i in audit.registry.evaluation_inventory(role)]

    def test_registered_clusters_and_hand_sums_without_inference(self):
        with patch.object(audit.arithmetic, 'draw_index', side_effect=AssertionError('no bootstrap')), \
             patch.object(audit.arithmetic, 'compute_fixture_tables', side_effect=AssertionError('no gates')):
            result = audit.aggregate_evaluations(self.rows)
        self.assertEqual([len(result[k]) for k in ('seed_clusters', 'by_seed', 'by_role', 'paired_descriptive')], [10, 90, 18, 12])
        self.assertEqual([x['seed'] for x in result['seed_clusters']],
                         [s for e in audit.registry.seed_registry()['entries'][:2] for s in e['seeds']])
        core, stress, overall = result['by_seed'][:3]
        self.assertEqual(core['counts']['machine_recall'], [12, 120])
        self.assertEqual(core['counts']['clean_rate'], [12, 40380])
        self.assertEqual(overall['counts']['precision'], [72, 120])
        for kind in audit.arithmetic.METRICS:
            self.assertEqual(overall['counts'][kind], [core['counts'][kind][j]+stress['counts'][kind][j] for j in (0, 1)])
        self.assertEqual({x['role'] for x in result['by_role']}, {'dev', 'smoke'})
        self.assertFalse(result['bootstrap_performed'])
        self.assertIsNone(result['selected_candidate'])
        self.assertTrue(all(t['ci_status'] == 'not_evaluated' for t in result['by_role']))
        # Only these invented clusters exercise the hand-fixture shape checker.
        audit.arithmetic._fixture_clusters([{'cluster_id': str(i), 'candidates': c['candidates']}
                                            for i, c in enumerate(result['seed_clusters'])])

    def test_ratio_of_sums_not_mean_of_ratios(self):
        metrics = self.rows[0]['ledger_audit']['metrics']
        metrics['precision'].update(denominator=25, value=3/25)
        metrics['false_alert_burden'].update(numerator=22, value=110.)
        self.rows[0]['ledger_audit']['equipment_episodes'] = 25
        result = audit.aggregate_evaluations(self.rows)['by_seed'][0]
        self.assertEqual(result['counts']['precision'], [36, 80])
        self.assertEqual(result['points']['precision'], .45)
        self.assertNotEqual(result['points']['precision'], (3/25+11*3/5)/12)

    def test_missing_duplicate_reordered_wrong_identity_rejected(self):
        for change in ('missing', 'duplicate', 'reorder', 'holdout', 'bool_layout'):
            rows = copy.deepcopy(self.rows)
            if change == 'missing': rows.pop()
            elif change == 'duplicate': rows[1] = rows[0]
            elif change == 'reorder': rows[0], rows[1] = rows[1], rows[0]
            elif change == 'holdout': rows[0]['identity']['role'] = 'holdout'
            else: rows[0]['identity']['layout'] = False
            with self.subTest(change=change), self.assertRaises(ValueError): audit.aggregate_evaluations(rows)

    def test_corrupt_counts_exposure_target_point_and_flags_rejected(self):
        mutations = [
            lambda r: r['ledger_audit']['metrics']['machine_recall'].update(numerator=True),
            lambda r: r['ledger_audit']['metrics']['machine_recall'].update(denominator=11, value=1/11),
            lambda r: r['ledger_audit']['metrics']['availability'].pop(),
            lambda r: r['ledger_audit']['metrics']['precision'].update(value=.61),
            lambda r: r['ledger_audit']['metrics']['clean_rate'].update(numerator=3, value=86400/3365),
            lambda r: r['ledger_audit']['metrics'].update(effective_clean_seconds=3366),
            lambda r: r['profile_and_score_audit'].update(available_score_rows=13919),
            lambda r: r['profile_and_score_audit'].update(profile_derivation_verified=1),
            lambda r: r['ledger_audit']['metrics']['precision'].update(ci_status='computed'),
            lambda r: r['profile_and_score_audit'].update(evaluation_outcome='failed'),
        ]
        for index, mutate in enumerate(mutations):
            rows = copy.deepcopy(self.rows); mutate(rows[0])
            with self.subTest(index=index), self.assertRaises(ValueError): audit.aggregate_evaluations(rows)

    def test_inconclusive_profile_retained_and_paired_status_propagated(self):
        row = self.rows[0]
        diagnostic = {'profile_id': row['identity']['evaluation_id']+'-profile-motor-01-motor_current-stopped', 'reason': 'zero_scale'}
        row['evaluation_outcome'] = 'inconclusive'
        row['profile_and_score_audit'].update(evaluation_outcome='inconclusive', inconclusive_profiles=[diagnostic])
        result = audit.aggregate_evaluations(self.rows)
        self.assertEqual(result['by_seed'][0]['profile_diagnostics'][0]['profiles'], [diagnostic])
        self.assertEqual(result['by_seed'][0]['counts']['machine_recall'], [12, 120])
        self.assertEqual(result['paired_descriptive'][0]['profile_status'], 'inconclusive')
        row['evaluation_outcome'] = 'success'
        with self.assertRaises(ValueError): audit.aggregate_evaluations(self.rows)

    def test_zero_alerts_keep_null_precision(self):
        for row in self.rows:
            if row['identity']['candidate_id'] != audit.arithmetic.CANDIDATES[0]: continue
            row['ledger_audit']['equipment_episodes'] = 0
            for kind in audit.arithmetic.METRICS[:5]:
                metric = row['ledger_audit']['metrics'][kind]
                metric.update(numerator=0, value=0.)
                if kind == 'precision': metric.update(denominator=0, value=None)
            row['ledger_audit']['metrics']['effective_clean_rate'] = 0.
        result = audit.aggregate_evaluations(self.rows)
        self.assertIsNone(result['by_seed'][0]['points']['precision'])
        self.assertEqual(result['by_seed'][0]['counts']['precision'], [0, 0])

    def test_unknown_or_duplicate_profile_diagnostic_rejected(self):
        row = self.rows[0]
        row['evaluation_outcome'] = 'inconclusive'
        profile = row['profile_and_score_audit']
        profile['evaluation_outcome'] = 'inconclusive'
        item = {'profile_id': row['identity']['evaluation_id']+'-profile-motor-01-motor_current-stopped', 'reason': 'nonfinite'}
        profile['inconclusive_profiles'] = [item, item]
        with self.assertRaises(ValueError): audit.aggregate_evaluations(self.rows)
        profile['inconclusive_profiles'] = [{**item, 'profile_id': 'unknown'}]
        with self.assertRaises(ValueError): audit.aggregate_evaluations(self.rows)


class AuthenticatedTests(unittest.TestCase):
    """A small retained-report tree; raw dataset/evaluation files do not exist."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root/'run-root'; self.run.mkdir()
        self.roots = {k: self.root/k/'savepoint-evidence.json' for k in ('inference', 'generation', 'score', 'connected', 'completed')}
        for path in self.roots.values(): path.parent.mkdir()
        self.plan = audit.checkpoints.fixed_plan('a'*40, 'b'*40)
        self.pins = {'run/metadata/plan.json': self.write(self.run/'run/metadata/plan.json', self.plan)}
        self.gens, self.olds, chunks = [], [], []
        for index, planned in enumerate(self.plan['chunks']):
            attempt = 2 if index == 119 else 1
            stem = f'run/attempts/chunks/{index:03d}/attempt-{attempt:04d}'
            audit_name = stem+'/audit/report.json'
            self.pins[audit_name] = pin(encoded({'invented': index}))
            gen_inputs = {'run/metadata/plan.json', audit_name}; score_inputs = set(gen_inputs)
            gen_hashes = {}
            for identity in planned['identities']:
                directory = stem+'/result/payload/datasets/'+identity['dataset_id']+'/'
                gen_hashes[identity['stratum']] = {}
                for name in set(audit.GENERATION_FILES) | set(audit.DATASET_INPUTS.values()):
                    self.pins[directory+name] = pin(encoded({'invented': directory+name}))
                    if name in audit.GENERATION_FILES:
                        gen_inputs.add(directory+name)
                        gen_hashes[identity['stratum']][name] = self.pins[directory+name]['sha256']
                    if name in audit.DATASET_INPUTS.values(): score_inputs.add(directory+name)
                evaluation = stem+'/result/payload/evaluations/'+identity['evaluation_id']+'.json'
                self.pins[evaluation] = pin(encoded({'invented': evaluation})); score_inputs.add(evaluation)
            ev = {'audit_sha256': self.pins[audit_name]['sha256']}
            selected = {'attempt': attempt, 'attempt_root': stem.removeprefix('run/attempts/'),
                        'status': 'verified_complete', 'context': {'source_bindings': self.plan['source_bindings']}, 'evidence': ev}
            chunks.append({'chunk_index': index, 'status': 'verified_complete', 'evidence': ev,
                'attempts': ([{'attempt': 1, 'status': 'failed'}] if attempt == 2 else [])+[selected],
                'outcome': {'worker_exit_confirmed': True, 'slots': [
                    {'evaluation_id': i['evaluation_id'], 'status': 'success'} for i in planned['identities']]}})
            common = {**audit.QUIET, 'chunk_index': index, 'attempt': attempt, 'run_root': str(self.run),
                      'prior_attempts_not_credited': attempt-1}
            self.gens.append({**common, 'status': 'selected_pair_checks_passed',
                'input_pins': {p: self.pins[p] for p in gen_inputs}, 'generation_audit': {**audit.QUIET,
                'status': 'generation_checks_passed', **{k: planned[k] for k in ('role', 'seed', 'layout')},
                'pair_id': planned['identities'][0]['pair_id'], 'datasets_checked': 2, 'input_sha256': gen_hashes,
                'normal_generation_verified': True, 'pre_rounding_overlay_verified': True, 'rounding_verified': True}})
            self.olds.append({**common, 'status': 'selected_chunk_checks_passed', 'evaluations_checked': 6,
                'input_pins': {p: self.pins[p] for p in score_inputs}, 'profile_derivation_verified': True,
                'score_derivation_verified': True, 'ledger_derivation_verified': True,
                'evaluations': [invented_row(i) for i in planned['identities']]})
        self.evidence = {'run_root': str(self.run), 'files': self.pins, 'journal_state': {
            'plan_sha256': audit.registry.canonical_sha256(self.plan), 'next_unverified_chunk': None, 'chunks': chunks}}
        self.seal()

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = encoded(value); path.write_bytes(raw)
        return pin(raw)

    def seal(self):
        evidence_pin = self.write(self.roots['completed'].parent/'evidence.json', self.evidence)
        completed = {'status': 'completed', 'full_120_chunks_completed': True, 'cumulative_verified_chunks': 120,
            'cumulative_verified_evaluations': 720, 'next_unverified_chunk': None, 'formal_permission': False,
            'evidence': evidence_pin, 'artifacts': {'evidence.json': evidence_pin}}
        completed_pin = self.write(self.roots['completed'], completed)
        gen_pins, score_pins, connected_pins = {}, {}, {}
        for index, (gen, old) in enumerate(zip(self.gens, self.olds)):
            for report in (gen, old):
                report.update(trust_anchor={**completed_pin, 'path': str(self.roots['completed'])}, evidence_pin=evidence_pin)
            name = f'verified/chunk-{index:03d}.json'
            gen_pins[name] = self.write(self.roots['generation'].parent/name, gen)
            name = 'verified-final/chunk-000.json' if index == 0 else f'chunk-{index:03d}.json'
            (connected_pins if index == 0 else score_pins)[name] = self.write(
                self.roots['connected' if index == 0 else 'score'].parent/name, old)
        connected_pin = self.write(self.roots['connected'], {**audit.QUIET,
            'status': 'bounded_connected_audit_completed', 'artifacts': connected_pins})
        score_pin = self.write(self.roots['score'], {**audit.QUIET, 'status': 'full_saved_numeric_ledger_audit_completed',
            'chunks_verified': 120, 'evaluations_verified': 720, 'full_720_profile_score_audit_completed': True,
            'prior_connected_savepoint': connected_pin, 'completed_campaign_savepoint': completed_pin, 'artifacts': score_pins})
        gen_pin = self.write(self.roots['generation'], {**audit.QUIET, 'status': 'full_saved_generation_audit_completed',
            'pairs_verified': 120, 'datasets_verified': 240, 'linked_profile_score_ledger_evaluations': 720,
            'normal_generation_verified': True, 'pre_rounding_overlay_verified': True, 'rounding_verified': True,
            'successful_result_directory': 'verified', 'previous_score_audit_savepoint': score_pin,
            'connected_savepoint': connected_pin, 'completed_campaign_savepoint': completed_pin, 'artifacts': gen_pins})
        repo = Path(audit.__file__).parents[2]
        self.root_pin = self.write(self.roots['inference'], {**audit.QUIET, 'status': 'inference_math_checks_completed',
            'prior_generation_manifest': gen_pin, 'code_pins': {name: pin((repo/name).read_bytes()) for name in (
                'src/banto_ai/anomaly_v03_inference_audit.py', 'examples/configs/anomaly-v03-freeze-registry.json')}})

    def run_audit(self, digest=None):
        return audit.authenticate_seed_counts(self.roots, digest or self.root_pin['sha256'], self.run)

    def test_complete_chain_no_payload_access_or_writes(self):
        before = {str(p): pin(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        result = self.run_audit()
        self.assertEqual(result['status'], 'authenticated_dev_smoke_counts')
        self.assertEqual(result['attempts_used'][-1], {'chunk_index': 119, 'attempt': 2, 'prior_attempts_not_credited': 1})
        self.assertFalse(result['payloads_rehashed'])
        self.assertEqual(result['profile_score_recalculations'], 0)
        self.assertEqual(before, {str(p): pin(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()})

    def test_wrong_external_root_and_report_tamper_rejected(self):
        with self.assertRaises(ValueError): self.run_audit('0'*64)
        path = self.roots['score'].parent/'chunk-002.json'
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ValueError): self.run_audit()

    def test_missing_report_rejected(self):
        (self.roots['generation'].parent/'verified/chunk-002.json').unlink()
        with self.assertRaises((ValueError, OSError)): self.run_audit()

    def test_resealed_semantic_corruption_rejected(self):
        mutations = [
            lambda: self.olds[119].update(attempt=1),
            lambda: self.gens[0]['generation_audit'].update(normal_generation_verified=False),
            lambda: self.olds[1]['input_pins'].update({'extra/path': pin(b'invented')}),
            lambda: self.olds[0]['evaluations'].reverse(),
            lambda: self.evidence['journal_state']['chunks'][0]['outcome'].update(worker_exit_confirmed=False),
            lambda: self.gens[1]['generation_audit']['input_sha256']['core'].update({'observations.jsonl': '0'*64}),
        ]
        original = copy.deepcopy((self.olds, self.gens, self.evidence))
        for index, mutate in enumerate(mutations):
            self.olds, self.gens, self.evidence = copy.deepcopy(original)
            mutate(); self.seal()
            with self.subTest(index=index), self.assertRaises(ValueError): self.run_audit()


if __name__ == '__main__':
    unittest.main()
