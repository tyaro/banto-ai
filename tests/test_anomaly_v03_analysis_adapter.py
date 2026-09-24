"""Small, invented 12-layout clusters; no registered observations or full CI run."""
import copy
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_analysis_adapter as adapter

I = adapter.inference
SCHEMA = json.loads((Path(__file__).parents[1]/'schemas/anomaly-multiseed-analysis-result-v0.3.schema.json').read_text(encoding='utf-8'))
DRAWS = ((0, 0), (0, 1), (1, 0), (1, 1))


def hand_inputs(*, c1=114, c2=114, zero_control=False):
    clusters, diagnostics = [], []
    for index in range(2):
        cluster = {'cluster_id': f'hand-{index}', 'candidates': {}}
        diagnostic = {'cluster_id': f'hand-{index}', 'candidates': {}}
        for candidate, machine in zip(I.CANDIDATES, (0 if zero_control else 96, c1, c2)):
            cluster['candidates'][candidate] = {}
            diagnostic['candidates'][candidate] = {}
            for layer in I.STRATA[:2]:
                sensor = (0 if zero_control else 96) if candidate == I.CANDIDATES[0] else (114 if layer == 'core' else 108)
                false = 4 if candidate == I.CANDIDATES[0] and not zero_control else 0
                detected = machine + sensor
                raw = {'machine_recall': [machine, 120], 'sensor_recall': [sensor, 120],
                    'precision': [detected, detected+false], 'clean_rate': [false, 40380],
                    'false_alert_burden': [false, 240],
                    **{kind: [20952 if layer == 'core' else 20736, 21600] for kind in I.AVAILABILITY}}
                cluster['candidates'][candidate][layer] = {'profile_status': 'calibrated', 'counts': raw}
                diagnostic['candidates'][candidate][layer] = {'effective_clean_seconds': 40000,
                    'detected_delays': [2 if index == 0 else 4]*detected}
        clusters.append(cluster); diagnostics.append(diagnostic)
    return clusters, diagnostics


def compute(clusters, diagnostics, *, ready=True):
    return adapter.compute_fixture_packet(clusters, DRAWS, diagnostics, SCHEMA, engineering_ready=ready)


class AdapterTests(unittest.TestCase):
    def test_closed_table_shape_mapping_and_hand_answers(self):
        clusters, diagnostics = hand_inputs()
        before = copy.deepcopy((clusters, diagnostics))
        result = compute(clusters, diagnostics)
        self.assertEqual((clusters, diagnostics), before)
        tables = result['fixture_candidate_tables']
        self.assertEqual(len(tables), 9)
        self.assertEqual(sum(len(t['gates']) for t in tables), 180)
        self.assertEqual(set(tables[0]), {'candidate_id','stratum','metrics','gates','profile_status','qualified'})
        m = tables[3]['metrics']
        self.assertEqual(m['machine_recall']['numerator'], 228)
        self.assertEqual(m['machine_recall']['denominator'], 240)
        self.assertEqual(m['machine_recall']['value'], .95)
        self.assertEqual(m['scheduled_clean_seconds'], 80760)
        self.assertEqual(m['effective_clean_seconds'], 80000)
        self.assertEqual(m['delay_summary'], {'count': 456, 'median': 3., 'mean': 3., 'min': 2, 'max': 4,
            'conditioned_on': 'causal-detected-only','undetected_fill': 'forbidden','unit': 'seconds'})
        self.assertEqual([r['full_target'] for r in m['availability']], list(I.TARGETS))
        self.assertEqual(result['fixture_draws'], {'clusters': 2, 'replicates': 4})
        self.assertEqual(result['fixture_selected_candidate'], I.CANDIDATES[1])
        self.assertFalse(result['formal_document_emitted'])
        self.assertIsNone(result['selected_candidate'])
        with self.assertRaises(ValueError): adapter.contract.validate_result_contract(result)

    def test_both_c1_only_c2_only_neither_and_engineering_unready(self):
        for c1, c2, ready, selected, decision in (
            (114,114,True,I.CANDIDATES[1],'qualified'), (114,60,True,I.CANDIDATES[1],'qualified'),
            (60,114,True,I.CANDIDATES[2],'qualified'), (60,60,True,None,'no_promotion'),
            (114,114,False,None,'inconclusive')):
            with self.subTest(c1=c1,c2=c2,ready=ready):
                result = compute(*hand_inputs(c1=c1,c2=c2), ready=ready)
                self.assertEqual((result['fixture_selected_candidate'],result['fixture_decision']), (selected,decision))
                self.assertEqual(result['performance_status'], 'not_evaluated')

    def test_zero_control_precision_and_delay_are_null(self):
        result = compute(*hand_inputs(zero_control=True))
        metrics = result['fixture_candidate_tables'][0]['metrics']
        self.assertEqual(metrics['precision']['null_replicates'], 4)
        self.assertEqual(metrics['precision']['ci_status'], 'inconclusive')
        self.assertIsNone(metrics['precision']['value'])
        self.assertEqual(metrics['delay_summary']['count'], 0)
        self.assertTrue(all(metrics['delay_summary'][k] is None for k in ('median','mean','min','max')))
        self.assertEqual(result['fixture_selected_candidate'], I.CANDIDATES[1])

    def test_control_profile_inconclusive_closes_paired_selection(self):
        clusters, diagnostics = hand_inputs()
        clusters[0]['candidates'][I.CANDIDATES[0]]['core']['profile_status'] = 'inconclusive'
        result = compute(clusters, diagnostics)
        self.assertIsNone(result['fixture_selected_candidate'])
        self.assertEqual(result['fixture_decision'], 'inconclusive')
        self.assertTrue(all(g['ci_status'] == 'inconclusive' for g in result['fixture_candidate_tables'][3]['gates'] if g['comparison'] == 'paired-control'))

    def test_delays_merge_samples_not_means_or_medians(self):
        clusters, diagnostics = hand_inputs()
        # Unequal detected counts give a combined median that is not the mean
        # of the four source medians (1, 5, 5, 5 -> 4).
        candidate = I.CANDIDATES[1]
        for i in (0,1):
            for layer in I.STRATA[:2]:
                cell = clusters[i]['candidates'][candidate][layer]['counts']
                amount = 114 if (i,layer) == (0,'core') else 1
                cell['machine_recall'][0] = cell['sensor_recall'][0] = amount
                cell['precision'] = [2*amount, 2*amount]
                diagnostics[i]['candidates'][candidate][layer]['detected_delays'] = [1 if amount == 114 else 5]*(2*amount)
        result = compute(clusters,diagnostics)
        delay = result['fixture_candidate_tables'][5]['metrics']['delay_summary']
        self.assertEqual(delay['count'],234)
        self.assertEqual(delay['median'],1)
        self.assertAlmostEqual(delay['mean'],258/234)

    def test_missing_extra_reordered_or_invalid_diagnostics_rejected(self):
        mutations = [lambda d:d.pop(),lambda d:d.reverse(),
            lambda d:d[0]['candidates'][I.CANDIDATES[0]].pop('core'),
            lambda d:d[0]['candidates'][I.CANDIDATES[0]]['core'].update(effective_clean_seconds=True),
            lambda d:d[0]['candidates'][I.CANDIDATES[0]]['core'].update(effective_clean_seconds=40381),
            lambda d:d[0]['candidates'][I.CANDIDATES[0]]['core']['detected_delays'].pop(),
            lambda d:d[0]['candidates'][I.CANDIDATES[0]]['core']['detected_delays'].__setitem__(0,0),
            lambda d:d[0]['candidates'][I.CANDIDATES[0]]['core']['detected_delays'].__setitem__(0,6),
            lambda d:d[0]['candidates'][I.CANDIDATES[0]]['core']['detected_delays'].__setitem__(0,math.nan),
            lambda d:d[0]['candidates'][I.CANDIDATES[0]]['core'].update(mean_delay=2)]
        for index, mutate in enumerate(mutations):
            clusters,diagnostics=hand_inputs();mutate(diagnostics)
            with self.subTest(index=index),self.assertRaises(ValueError): compute(clusters,diagnostics)

    def test_denominator_and_real_aggregate_shape_rejected_before_computation(self):
        for bad in ('denominator','real'):
            clusters,diagnostics=hand_inputs()
            if bad == 'denominator': clusters[0]['candidates'][I.CANDIDATES[0]]['core']['counts']['machine_recall'][1] = 100
            else: clusters[0].update(role='dev',seed=123)
            with patch.object(I,'compute_fixture_tables',side_effect=AssertionError('must reject first')):
                with self.assertRaises(ValueError): compute(clusters,diagnostics)

    def test_table_gate_null_and_selection_corruptions_rejected(self):
        result=compute(*hand_inputs())
        mutations = [lambda p:p['fixture_candidate_tables'][0].update(extra=1),
            lambda p:p['fixture_candidate_tables'].reverse(),
            lambda p:p['fixture_candidate_tables'][3]['gates'].pop(),
            lambda p:p['fixture_candidate_tables'][3]['gates'][0].update(point=.94),
            lambda p:p['fixture_candidate_tables'][3]['gates'][-1].update(status='fail'),
            lambda p:p['fixture_candidate_tables'][3]['metrics']['precision'].update(null_replicates=5),
            lambda p:p.update(fixture_selected_candidate=I.CANDIDATES[2]),
            lambda p:p.update(formal_permission=True),
            lambda p:p.update(selected_candidate=I.CANDIDATES[1])]
        for index, mutate in enumerate(mutations):
            value=copy.deepcopy(result);mutate(value)
            with self.subTest(index=index),self.assertRaises(ValueError): adapter.validate_fixture_packet(value,SCHEMA)

    def test_zero_effective_exposure_stays_null(self):
        clusters,diagnostics=hand_inputs()
        for d in diagnostics:
            d['candidates'][I.CANDIDATES[0]]['core']['effective_clean_seconds']=0
        result=compute(clusters,diagnostics)
        self.assertIsNone(result['fixture_candidate_tables'][0]['metrics']['effective_clean_rate'])

    def test_uncomputed_or_profile_incompatible_ci_rejected(self):
        result=compute(*hand_inputs())
        for change in ('not_evaluated', 'profile', 'bool_nulls'):
            value=copy.deepcopy(result)
            table=value['fixture_candidate_tables'][0]
            metric=table['metrics']['machine_recall']
            if change == 'not_evaluated': metric.update(ci_status='not_evaluated',ci_lower=None,ci_upper=None)
            elif change == 'profile': table['profile_status']='inconclusive'
            else: metric['null_replicates']=False
            with self.subTest(change=change),self.assertRaises(ValueError): adapter.validate_fixture_packet(value,SCHEMA)

    def test_input_ci_and_gate_values_preserved_without_rounding(self):
        clusters,diagnostics=hand_inputs()
        result=compute(clusters,diagnostics)
        raw=I.compute_fixture_tables(clusters,DRAWS,engineering_ready=True)
        for mapped,original in zip(result['fixture_candidate_tables'],raw['candidate_tables']):
            self.assertEqual(mapped['gates'],original['gates'])
            for kind in I.METRICS[:5]: self.assertEqual(mapped['metrics'][kind],original['metrics'][kind])
            for target,kind in zip(mapped['metrics']['availability'],I.AVAILABILITY):
                self.assertEqual(target['metric'],original['metrics'][kind])


if __name__ == '__main__':
    unittest.main()
